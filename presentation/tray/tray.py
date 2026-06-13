import threading
import logging

import pystray

from .state import TrayState
from .icon import TrayIconGenerator
from .menu import TrayMenuBuilder

logger = logging.getLogger("VoxTray")


class VoxTrayIcon:
    def __init__(
        self,
        on_toggle_pause,
        on_copy_last_text,
        on_open_preferences,
        on_toggle_autostart,
        on_about,
        on_quit,
        on_toggle_save_audio=None,
        on_play_recording=None,
        on_toggle_auto_enter=None,
        title="Vox - hands-free voice to text",
    ):
        self._tray_state = TrayState()
        self._title = title
        self._icon = None
        self._thread = None
        self._icon_gen = TrayIconGenerator()

        callbacks = {
            "toggle_pause": self._toggle_pause,
            "copy_last_text": on_copy_last_text,
            "open_preferences": on_open_preferences,
            "toggle_autostart": self._toggle_autostart,
            "toggle_save_audio": self._toggle_save_audio,
            "play_recording": on_play_recording,
            "toggle_auto_enter": self._toggle_auto_enter,
            "about": on_about,
            "quit": self._quit,
        }
        self._menu_builder = TrayMenuBuilder(callbacks)

        self._on_toggle_pause = on_toggle_pause
        self._on_toggle_autostart = on_toggle_autostart
        self._on_toggle_save_audio = on_toggle_save_audio
        self._on_toggle_auto_enter = on_toggle_auto_enter
        self._on_quit = on_quit

    def update_state(self, state: str):
        if state not in ("listening", "idle", "recording"):
            return
        self._tray_state = self._tray_state.with_state(state)
        self._refresh_icon()

    def set_paused(self, paused: bool):
        self._tray_state = self._tray_state.with_paused(paused)
        self._refresh_icon()
        self._refresh_menu()

    def update_last_text(self, text: str):
        self._tray_state.last_text = text or ""
        self._refresh_menu()

    def set_autostart(self, enabled: bool):
        self._tray_state.autostart_enabled = enabled
        self._refresh_menu()

    def set_save_audio(self, enabled: bool):
        self._tray_state.save_audio = enabled
        self._refresh_menu()

    def set_recording_exists(self, exists: bool):
        self._tray_state.recording_exists = exists
        self._refresh_menu()

    def set_auto_enter(self, enabled: bool):
        self._tray_state.auto_enter = enabled
        self._refresh_menu()

    def _refresh_icon(self):
        if self._icon:
            self._icon.icon = self._icon_gen.generate(
                self._tray_state.state, self._tray_state.paused
            )

    def _refresh_menu(self):
        if self._icon:
            self._icon.menu = self._menu_builder.build(self._tray_state)

    def _toggle_pause(self, icon=None, item=None):
        self._tray_state = self._tray_state.with_paused(not self._tray_state.paused)
        self._refresh_icon()
        self._refresh_menu()
        if self._on_toggle_pause:
            self._on_toggle_pause(self._tray_state.paused)

    def _toggle_autostart(self, icon=None, item=None):
        self._tray_state.autostart_enabled = not self._tray_state.autostart_enabled
        self._refresh_menu()
        if self._on_toggle_autostart:
            self._on_toggle_autostart(self._tray_state.autostart_enabled)

    def _toggle_save_audio(self, icon=None, item=None):
        self._tray_state.save_audio = not self._tray_state.save_audio
        self._refresh_menu()
        if self._on_toggle_save_audio:
            self._on_toggle_save_audio(self._tray_state.save_audio)

    def _toggle_auto_enter(self, icon=None, item=None):
        self._tray_state.auto_enter = not self._tray_state.auto_enter
        self._refresh_menu()
        if self._on_toggle_auto_enter:
            self._on_toggle_auto_enter(self._tray_state.auto_enter)

    def _quit(self, icon=None, item=None):
        logger.info("Натиснуто вихід у треї. Зупиняю іконку трею...")
        if self._icon:
            self._icon.stop()
        if self._on_quit:
            self._on_quit()

    def start(self):
        logger.info("Запуск потоку іконки трею...")
        self._icon = pystray.Icon(
            name="vox",
            icon=self._icon_gen.generate(self._tray_state.state, self._tray_state.paused),
            title=self._title,
            menu=self._menu_builder.build(self._tray_state),
        )
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()
        logger.info("Потік трею запущено!")

    def stop(self):
        if self._icon:
            self._icon.stop()

    @property
    def thread(self):
        return self._thread

    @property
    def save_audio(self):
        return self._tray_state.save_audio
