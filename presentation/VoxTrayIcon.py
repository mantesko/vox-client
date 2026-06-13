import threading
import logging
import shutil
import subprocess
from functools import partial
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item, Menu

logger = logging.getLogger("VoxTray")

class VoxTrayIcon:
    def __init__(
        self,
        on_toggle_pause,
        on_copy_last_text,
        on_open_preferences,
        on_audio_device_change,
        on_language_change,
        on_toggle_autostart,
        on_check_updates,
        on_about,
        on_quit,
        on_edit_prompt=None,
        on_toggle_save_audio=None,
        title="Vox - hands-free voice to text",
    ):
        self.on_toggle_pause = on_toggle_pause
        self.on_copy_last_text = on_copy_last_text
        self.on_open_preferences = on_open_preferences
        self.on_audio_device_change = on_audio_device_change
        self.on_language_change = on_language_change
        self.on_toggle_autostart = on_toggle_autostart
        self.on_check_updates = on_check_updates
        self.on_about = on_about
        self.on_quit = on_quit
        self.on_edit_prompt = on_edit_prompt
        self.on_toggle_save_audio = on_toggle_save_audio
        self.title = title

        self.paused = False
        self.last_text = ""
        self.selected_audio_device = None
        self.available_audio_devices = []
        self.language = "uk"
        self.autostart_enabled = False
        self.initial_prompt = ""
        self.save_audio = False
        self.state = "listening"

        self.icon = None
        self.thread = None

        self.current_image = self._generate_icon_image()

    def _generate_icon_image(self) -> Image.Image:
        width, height = 64, 64
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        dc = ImageDraw.Draw(image)

        if self.state == "recording":
            color = (255, 59, 48, 255)
            glow_color = (255, 59, 48, 80)
        elif self.paused:
            color = (142, 142, 147, 255)
            glow_color = (142, 142, 147, 80)
        elif self.state == "listening":
            color = (52, 199, 89, 255)
            glow_color = (52, 199, 89, 80)
        else:
            color = (142, 142, 147, 255)
            glow_color = (142, 142, 147, 80)

        dc.ellipse((2, 2, width - 2, height - 2), fill=glow_color)
        dc.ellipse((12, 12, width - 12, height - 12), fill=color, outline=(255, 255, 255, 255), width=2)

        return image

    def update_state(self, state: str):
        if state not in ["listening", "idle", "recording"]:
            return
        self.state = state
        logger.info(f"Оновлення стану трею: {state}")
        self.current_image = self._generate_icon_image()
        if self.icon:
            self.icon.icon = self.current_image

    def set_paused(self, paused: bool):
        self.paused = paused
        logger.info(f"Pause mode {'on' if paused else 'off'}")
        if not paused and self.state == "idle":
            self.state = "listening"
        if paused:
            self.state = "idle"
        self._refresh_icon()
        self._refresh_menu()

    def update_last_text(self, text: str):
        self.last_text = text or ""
        self._refresh_menu()

    def set_audio_devices(self, devices, selected_device=None):
        self.available_audio_devices = devices or []
        self.selected_audio_device = selected_device
        self._refresh_menu()

    def set_language(self, language: str):
        self.language = language
        self._refresh_menu()

    def set_autostart(self, enabled: bool):
        self.autostart_enabled = enabled
        self._refresh_menu()

    def set_initial_prompt(self, prompt: str):
        self.initial_prompt = prompt or ""
        self._refresh_menu()

    def set_save_audio(self, enabled: bool):
        self.save_audio = enabled
        self._refresh_menu()

    def _refresh_icon(self):
        self.current_image = self._generate_icon_image()
        if self.icon:
            self.icon.icon = self.current_image

    def _refresh_menu(self):
        if self.icon:
            self.icon.menu = self._build_menu()

    def _toggle_pause_action(self, icon=None, item=None):
        self.paused = not self.paused
        self.set_paused(self.paused)
        if self.on_toggle_pause:
            self.on_toggle_pause(self.paused)

    def _copy_last_text_action(self, icon=None, item=None):
        if self.on_copy_last_text:
            self.on_copy_last_text()

    def _open_preferences_action(self, icon=None, item=None):
        if self.on_open_preferences:
            self.on_open_preferences()

    def _select_audio_device_action(self, device, icon=None, item=None):
        self.selected_audio_device = device
        self._refresh_menu()
        if self.on_audio_device_change:
            self.on_audio_device_change(device)

    def _select_language_action(self, language, icon=None, item=None):
        self.language = language
        self._refresh_menu()
        if self.on_language_change:
            self.on_language_change(language)

    def _toggle_autostart_action(self, icon=None, item=None):
        self.autostart_enabled = not self.autostart_enabled
        self._refresh_menu()
        if self.on_toggle_autostart:
            self.on_toggle_autostart(self.autostart_enabled)

    def _toggle_save_audio_action(self, icon=None, item=None):
        self.save_audio = not self.save_audio
        self._refresh_menu()
        if self.on_toggle_save_audio:
            self.on_toggle_save_audio(self.save_audio)

    def _check_updates_action(self, icon=None, item=None):
        if self.on_check_updates:
            self.on_check_updates()

    def _about_action(self, icon=None, item=None):
        if self.on_about:
            self.on_about()

    def _edit_prompt_action(self, icon=None, item=None):
        if self.on_edit_prompt:
            self.on_edit_prompt()

    def _quit_action(self, icon=None, item=None):
        logger.info("Натиснуто вихід у треї. Зупиняю іконку трею...")
        if self.icon:
            self.icon.stop()
        if self.on_quit:
            self.on_quit()

    def _build_menu(self):
        pause_label = "Resume recognition" if self.paused else "Pause recognition"

        device_items = []
        if self.available_audio_devices:
            for device_id, device_name in self.available_audio_devices:
                device_items.append(item(
                    device_name,
                    partial(self._select_audio_device_action, device_id),
                    checked=lambda i, did=device_id: self.selected_audio_device == did,
                    radio=True,
                ))
        else:
            device_items.append(item("No input devices", None, enabled=False))

        language_items = [
            item("Українська", partial(self._select_language_action, "uk"),
                 checked=lambda i: self.language == "uk", radio=True),
            item("English", partial(self._select_language_action, "en"),
                 checked=lambda i: self.language == "en", radio=True),
        ]

        prompt_label = f"Prompt: {self.initial_prompt[:30]}..." if len(self.initial_prompt) > 30 else f"Prompt: {self.initial_prompt}" if self.initial_prompt else "Prompt: (empty)"

        return Menu(
            item(pause_label, self._toggle_pause_action, checked=lambda i: self.paused),
            item("Copy Last Text", self._copy_last_text_action, enabled=lambda i: bool(self.last_text)),
            Menu.SEPARATOR,
            item("Audio Input", Menu(*device_items)),
            item("Language", Menu(*language_items)),
            item(prompt_label, self._edit_prompt_action),
            item("Preferences...", self._open_preferences_action),
            Menu.SEPARATOR,
            item("Start on Boot", self._toggle_autostart_action, checked=lambda i: self.autostart_enabled),
            item("Save Audio", self._toggle_save_audio_action, checked=lambda i: self.save_audio),
            item("Check for Updates", self._check_updates_action),
            Menu.SEPARATOR,
            item("About", self._about_action),
            item("Quit", self._quit_action),
        )

    def start(self):
        logger.info("Запуск потоку іконки трею...")
        self.icon = pystray.Icon(
            name="vox",
            icon=self.current_image,
            title=self.title,
            menu=self._build_menu()
        )

        self.thread = threading.Thread(target=self.icon.run, daemon=True)
        self.thread.start()
        logger.info("Потік трею запущено!")

    def stop(self):
        if self.icon:
            self.icon.stop()
