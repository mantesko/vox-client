from abc import ABC, abstractmethod
from typing import Optional, List
from .entities import AudioChunk, TranscriptionResult, RecordingSession
from .value_objects import AudioConfig, ServerConfig

class AudioStreamRepository(ABC):
    """Repository interface for audio stream operations"""
    
    @abstractmethod
    def start_stream(self) -> None:
        """Start audio stream"""
        pass
    
    @abstractmethod
    def stop_stream(self) -> None:
        """Stop audio stream"""
        pass
    
    @abstractmethod
    def get_audio_chunk(self, timeout: float) -> Optional[bytes]:
        """Get audio chunk from stream"""
        pass
    
    @abstractmethod
    def clear_buffer(self) -> None:
        """Clear audio buffer"""
        pass
    
    @abstractmethod
    def set_recording_mode(self, enabled: bool) -> None:
        """Set recording mode"""
        pass

class TextInjectionRepository(ABC):
    """Repository interface for text injection operations"""
    
    @abstractmethod
    def inject_text(self, text: str) -> None:
        """Inject text into active application"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if injection is available"""
        pass

class TranscriptionRepository(ABC):
    """Repository interface for transcription operations"""
    
    @abstractmethod
    async def transcribe_stream(self, audio_data: bytes, language: str) -> TranscriptionResult:
        """Transcribe audio data"""
        pass
    
    @abstractmethod
    async def finalize_transcription(self, audio_data: bytes, language: str) -> TranscriptionResult:
        """Finalize transcription of audio data"""
        pass

class SessionRepository(ABC):
    """Repository interface for session management"""
    
    @abstractmethod
    def create_session(self, language: str = "uk") -> RecordingSession:
        """Create new recording session"""
        pass
    
    @abstractmethod
    def save_session(self, session: RecordingSession) -> None:
        """Save session state"""
        pass
    
    @abstractmethod
    def get_active_session(self) -> Optional[RecordingSession]:
        """Get active recording session"""
        pass
