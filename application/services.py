import asyncio
import logging
from typing import Optional
from ..domain.entities import RecordingSession, AudioChunk, TranscriptionResult
from ..domain.services import RecordingSessionService, VoiceActivationService
from ..domain.interfaces import AudioStreamRepository, SessionRepository
from ..domain.value_objects import ServerConfig
from .dto import WebSocketMessage, RecordingSessionDTO, TranscriptionResultDTO

logger = logging.getLogger("VoxApplication")

class WebSocketService:
    """Application service for WebSocket communication"""
    
    def __init__(
        self,
        session_service: RecordingSessionService,
        audio_repo: AudioStreamRepository,
        session_repo: SessionRepository,
        server_config: ServerConfig
    ):
        self.session_service = session_service
        self.audio_repo = audio_repo
        self.session_repo = session_repo
        self.server_config = server_config
    
    async def handle_websocket_connection(self, websocket):
        """Handle WebSocket connection and message processing"""
        audio_buffer = bytearray()
        session = None
        
        try:
            # Initialize session
            init_data = await websocket.receive_json()
            if init_data.get("type") == "start":
                session = await self.session_service.start_recording_session(
                    init_data.get("language", "uk")
                )
            
            # Start transcription loop
            transcription_task = asyncio.create_task(self._transcription_loop(websocket, audio_buffer, session))
            
            # Handle incoming messages
            while True:
                message = await websocket.receive()
                
                if "bytes" in message:
                    audio_buffer.extend(message["bytes"])
                    if session and len(audio_buffer) >= 16000:  # 1 second
                        chunk = AudioChunk(bytes(audio_buffer))
                        session = await self.session_service.process_audio_chunk(session, chunk)
                        audio_buffer.clear()
                        
                        # Start transcription
                        if session.status.value == "recording":
                            session = await self.session_service.transcribe_and_inject(session)
                
                elif "text" in message:
                    data = message["text"]
                    if isinstance(data, str):
                        import json
                        data = json.loads(data)
                    
                    if data.get("type") == "stop" and session:
                        session = await self.session_service.stop_recording_session(session)
                        transcription_task.cancel()
                        break
                        
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            if session:
                await self.session_service.stop_recording_session(session)
    
    async def _transcription_loop(self, websocket, audio_buffer, session):
        """Background task for continuous transcription"""
        while session and session.status.value == "recording":
            await asyncio.sleep(0.3)
            if len(audio_buffer) >= 16000:  # 1 second
                chunk = AudioChunk(bytes(audio_buffer))
                session = await self.session_service.process_audio_chunk(session, chunk)
                audio_buffer.clear()
                
                # Get partial transcription
                if session.audio_chunks:
                    audio_data = b''.join([c.data for c in session.audio_chunks[-10:]])  # Last 10 seconds
                    result = await self.session_service.transcription_repo.transcribe_stream(
                        audio_data, session.language
                    )
                    
                    if result.text:
                        await websocket.send_json({
                            "type": "partial",
                            "text": result.text
                        })

class HotkeyService:
    """Application service for handling hotkey events"""
    
    def __init__(self, session_service: RecordingSessionService):
        self.session_service = session_service
    
    async def toggle_recording(self) -> Optional[RecordingSession]:
        """Toggle recording state"""
        session = self.session_repo.get_active_session()
        
        if session and session.status.value == "recording":
            return await self.session_service.stop_recording_session(session)
        else:
            return await self.session_service.start_recording_session()
