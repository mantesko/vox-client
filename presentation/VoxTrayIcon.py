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
        show_custom_menu_callback=None,
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
        self.show_custom_menu_callback = show_custom_menu_callback
        self.title = title

        self.paused = False
        self.last_text = ""
        self.selected_audio_device = None
        self.available_audio_devices = []
        self.language = "uk"
        self.autostart_enabled = False
        self.initial_prompt = ""
        self.state = "listening"  # "listening", "idle", "recording"

        self.icon = None
        self.thread = None

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

    def set_initial_prompt(self, prompt: str):
        self.initial_prompt = prompt or ""
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

    def get_menu_structure(self):
        """Повертає структуру меню у вигляді списку словників для кастомного меню."""
        pause_label = "Resume recognition" if self.paused else "Pause recognition"
        
        device_items = []
        if self.available_audio_devices:
            for device_id, device_name in self.available_audio_devices:
                device_items.append({
                    "label": device_name,
                    "callback": partial(self._select_audio_device_action, device_id),
                    "checked": self.selected_audio_device == device_id
                })
        else:
            device_items.append({"label": "No input devices", "enabled": False})

        language_items = [
            {
                "label": "Українська",
                "callback": partial(self._select_language_action, "uk"),
                "checked": self.language == "uk"
            },
            {
                "label": "English",
                "callback": partial(self._select_language_action, "en"),
                "checked": self.language == "en"
            }
        ]

        prompt_label = f"Prompt: {self.initial_prompt[:30]}..." if len(self.initial_prompt) > 30 else f"Prompt: {self.initial_prompt}" if self.initial_prompt else "Prompt: (empty)"

        menu = [
            {"label": pause_label, "callback": self._toggle_pause_action, "checked": self.paused},
            {"label": "Copy Last Text", "callback": self._copy_last_text_action, "enabled": bool(self.last_text)},
            {"separator": True},
            {"label": "Audio Input", "submenu": device_items},
            {"label": "Language", "submenu": language_items},
            {"label": prompt_label, "callback": self._edit_prompt_action},
            {"label": "Preferences...", "callback": self._open_preferences_action},
            {"separator": True},
            {"label": "Start on Boot", "callback": self._toggle_autostart_action, "checked": self.autostart_enabled},
            {"label": "Check for Updates", "callback": self._check_updates_action},
            {"separator": True},
            {"label": "About", "callback": self._about_action},
            {"label": "Quit", "callback": self._quit_action},
        ]
        return menu

    def _open_custom_menu(self, icon, item):
        if self.show_custom_menu_callback:
            self.show_custom_menu_callback(self.get_menu_structure())

    def _build_menu(self):
        return Menu(item("Open Menu", self._open_custom_menu, default=True))

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

