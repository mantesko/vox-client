from dataclasses import dataclass


@dataclass
class TrayState:
    paused: bool = False
    last_text: str = ""
    autostart_enabled: bool = False
    save_audio: bool = False
    recording_exists: bool = False
    auto_enter: bool = True
    state: str = "listening"

    def with_state(self, state: str) -> "TrayState":
        s = self.__copy__()
        s.state = state
        return s

    def with_paused(self, paused: bool) -> "TrayState":
        s = self.__copy__()
        s.paused = paused
        if not paused and s.state == "idle":
            s.state = "listening"
        elif paused:
            s.state = "idle"
        return s

    def __copy__(self) -> "TrayState":
        return TrayState(
            paused=self.paused,
            last_text=self.last_text,
            autostart_enabled=self.autostart_enabled,
            save_audio=self.save_audio,
            recording_exists=self.recording_exists,
            auto_enter=self.auto_enter,
            state=self.state,
        )
