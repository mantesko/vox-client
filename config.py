import os
import json
from dotenv import load_dotenv

load_dotenv()

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
INITIAL_PROMPT = os.getenv("VOX_INITIAL_PROMPT", "")

# Log level for the client.
# Configure this with VOX_LOG_LEVEL (e.g. DEBUG, INFO, WARNING).
LOG_LEVEL = os.getenv("VOX_LOG_LEVEL", "INFO")
LANGUAGE = "uk"
HOTKEY = "<ctrl>+<space>"
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUTO_ENTER = True
INJECTION_METHOD = "auto"

_SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".vox_settings.json")
_DEFAULTS = {
    "language": "uk",
    "auto_enter": True,
    "initial_prompt": "",
}

def _load_settings() -> dict:
    try:
        with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        merged = {**_DEFAULTS, **saved}
        return merged
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(_DEFAULTS)

def _save_settings(data: dict):
    with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_menu_settings():
    global LANGUAGE, AUTO_ENTER, INITIAL_PROMPT
    s = _load_settings()
    LANGUAGE = s["language"]
    AUTO_ENTER = s["auto_enter"]
    INITIAL_PROMPT = s["initial_prompt"]

def save_menu_settings(**kwargs):
    global LANGUAGE, AUTO_ENTER, INITIAL_PROMPT
    s = _load_settings()
    if "language" in kwargs:
        LANGUAGE = kwargs["language"]
        s["language"] = kwargs["language"]
    if "auto_enter" in kwargs:
        AUTO_ENTER = kwargs["auto_enter"]
        s["auto_enter"] = kwargs["auto_enter"]
    if "initial_prompt" in kwargs:
        INITIAL_PROMPT = kwargs["initial_prompt"]
        s["initial_prompt"] = kwargs["initial_prompt"]
    _save_settings(s)

load_menu_settings()
