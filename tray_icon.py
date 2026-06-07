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
        self.title = title

        self.paused = False
        self.last_text = ""
        self.selected_audio_device = None
        self.available_audio_devices = []
        self.language = "uk"
        self.autostart_enabled = False
        self.state = "listening"  # "listening", "idle", "recording"

        self.icon = None
        self.thread = None
        self.fallback_menu = None

        self.current_image = self._generate_icon_image()

    def _generate_icon_image(self) -> Image.Image:
        """Динамічно малює іконку статусу в пам'яті (LED-індикатор)."""
        width, height = 64, 64
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        dc = ImageDraw.Draw(image)

        # Визначаємо колір індикатора на основі стану
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
        """Оновлює внутрішній стан та змінює вигляд іконки."""
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

    def _refresh_icon(self):
        self.current_image = self._generate_icon_image()
        if self.icon:
            self.icon.icon = self.current_image

    def _refresh_menu(self):
        if self.icon:
            if self.icon.HAS_MENU:
                self.icon.menu = self._build_menu()
            else:
                self.fallback_menu = self._build_menu()

    def _toggle_pause_action(self, icon, item):
        self.paused = not self.paused
        self.set_paused(self.paused)
        if self.on_toggle_pause:
            self.on_toggle_pause(self.paused)

    def _copy_last_text_action(self, icon, item):
        if self.on_copy_last_text:
            self.on_copy_last_text()

    def _open_preferences_action(self, icon, item):
        if self.on_open_preferences:
            self.on_open_preferences()

    def _select_audio_device_action(self, icon, item, device):
        self.selected_audio_device = device
        self._refresh_menu()
        if self.on_audio_device_change:
            self.on_audio_device_change(device)

    def _select_language_action(self, icon, item, language):
        self.language = language
        self._refresh_menu()
        if self.on_language_change:
            self.on_language_change(language)

    def _toggle_autostart_action(self, icon, item):
        self.autostart_enabled = not self.autostart_enabled
        self._refresh_menu()
        if self.on_toggle_autostart:
            self.on_toggle_autostart(self.autostart_enabled)

    def _check_updates_action(self, icon, item):
        if self.on_check_updates:
            self.on_check_updates()

    def _about_action(self, icon, item):
        if self.on_about:
            self.on_about()

    def _quit_action(self, icon, item):
        logger.info("Натиснуто вихід у треї. Зупиняю іконку трею...")
        self.icon.stop()
        if self.on_quit:
            self.on_quit()

    def _has_zenity(self) -> bool:
        return shutil.which("zenity") is not None

    def _zenity_select(self, title: str, column: str, items: list[str]) -> str | None:
        if not self._has_zenity() or not items:
            return None

        command = [
            "zenity",
            "--list",
            "--title",
            title,
            "--column",
            column,
            "--height",
            "360",
            "--width",
            "420",
            "--text",
            "Select an item",
        ]
        command.extend(items)

        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.warning(f"Zenity dialog failed: {e}")
        return None

    def _open_audio_input_dialog(self) -> int | None:
        if not self.available_audio_devices:
            return None
        entries = [f"[{device_id}] {device_name}" for device_id, device_name in self.available_audio_devices]
        selected = self._zenity_select("Vox audio input", "Device", entries)
        if not selected:
            return None
        try:
            device_id = int(selected.split("]", 1)[0].lstrip("["))
            return device_id
        except ValueError:
            return None

    def _open_language_dialog(self) -> str | None:
        option = self._zenity_select(
            "Vox language",
            "Language",
            [
                "uk",
                "en",
            ],
        )
        return option

    def _open_fallback_menu(self, icon, item):
        pause_label = "Resume recognition" if self.paused else "Pause recognition"
        boot_label = "Disable Start on Boot" if self.autostart_enabled else "Enable Start on Boot"
        choices = [pause_label, "Audio Input", "Language", "Preferences...", boot_label, "Check for Updates", "About", "Quit"]
        if self.last_text:
            choices.insert(1, "Copy Last Text")

        action = self._zenity_select("Vox tray menu", "Action", choices)
        if not action:
            return

        if action == pause_label:
            self._toggle_pause_action(icon, item)
        elif action == "Copy Last Text":
            self._copy_last_text_action(icon, item)
        elif action == "Audio Input":
            device = self._open_audio_input_dialog()
            if device is not None:
                self._select_audio_device_action(icon, item, device)
        elif action == "Language":
            lang = self._open_language_dialog()
            if lang:
                self._select_language_action(icon, item, lang)
        elif action == "Preferences...":
            self._open_preferences_action(icon, item)
        elif action == boot_label:
            self._toggle_autostart_action(icon, item)
        elif action == "Check for Updates":
            self._check_updates_action(icon, item)
        elif action == "About":
            self._about_action(icon, item)
        elif action == "Quit":
            self._quit_action(icon, item)

    def _build_menu(self):
        pause_label = "Resume recognition" if self.paused else "Pause recognition"
        device_items = []
        if self.available_audio_devices:
            for device_id, device_name in self.available_audio_devices:
                device_items.append(
                    item(
                        device_name,
                        partial(self._select_audio_device_action, device=device_id),
                        checked=lambda item, device=device_id: self.selected_audio_device == device,
                    )
                )
        else:
            device_items.append(item("No input devices", lambda icon, item: None, enabled=False))

        language_items = [
            item(
                "Українська",
                partial(self._select_language_action, language="uk"),
                checked=lambda item: self.language == "uk",
            ),
            item(
                "English",
                partial(self._select_language_action, language="en"),
                checked=lambda item: self.language == "en",
            ),
        ]

        return Menu(
            item("Vox - Hands-Free STT", lambda icon, item: None, enabled=False),
            Menu.SEPARATOR,
            item(pause_label, self._toggle_pause_action, checked=lambda item: self.paused),
            item("Copy Last Text", self._copy_last_text_action, enabled=lambda item: bool(self.last_text)),
            Menu.SEPARATOR,
            item("Audio Input", Menu(*device_items)),
            item("Language", Menu(*language_items)),
            item("Preferences...", self._open_preferences_action),
            Menu.SEPARATOR,
            item("Start on Boot", self._toggle_autostart_action, checked=lambda item: self.autostart_enabled),
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
            menu=self._build_menu(),
        )

        if not self.icon.HAS_MENU:
            self.fallback_menu = self._build_menu()
            self.icon.menu = Menu(item("Open Vox menu", self._open_fallback_menu, default=True))

        self.thread = threading.Thread(target=self.icon.run, daemon=True)
        self.thread.start()
        logger.info("Потік трею запущено!")

    def stop(self):
        if self.icon:
            self.icon.stop()

