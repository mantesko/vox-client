import queue
import logging
from typing import Optional
import sounddevice as sd
from ..domain.entities import AudioStreamRepository
from ..domain.value_objects import AudioConfig

logger = logging.getLogger("AudioRepository")

class SoundDeviceAudioRepository(AudioStreamRepository):
    """Concrete implementation of audio repository using sounddevice"""
    
    def __init__(self, config: AudioConfig):
        self._config = config
        self._stream: Optional[sd.InputStream] = None
        self._audio_queue: queue.Queue[bytes] = queue.Queue()
        self._recording_enabled = False
    
    def _audio_callback(self, indata, frames, time_info, status) -> None:
        """Audio callback for sounddevice stream"""
        if self._recording_enabled:
            self._audio_queue.put(bytes(indata))
    
    def start_stream(self) -> None:
        """Start audio input stream"""
        if self._stream is not None:
            return
            
        self._stream = sd.InputStream(
            samplerate=self._config.sample_rate,
            channels=self._config.channels,
            dtype=self._config.dtype,
            blocksize=self._config.block_size,
            callback=self._audio_callback
        )
        self._stream.start()
        logger.info("Audio stream started")
    
    def stop_stream(self) -> None:
        """Stop audio input stream"""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            logger.info("Audio stream stopped")
    
    def get_audio_chunk(self, timeout: float) -> Optional[bytes]:
        """Get audio chunk from queue"""
        try:
            return self._audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def clear_buffer(self) -> None:
        """Clear audio buffer"""
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break
    
    def set_recording_mode(self, enabled: bool) -> None:
        """Enable or disable recording mode"""
        self._recording_enabled = enabled
