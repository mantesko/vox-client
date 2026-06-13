from pystray import MenuItem as item, Menu

from .state import TrayState


class TrayMenuBuilder:
    def __init__(self, callbacks: dict):
        self._cb = callbacks

    def build(self, tray_state: TrayState) -> Menu:
        pause_label = "Resume recognition" if tray_state.paused else "Pause recognition"

        return Menu(
            item(pause_label, self._cb["toggle_pause"], checked=lambda i: tray_state.paused),
            item("Copy Last Text", self._cb["copy_last_text"], enabled=lambda i: bool(tray_state.last_text)),
            Menu.SEPARATOR,
            item("Preferences...", self._cb["open_preferences"]),
            Menu.SEPARATOR,
            item("Start on Boot", self._cb["toggle_autostart"], checked=lambda i: tray_state.autostart_enabled),
            item("Save Audio", self._cb["toggle_save_audio"], checked=lambda i: tray_state.save_audio),
            item("Auto Enter", self._cb["toggle_auto_enter"], checked=lambda i: tray_state.auto_enter),
            Menu.SEPARATOR,
            item("About", self._cb["about"]),
            item("Quit", self._cb["quit"]),
        )
