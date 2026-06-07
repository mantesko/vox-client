from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class RecordingSessionDTO:
    """Data transfer object for recording session"""
    id: str
    status: str
    language: str
    created_at: datetime
    updated_at: datetime
    audio_chunks_count: int
    transcription_results_count: int

@dataclass
class TranscriptionResultDTO:
    """Data transfer object for transcription result"""
    text: str
    confidence: float
    language: str
    timestamp: datetime
    is_final: bool

@dataclass
class WebSocketMessage:
    """Data transfer object for WebSocket messages"""
    type: str
    data: Optional[dict] = None
    text: Optional[str] = None
