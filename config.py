import os
import re

# Список доступних серверів
SERVERS = {
    "remote": "ws://vox.costa.pp.ua/stream",
    "local": "ws://localhost:8002/stream"
}

# Вибір активного сервера через змінну оточення VOX_SERVER_PROFILE (local/remote)
# Якщо не вказано, використовується VOX_SERVER_URL або remote за замовчуванням.
def _resolve_server_url() -> str:
    profile = os.getenv("VOX_SERVER_PROFILE", "remote").lower()
    url = os.getenv("VOX_SERVER_URL", "")
    
    if url:
        return url.rstrip("/")
    
    return SERVERS.get(profile, SERVERS["remote"]).rstrip("/")

SERVER_BASE_URL = _resolve_server_url()
WHISPER_MODEL = os.getenv("VOX_WHISPER_MODEL", "Systran/faster-whisper-small")
API_KEY = os.getenv("VOX_API_KEY", "")

# Log level for the client.
# Configure this with VOX_LOG_LEVEL (e.g. DEBUG, INFO, WARNING).
LOG_LEVEL = os.getenv("VOX_LOG_LEVEL", "INFO")
LANGUAGE = "uk"
HOTKEY = "<ctrl>+<space>"
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUTO_ENTER = True
INJECTION_METHOD = "auto"
