import os
import json

SERVERS = {
    "remote": "ws://vox.costa.pp.ua/stream",
    "local": "ws://localhost:8002/stream"
}

DEFAULT_SERVER_URL = SERVERS["remote"]

AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
INJECTION_METHOD = "auto"

_SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".vox_settings.json")
_DEFAULTS = {
    "language": "uk",
    "auto_enter": True,
    "initial_prompt": "",
    "server_url": DEFAULT_SERVER_URL,
    "hotkey": "<ctrl>+<space>",
    "api_key": "",
    "log_level": "INFO",
    "groq_post_process": False,
    "groq_api_key": "",
    "groq_prompt": "",
    "groq_model": "llama-3.3-70b-versatile",
    "groq_temperature": 0.2,
}

LANGUAGE = _DEFAULTS["language"]
AUTO_ENTER = _DEFAULTS["auto_enter"]
INITIAL_PROMPT = _DEFAULTS["initial_prompt"]
SERVER_BASE_URL = _DEFAULTS["server_url"]
HOTKEY = _DEFAULTS["hotkey"]
API_KEY = _DEFAULTS["api_key"]
LOG_LEVEL = _DEFAULTS["log_level"]
GROQ_POST_PROCESS = _DEFAULTS["groq_post_process"]
GROQ_API_KEY = _DEFAULTS["groq_api_key"]
GROQ_PROMPT = _DEFAULTS["groq_prompt"]
GROQ_MODEL = _DEFAULTS["groq_model"]
GROQ_TEMPERATURE = _DEFAULTS["groq_temperature"]


def _load_settings() -> dict:
    try:
        with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        return {**_DEFAULTS, **saved}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(_DEFAULTS)


def _save_settings(data: dict):
    with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_settings():
    global LANGUAGE, AUTO_ENTER, INITIAL_PROMPT, SERVER_BASE_URL, HOTKEY, API_KEY, LOG_LEVEL
    global GROQ_POST_PROCESS, GROQ_API_KEY, GROQ_PROMPT, GROQ_MODEL, GROQ_TEMPERATURE
    s = _load_settings()
    LANGUAGE = s["language"]
    AUTO_ENTER = s["auto_enter"]
    INITIAL_PROMPT = s["initial_prompt"]
    SERVER_BASE_URL = s["server_url"].rstrip("/")
    HOTKEY = s["hotkey"]
    API_KEY = s["api_key"]
    LOG_LEVEL = s["log_level"]
    GROQ_POST_PROCESS = s["groq_post_process"]
    GROQ_API_KEY = s["groq_api_key"]
    GROQ_PROMPT = s["groq_prompt"]
    GROQ_MODEL = s["groq_model"]
    GROQ_TEMPERATURE = s["groq_temperature"]


def save_settings(**kwargs):
    global LANGUAGE, AUTO_ENTER, INITIAL_PROMPT, SERVER_BASE_URL, HOTKEY, API_KEY, LOG_LEVEL
    global GROQ_POST_PROCESS, GROQ_API_KEY, GROQ_PROMPT, GROQ_MODEL, GROQ_TEMPERATURE
    s = _load_settings()
    for key, value in kwargs.items():
        if key in s:
            s[key] = value
    if "language" in kwargs:
        LANGUAGE = kwargs["language"]
    if "auto_enter" in kwargs:
        AUTO_ENTER = kwargs["auto_enter"]
    if "initial_prompt" in kwargs:
        INITIAL_PROMPT = kwargs["initial_prompt"]
    if "server_url" in kwargs:
        SERVER_BASE_URL = kwargs["server_url"].rstrip("/")
    if "hotkey" in kwargs:
        HOTKEY = kwargs["hotkey"]
    if "api_key" in kwargs:
        API_KEY = kwargs["api_key"]
    if "log_level" in kwargs:
        LOG_LEVEL = kwargs["log_level"]
    if "groq_post_process" in kwargs:
        GROQ_POST_PROCESS = kwargs["groq_post_process"]
    if "groq_api_key" in kwargs:
        GROQ_API_KEY = kwargs["groq_api_key"]
    if "groq_prompt" in kwargs:
        GROQ_PROMPT = kwargs["groq_prompt"]
    if "groq_model" in kwargs:
        GROQ_MODEL = kwargs["groq_model"]
    if "groq_temperature" in kwargs:
        GROQ_TEMPERATURE = kwargs["groq_temperature"]
    _save_settings(s)


load_settings()
