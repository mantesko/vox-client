from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class AudioConfig:
    """Audio configuration value object"""
    sample_rate: int
    channels: int
    dtype: str
    block_size: int

@dataclass(frozen=True)
class ServerConfig:
    """Server connection configuration"""
    ws_url: str
    language: str

@dataclass(frozen=True)
class HotkeyConfig:
    """Hotkey configuration value object"""
    combination: str

@dataclass(frozen=True)
class RecordingState:
    """Immutable recording state"""
    status: Literal["idle", "listening", "recording"]
    is_voice_enabled: bool
    
    def with_status(self, new_status: Literal["idle", "listening", "recording"]) -> 'RecordingState':
        """Create new state with updated status"""
        return RecordingState(status=new_status, is_voice_enabled=self.is_voice_enabled)
    
    def with_voice_enabled(self, enabled: bool) -> 'RecordingState':
        """Create new state with updated voice activation"""
        return RecordingState(status=self.status, is_voice_enabled=enabled)

@dataclass(frozen=True)
class TranscriptionResult:
    """Immutable transcription result"""
    text: str
    is_final: bool
    confidence: float = 0.0
