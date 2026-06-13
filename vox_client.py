import base64
import io
import json
import os
import queue
import sys
import time
import uuid
import wave
import logging
import threading
import subprocess
import webbrowser
import tkinter as tk
from tkinter import messagebox
from urllib import error, request as urlrequest

try:
    from websockets.sync.client import connect as ws_connect
except ImportError:
    ws_connect = None

import config
from infrastructure.SoundDeviceMicrophone import MicrophoneManager
from presentation.TranscriptionOverlay import TranscriptionOverlay
from infrastructure.X11TextInjector import TextInjector
from presentation.VoxTrayIcon import VoxTrayIcon
from presentation.VoxMenu import VoxMenu

from config import LOG_LEVEL

numeric_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(level=numeric_level, format="%(asctime)s [%(levelname)s] (%(threadName)s) %(message)s")
logger = logging.getLogger("VoxClient")

class VoxClientDaemon:
    def __init__(self):
        self.stop_event = threading.Event()
        self.recording_lock = threading.Lock()
        self.injector = TextInjector()
        self.audio = MicrophoneManager()
        self.overlay = TranscriptionOverlay(self.audio)
        self.tray_menu = VoxMenu(self.overlay.root)
        self.ui_queue = queue.Queue()

        self.paused = False
        self.active_recording = False
        self.recording_thread = None
        self.current_session_id = 0
        self.has_injected_current_session = False
        self.last_transcription = ""
        self.language = config.LANGUAGE
        self.autostart_enabled = self._is_autostart_enabled()

        self.tray = VoxTrayIcon(
            on_toggle_pause=self.toggle_pause,
            on_copy_last_text=self.copy_last_text,
            on_open_preferences=self.open_preferences,
            on_audio_device_change=self.change_audio_device,
            on_language_change=self.change_language,
            on_toggle_autostart=self.toggle_autostart,
            on_check_updates=self.check_for_updates,
            on_about=self.show_about,
            on_quit=self.shutdown,
            on_edit_prompt=self.edit_prompt,
            show_custom_menu_callback=self.show_tray_menu,
        )

        self.max_retries = 6
        self.retry_delay = 1.5
        self.connect_timeout = 60.0
        self.shutdown_lock = threading.Lock()
        self.hotkey_listener = None
        self.overlay_destroyed = False
        self.initial_prompt = self._load_prompt()

    def show_tray_menu(self, menu_data):
        """Ставить команду показу меню в чергу для виконання у головному потоці."""
        self.ui_queue.put(menu_data)

    def _is_autostart_enabled(self) -> bool:
        autostart_file = self._get_autostart_file()
        return os.path.exists(autostart_file)

    def _get_autostart_file(self) -> str:
        autostart_dir = os.path.expanduser("~/.config/autostart")
        return os.path.join(autostart_dir, "vox.desktop")

    def _build_autostart_entry(self) -> str:
        exec_command = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
        return (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=Vox\n"
            f"Exec={exec_command}\n"
            "X-GNOME-Autostart-enabled=true\n"
            "NoDisplay=false\n"
        )

    def _get_prompt_file(self) -> str:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), ".prompt")

    def _load_prompt(self) -> str:
        try:
            with open(self._get_prompt_file(), "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            return ""

    def _save_prompt(self, prompt: str):
        try:
            with open(self._get_prompt_file(), "w", encoding="utf-8") as f:
                f.write(prompt)
            self.initial_prompt = prompt
            self.tray.set_initial_prompt(prompt)
        except Exception as e:
            logger.error(f"Failed to save prompt: {e}")

    def edit_prompt(self):
        import tkinter as tk
        from tkinter import simpledialog

        def _show_dialog():
            root = tk.Tk()
            root.withdraw()
            current = self.initial_prompt or ""
            prompt = simpledialog.askstring(
                "Vox - Initial Prompt",
                "Enter initial prompt for Whisper.\nThis helps recognize Ukrainian and technical terms:",
                initialvalue=current,
                parent=root,
            )
            root.destroy()
            if prompt is not None:
                self._save_prompt(prompt.strip())

        self.ui_queue.put(("dialog", _show_dialog))

    def toggle_pause(self, paused: bool):
        self.paused = paused
        if self.paused:
            logger.info("Recognition paused")
            if self.active_recording:
                self.active_recording = False
                self.overlay.show_processing()
            self.tray.update_state("idle")
        else:
            logger.info("Recognition resumed")
            self.tray.update_state("listening")

    def copy_last_text(self):
        if not self.last_transcription:
            logger.info("Немає останнього тексту для копіювання")
            return

        try:
            root = tk.Tk()
            root.withdraw()
            root.clipboard_clear()
            root.clipboard_append(self.last_transcription)
            root.update()
            root.destroy()
            logger.info("Останній текст скопійовано до буфера обміну")
        except Exception as e:
            logger.error(f"Не вдалося скопіювати до буфера обміну: {e}")

    def open_preferences(self):
        preferences_path = os.path.join(os.path.dirname(__file__), "README.md")
        if not os.path.exists(preferences_path):
            preferences_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        try:
            if sys.platform.startswith("linux"):
                subprocess.Popen(["xdg-open", preferences_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", preferences_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif sys.platform == "win32":
                os.startfile(preferences_path)
            else:
                logger.info("Open preferences is not supported on this platform.")
        except Exception as e:
            logger.error(f"Не вдалося відкрити налаштування: {e}")

    def change_audio_device(self, device):
        if self.audio.device == device:
            return
        logger.info(f"Вибрано аудіопристрій: {device}")
        try:
            self.audio.set_input_device(device)
            self.tray.set_audio_devices(self.audio.list_input_devices(), self.audio.device)
        except Exception as e:
            logger.error(f"Не вдалося встановити аудіопристрій: {e}")

    def change_language(self, language):
        if self.language == language:
            return
        self.language = language
        config.LANGUAGE = language
        logger.info(f"Мова розпізнавання змінена на: {language}")
        self.tray.set_language(language)

    def toggle_autostart(self, enabled: bool):
        autostart_file = self._get_autostart_file()
        try:
            if enabled:
                os.makedirs(os.path.dirname(autostart_file), exist_ok=True)
                with open(autostart_file, "w", encoding="utf-8") as f:
                    f.write(self._build_autostart_entry())
                logger.info("Автозапуск увімкнено")
            else:
                if os.path.exists(autostart_file):
                    os.remove(autostart_file)
                logger.info("Автозапуск вимкнено")
            self.autostart_enabled = enabled
        except Exception as e:
            logger.error(f"Не вдалося змінити автозапуск: {e}")
            self.autostart_enabled = self._is_autostart_enabled()
        self.tray.set_autostart(self.autostart_enabled)

    def check_for_updates(self):
        threading.Thread(target=self._check_for_updates_worker, daemon=True).start()

    def _normalize_remote_url(self, url: str) -> str:
        if url.startswith("git@github.com:"):
            return "https://github.com/" + url.split("git@github.com:", 1)[1].replace(".git", "")
        if url.startswith("git://"):
            return url.replace("git://", "https://")
        return url

    def _check_for_updates_worker(self):
        repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            remote_url = subprocess.check_output(
                ["git", "-C", repo_dir, "remote", "get-url", "origin"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            local_hash = subprocess.check_output(
                ["git", "-C", repo_dir, "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            remote_hash = subprocess.check_output(
                ["git", "-C", repo_dir, "ls-remote", "origin", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).split()[0]

            if local_hash == remote_hash:
                logger.info("Оновлення не потрібні: програма вже актуальна.")
            else:
                logger.info("Доступне оновлення. Відкриваю сторінку репозиторію...")
                url = self._normalize_remote_url(remote_url)
                if url:
                    webbrowser.open(url)
        except Exception as e:
            logger.warning(f"Не вдалося перевірити оновлення: {e}")

    def show_about(self):
        repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        version = getattr(config, 'APP_VERSION', '0.1.0')
        message = f"Vox\nВерсія: {version}\nМова: {self.language}\nГарячі клавіші: {config.HOTKEY}\n"

        try:
            remote_url = subprocess.check_output(
                ["git", "-C", repo_dir, "remote", "get-url", "origin"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            if remote_url:
                message += f"Repo: {self._normalize_remote_url(remote_url)}\n"
        except Exception:
            pass

        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo("About Vox", message)
            root.destroy()
        except Exception as e:
            logger.info(message)
            logger.warning(f"Не вдалося показати вікно About: {e}")

    def _build_wav_bytes(self, audio_bytes: bytes) -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.audio.sample_rate)
            wav_file.writeframes(audio_bytes)
        return buffer.getvalue()

    def _transcribe_audio(self, audio_bytes: bytes) -> str:
        if not audio_bytes:
            return ""

        wav_data = self._build_wav_bytes(audio_bytes)
        url = config.SERVER_BASE_URL.rstrip("/") + "/audio/transcriptions"
        boundary = uuid.uuid4().hex

        def field(name, value):
            return (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")

        body = (
            field("model", config.WHISPER_MODEL)
            + field("language", self.language)
            + (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n'
                f"Content-Type: audio/wav\r\n\r\n"
            ).encode("utf-8")
            + wav_data
            + f"\r\n--{boundary}--\r\n".encode("utf-8")
        )

        req = urlrequest.Request(url, data=body, method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        req.add_header("Content-Length", str(len(body)))

        try:
            with urlrequest.urlopen(req, timeout=self.connect_timeout) as resp:
                payload = resp.read().decode("utf-8", errors="ignore")
                data = json.loads(payload)
                return data.get("text", "").strip()
        except error.HTTPError as e:
            body_err = e.read().decode("utf-8", errors="ignore")
            logger.error(f"Transcription HTTP error {e.code}: {body_err}")
        except Exception as e:
            logger.error(f"Transcription error: {e}")
        return ""

    def start_recording_session(self):
        if self.paused:
            logger.info("Recognition paused, hotkey ignored.")
            return

        with self.recording_lock:
            if self.active_recording:
                self.active_recording = False
                self.overlay.show_processing()
                self.tray.update_state("listening")
                return

            if self.recording_thread and self.recording_thread.is_alive():
                logger.warning("Recording thread still active; ignoring duplicate start request.")
                return

            self.current_session_id += 1
            self.has_injected_current_session = False
            self.last_transcription = ""
            self.active_recording = True
            session_id = self.current_session_id
        
        # Запуск аудіо потоку
        self.audio.start()
        self.audio.start_wav_recording()

        self.tray.update_state("recording")
        self.overlay.show_waveform()
        self.recording_thread = threading.Thread(target=self._streaming_worker, name="VoxStreamWorker", daemon=True)
        self.recording_thread.start()
        logger.info(f"Started recording session {session_id}")

    def _streaming_worker(self):
        is_ws = config.SERVER_BASE_URL.startswith("ws://") or config.SERVER_BASE_URL.startswith("wss://")
        if is_ws and ws_connect:
            self._streaming_worker_ws()
        else:
            self._streaming_worker_http()

    def _streaming_worker_ws(self):
        session_id = self.current_session_id
        self.audio.clear_queues()
        self.audio.route_to_server = True
        
        try:
            with ws_connect(config.SERVER_BASE_URL, timeout=self.connect_timeout) as ws:
                # 1. Надсилаємо налаштування
                ws.send(json.dumps({
                    "type": "start",
                    "language": self.language,
                    "model": config.WHISPER_MODEL,
                    "api_key": getattr(config, "API_KEY", ""),
                    "initial_prompt": self.initial_prompt or getattr(config, "INITIAL_PROMPT", "") or None
                }))

                logger.info("Recording audio (WebSocket)...")
                while self.active_recording and not self.stop_event.is_set():
                    try:
                        chunk = self.audio.server_queue.get(timeout=0.2)
                        ws.send(chunk)
                    except queue.Empty:
                        continue
                
                # 2. Зупиняємо запис і просимо фінальний результат
                self.audio.route_to_server = False
                self.overlay.show_processing()
                ws.send(json.dumps({"type": "stop"}))
                
                # 3. Очікуємо результат
                msg = ws.recv()
                data = json.loads(msg)
                text = data.get("text", "").strip()
                
                if text:
                    self._handle_transcription_result(text, session_id)
                    
        except Exception as e:
            logger.error(f"WebSocket stream error: {e}")
        finally:
            self._finalize_recording_session()

    def _streaming_worker_http(self):
        session_id = self.current_session_id
        self.audio.clear_queues()
        self.audio.route_to_server = True

        try:
            audio_buffer = bytearray()
            logger.info("Recording audio (HTTP)...")
            while self.active_recording and not self.stop_event.is_set():
                try:
                    chunk = self.audio.server_queue.get(timeout=0.2)
                    audio_buffer.extend(chunk)
                except queue.Empty:
                    continue

            self.audio.route_to_server = False
            self.overlay.show_processing()
            
            text = self._transcribe_audio(bytes(audio_buffer))
            if text:
                self._handle_transcription_result(text, session_id)
        except Exception as e:
            logger.error(f"HTTP stream error: {e}")
        finally:
            self._finalize_recording_session()

    def _handle_transcription_result(self, text: str, session_id: int):
        if session_id != self.current_session_id:
            logger.warning(f"Ignoring result from old session {session_id}")
            return
        if self.has_injected_current_session:
            logger.warning(f"Ignoring duplicated injection in session {session_id}")
            return
            
        with self.recording_lock:
            self.has_injected_current_session = True
            
        if text == self.last_transcription:
            logger.warning(f"Ignoring identical text in session {session_id}")
        else:
            self.last_transcription = text
            self.tray.update_last_text(text)
            try:
                self.injector.inject(text)
            except Exception as e:
                logger.error(f"Injection error: {e}")

    def _finalize_recording_session(self):
        with self.recording_lock:
            self.active_recording = False
        self.audio.route_to_server = False
        
        # Зупинка аудіо потоку
        self.audio.stop_wav_recording()
        self.audio.stop()
        
        self.overlay.hide()
        if not self.paused:
            self.tray.update_state("listening")
        else:
            self.tray.update_state("idle")
        self.recording_thread = None

    def _init_hotkeys(self):
        from pynput import keyboard
        self.hotkey_listener = keyboard.GlobalHotKeys({config.HOTKEY: self.start_recording_session})
        self.hotkey_listener.start()

    def run(self):
        # self.audio.start() -- видалено, запуск динамічний
        self.tray.set_audio_devices(self.audio.list_input_devices(), self.audio.device)
        self.tray.set_language(self.language)
        self.tray.set_autostart(self.autostart_enabled)
        self.tray.set_paused(self.paused)
        self.tray.set_initial_prompt(self.initial_prompt)
        self._init_hotkeys()
        self.tray.start()
        logger.info(f"Using VOX_SERVER_URL: {config.SERVER_BASE_URL}")

        if config.SERVER_BASE_URL.startswith("ws"):
            logger.info("WebSocket transcription mode enabled")
        else:
            logger.info("HTTP transcription mode enabled")
        try:
            while not self.stop_event.is_set():
                # Обробка черги UI команд
                try:
                    while not self.ui_queue.empty():
                        item = self.ui_queue.get_nowait()
                        if isinstance(item, tuple) and item[0] == "dialog":
                            item[1]()
                        else:
                            menu_data = item
                            x, y = self.overlay.root.winfo_pointerxy()
                            self.tray_menu.set_data(menu_data)
                            self.tray_menu.show(x, y)
                except queue.Empty:
                    pass
                
                self.overlay.run_step()
                time.sleep(0.01)
        except KeyboardInterrupt:
            self.shutdown()
        finally:
            if self.overlay and not self.overlay_destroyed:
                self.overlay.destroy()
                self.overlay_destroyed = True
                self.overlay = None

    def shutdown(self):
        with self.shutdown_lock:
            if self.stop_event.is_set() and self.overlay_destroyed:
                return
            logger.info("Shutdown requested")
            self.stop_event.set()
            if self.hotkey_listener:
                try:
                    self.hotkey_listener.stop()
                    self.hotkey_listener.join(timeout=2.0)
                except Exception as e:
                    logger.warning(f"Failed to stop hotkey listener: {e}")
            if self.recording_thread and self.recording_thread.is_alive():
                try:
                    self.recording_thread.join(timeout=2.0)
                except Exception as e:
                    logger.warning(f"Failed to join recording thread: {e}")
            self.audio.stop()
            self.tray.stop()
            if self.tray.thread and self.tray.thread.is_alive():
                try:
                    self.tray.thread.join(timeout=2.0)
                except Exception as e:
                    logger.warning(f"Failed to join tray thread: {e}")
            if threading.current_thread() is threading.main_thread():
                if self.overlay:
                    self.overlay.destroy()
                    self.overlay_destroyed = True
                    self.overlay = None

if __name__ == "__main__":
    VoxClientDaemon().run()
