from typing import Protocol, AsyncGenerator
from .entities import RecordingSession, AudioStreamRepository, TextInjectionRepository, TranscriptionRepository
from .value_objects import TranscriptionResult, ServerConfig

class RecordingSessionService:
    """Domain service for managing recording sessions"""
    
    def __init__(
        self,
        audio_repo: AudioStreamRepository,
        injection_repo: TextInjectionRepository,
        transcription_repo: TranscriptionRepository
    ):
        self._audio_repo = audio_repo
        self._injection_repo = injection_repo
        self._transcription_repo = transcription_repo
    
    async def start_recording_session(
        self, 
        session: RecordingSession,
        server_config: ServerConfig
    ) -> AsyncGenerator[TranscriptionResult, None]:
        """Start recording session and yield transcription results"""
        if not session.state.is_voice_enabled:
            return
            
        # Start audio capture
        self._audio_repo.clear_buffer()
        self._audio_repo.set_recording_mode(True)
        
        try:
            # Stream audio and get transcriptions
            while True:
                audio_chunk = self._audio_repo.get_audio_chunk(timeout=0.2)
                if audio_chunk is None:
                    break
                    
                result = await self._transcription_repo.transcribe_stream(
                    audio_chunk, 
                    server_config.language
                )
                yield result
                
                if result.is_final:
                    break
                    
        finally:
            self._audio_repo.set_recording_mode(False)
    
    def inject_transcription_result(self, result: TranscriptionResult) -> None:
        """Inject transcription result as text"""
        if result.text and result.is_final:
            self._injection_repo.inject_text(result.text)

class VoiceActivationService:
    """Domain service for voice activation management"""
    
    def can_activate_voice(self, session: RecordingSession) -> bool:
        """Check if voice can be activated"""
        return (
            session.state.is_voice_enabled and 
            session.state.status in ["idle", "listening"]
        )
    
    def should_show_overlay(self, session: RecordingSession) -> bool:
        """Check if overlay should be shown"""
        return session.state.status == "recording"
