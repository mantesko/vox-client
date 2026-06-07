import uuid
import logging
from typing import Optional
from ..domain.entities import RecordingSession, RecordingStatus
from ..domain.interfaces import SessionRepository

logger = logging.getLogger("VoxSession")

class InMemorySessionRepository(SessionRepository):
    """In-memory implementation of session repository"""
    
    def __init__(self):
        self.sessions = {}
        self.active_session_id = None
    
    def create_session(self, language: str = "uk") -> RecordingSession:
        """Create new recording session"""
        session_id = str(uuid.uuid4())
        session = RecordingSession(
            id=session_id,
            language=language,
            status=RecordingStatus.IDLE
        )
        self.sessions[session_id] = session
        logger.info(f"Created session: {session_id}")
        return session
    
    def save_session(self, session: RecordingSession) -> None:
        """Save session state"""
        self.sessions[session.id] = session
        if session.status != RecordingStatus.IDLE:
            self.active_session_id = session.id
        logger.debug(f"Saved session: {session.id}")
    
    def get_active_session(self) -> Optional[RecordingSession]:
        """Get active recording session"""
        if self.active_session_id and self.active_session_id in self.sessions:
            return self.sessions[self.active_session_id]
        return None
    
    def get_session(self, session_id: str) -> Optional[RecordingSession]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> None:
        """Delete session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            if self.active_session_id == session_id:
                self.active_session_id = None
            logger.info(f"Deleted session: {session_id}")
