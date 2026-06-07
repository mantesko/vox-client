from dataclasses import dataclass
from typing import Protocol, Optional
from .value_objects import RecordingState, TranscriptionResult

class AudioStreamRepository(Protocol):
    """Repository interface for audio stream operations"""
    def start_stream(self) -> None: ...
    def stop_stream(self) -> None: ...
    def get_audio_chunk(self, timeout: float) -> Optional[bytes]: ...
    def clear_buffer(self) -> None: ...
    def set_recording_mode(self, enabled: bool) -> None: ...

class TextInjectionRepository(Protocol):
    """Repository interface for text injection operations"""
    def inject_text(self, text: str) -> None: ...
    def is_available(self) -> bool: ...

class TranscriptionRepository(Protocol):
    """Repository interface for transcription operations"""
    async def transcribe_stream(self, audio_data: bytes, language: str) -> TranscriptionResult: ...
    async def finalize_transcription(self, audio_data: bytes, language: str) -> TranscriptionResult: ...

@dataclass(frozen=True)
class RecordingSession:
    """Domain entity representing a recording session"""
    session_id: str
    state: RecordingState
    language: str
    
    def start_recording(self) -> 'RecordingSession':
        """Start recording session"""
        new_state = self.state.with_status("recording")
        return RecordingSession(self.session_id, new_state, self.language)
    
    def stop_recording(self) -> 'RecordingSession':
        """Stop recording session"""
        new_state = self.state.with_status("idle")
        return RecordingSession(self.session_id, new_state, self.language)
    
    def toggle_voice_activation(self) -> 'RecordingSession':
        """Toggle voice activation"""
        new_state = self.state.with_voice_enabled(not self.state.is_voice_enabled)
        return RecordingSession(self.session_id, new_state, self.language)
