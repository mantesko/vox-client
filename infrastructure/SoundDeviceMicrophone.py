import queue
import logging
import threading
import numpy as np
import sounddevice as sd
from collections import deque

logger = logging.getLogger("MicrophoneManager")

class MicrophoneManager:
    def __init__(self, sample_rate=16000, device=None):
        self.sample_rate = sample_rate
        self.device = device
        self.stream = None
        self.server_queue = queue.Queue()
        self.route_to_server = False
        self.silence_threshold = 0.01  # Adjust based on your environment
        self.consecutive_silence_chunks = 0
        self.max_silence_chunks = 5  # ~0.5 seconds at 16kHz
        self.audio_buffer = deque(maxlen=3)  # Keep last 3 chunks for context
        self.level_lock = threading.Lock()
        self.last_level = 0.0

    def get_last_level(self) -> float:
        with self.level_lock:
            return self.last_level

    def _set_last_level(self, level: float):
        with self.level_lock:
            self.last_level = max(0.0, min(1.0, level))

    def _normalize_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """Normalize audio to -1.0 to 1.0 range"""
        audio_float = audio_data.astype(np.float32) / 32768.0
        # Apply soft normalization to prevent clipping
        max_val = np.max(np.abs(audio_float))
        if max_val > 0:
            audio_float = audio_float / max_val * 0.95
        return audio_float

    def _detect_silence(self, audio_data: np.ndarray) -> bool:
        """Detect if audio chunk is silence using RMS energy"""
        audio_float = audio_data.astype(np.float32) / 32768.0
        rms = np.sqrt(np.mean(audio_float ** 2))
        return rms < self.silence_threshold

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            logger.warning(f"Audio callback status: {status}")

        if self.route_to_server:
            audio_data = indata.copy().astype(np.int16)
            audio_float = audio_data.astype(np.float32) / 32768.0
            rms = np.sqrt(np.mean(audio_float ** 2))
            level = min(1.0, rms * 6.0)
            self._set_last_level(level)

            # Check for silence
            if self._detect_silence(audio_data):
                self.consecutive_silence_chunks += 1
                # Drop consecutive silence chunks (but keep some for context)
                if self.consecutive_silence_chunks > self.max_silence_chunks:
                    self._set_last_level(level * 0.15)
                    return
            else:
                self.consecutive_silence_chunks = 0
                self._set_last_level(level)

            # Normalize and send
            normalized = self._normalize_audio(audio_data)
            # Convert back to int16 for transmission
            normalized_int16 = (normalized * 32768.0).astype(np.int16)
            self.server_queue.put(bytes(normalized_int16))

    def list_input_devices(self):
        """Return a list of available input devices as (id, name)."""
        devices = []
        try:
            for index, info in enumerate(sd.query_devices()):
                if info.get('max_input_channels', 0) > 0:
                    name = info.get('name', f'Input {index}')
                    devices.append((index, name))
        except Exception as e:
            logger.warning(f"Failed to list audio devices: {e}")
        return devices

    def get_current_device_name(self):
        if self.device is None:
            return "Default"
        try:
            info = sd.query_devices(self.device)
            return info.get('name', str(self.device))
        except Exception:
            return str(self.device)

    def set_input_device(self, device):
        self.device = device
        if self.stream:
            self.stop()
            self.start()

    def start(self):
        # 16кГц, моно, int16 - стандарт для Whisper
        if self.stream is not None:
            return
            
        try:
            stream_kwargs = {
                'samplerate': self.sample_rate,
                'channels': 1,
                'dtype': 'int16',
                'blocksize': 1600,
                'callback': self._audio_callback,
                'latency': 'low'
            }
            if self.device is not None:
                stream_kwargs['device'] = self.device

            self.stream = sd.InputStream(**stream_kwargs)
            self.stream.start()
            logger.info(f"Microphone stream started successfully on device: {self.get_current_device_name()}")
        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}")
            raise

    def stop(self):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                logger.error(f"Error stopping stream: {e}")
            finally:
                self.stream = None
        self.clear_queues()
        self._set_last_level(0.0)

    def clear_queues(self):
        while not self.server_queue.empty():
            try:
                self.server_queue.get_nowait()
            except queue.Empty:
                break
