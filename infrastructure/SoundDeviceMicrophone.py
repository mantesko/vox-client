import queue
import logging
import threading
import wave
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
        self.silence_threshold = 0.008
        self.consecutive_silence_chunks = 0
        self.max_silence_chunks = 3
        self.consecutive_speech_chunks = 0
        self.min_speech_chunks = 2
        self.is_speaking = False
        self.audio_buffer = deque(maxlen=3)
        self.level_lock = threading.Lock()
        self.last_level = 0.0
        self._wav_file = None
        self._recording_wav = False
        self._hp_b0 = 0.9695
        self._hp_b1 = -0.9390
        self._hp_a1 = -0.8780
        self._hp_prev_x = 0.0
        self._hp_prev_y = 0.0

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

    def _high_pass_filter(self, audio_float: np.ndarray) -> np.ndarray:
        out = np.empty_like(audio_float)
        px, py = self._hp_prev_x, self._hp_prev_y
        b0, b1, a1 = self._hp_b0, self._hp_b1, self._hp_a1
        for i in range(len(audio_float)):
            x = audio_float[i]
            y = b0 * x + b1 * px - a1 * py
            out[i] = y
            px = x
            py = y
        self._hp_prev_x = px
        self._hp_prev_y = py
        return out

    def _detect_silence(self, audio_data: np.ndarray) -> bool:
        audio_float = audio_data.astype(np.float32) / 32768.0
        filtered = self._high_pass_filter(audio_float)
        rms = np.sqrt(np.mean(filtered ** 2))
        return rms < self.silence_threshold

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            logger.warning(f"Audio callback status: {status}")

        if self.route_to_server:
            audio_data = indata.copy().astype(np.int16)
            audio_float = audio_data.astype(np.float32) / 32768.0
            filtered = self._high_pass_filter(audio_float)
            rms = np.sqrt(np.mean(filtered ** 2))
            level = min(1.0, rms * 6.0)
            self._set_last_level(level)

            if rms < self.silence_threshold:
                self.consecutive_silence_chunks += 1
                self.consecutive_speech_chunks = 0
                if self.is_speaking and self.consecutive_silence_chunks > self.max_silence_chunks:
                    self.is_speaking = False
                if not self.is_speaking:
                    self._set_last_level(level * 0.15)
                    return
            else:
                self.consecutive_silence_chunks = 0
                self.consecutive_speech_chunks += 1
                if not self.is_speaking and self.consecutive_speech_chunks >= self.min_speech_chunks:
                    self.is_speaking = True
                self._set_last_level(level)

            normalized = self._normalize_audio(audio_data)
            normalized_int16 = (normalized * 32768.0).astype(np.int16)
            self.server_queue.put(bytes(normalized_int16))

            if self._recording_wav and self._wav_file:
                self._wav_file.writeframes(bytes(normalized_int16))

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

    def start_wav_recording(self, filepath="debug_mic.wav"):
        try:
            self._wav_file = wave.open(filepath, "wb")
            self._wav_file.setnchannels(1)
            self._wav_file.setsampwidth(2)
            self._wav_file.setframerate(self.sample_rate)
            self._recording_wav = True
            logger.info(f"Recording mic to {filepath}")
        except Exception as e:
            logger.error(f"Failed to start WAV recording: {e}")

    def stop_wav_recording(self):
        self._recording_wav = False
        if self._wav_file:
            try:
                self._wav_file.close()
                logger.info("WAV recording saved")
            except Exception as e:
                logger.error(f"Failed to close WAV file: {e}")
            finally:
                self._wav_file = None
