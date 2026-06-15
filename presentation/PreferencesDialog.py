import tkinter as tk
from tkinter import ttk
import logging

import config

logger = logging.getLogger("VoxPreferences")

LANGUAGES = [("Українська", "uk"), ("English", "en")]
LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]
PROVIDERS = [("Groq", "groq"), ("Google Gemini", "gemini")]

DEFAULT_PROMPT = (
    "Ти — експерт із редагування українського тексту. Твоє завдання — зробити "
    "пост-обробку тексту, отриманого після розпізнавання мовлення (STT). "
    "Виправ друкарські помилки, граматику, пунктуацію та розбий текст на логічні абзаци, "
    "якщо це необхідно. Зберігай оригінальний зміст, тон та мову (українську). "
    "НЕ додавай жодних коментарів від себе. Виводь ТІЛЬКИ чистий виправлений текст."
)


class PreferencesDialog:
    def __init__(self, on_save=None):
        self.on_save = on_save
        self.root = None

    def show(self):
        self.root = tk.Toplevel()
        self.root.title("Vox - Preferences")
        self.root.resizable(False, False)
        self.root.configure(bg="#f5f5f5")
        self.root.attributes("-topmost", True)

        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)

        row = 0

        ttk.Label(frame, text="Server URL:").grid(row=row, column=0, sticky="w", pady=(0, 4))
        self.server_var = tk.StringVar(value=config.SERVER_BASE_URL)
        ttk.Entry(frame, textvariable=self.server_var, width=50).grid(row=row, column=1, sticky="ew", pady=(0, 4))
        row += 1

        ttk.Label(frame, text="Language:").grid(row=row, column=0, sticky="w", pady=(0, 4))
        self.language_var = tk.StringVar(value=config.LANGUAGE)
        lang_frame = ttk.Frame(frame)
        lang_frame.grid(row=row, column=1, sticky="ew", pady=(0, 4))
        for label, code in LANGUAGES:
            ttk.Radiobutton(lang_frame, text=label, variable=self.language_var, value=code).pack(side="left", padx=(0, 8))
        row += 1

        ttk.Label(frame, text="Hotkey:").grid(row=row, column=0, sticky="w", pady=(0, 4))
        self.hotkey_var = tk.StringVar(value=config.HOTKEY)
        ttk.Entry(frame, textvariable=self.hotkey_var, width=30).grid(row=row, column=1, sticky="w", pady=(0, 4))
        row += 1

        ttk.Label(frame, text="API Key:").grid(row=row, column=0, sticky="w", pady=(0, 4))
        self.api_key_var = tk.StringVar(value=config.API_KEY)
        self.api_key_entry = ttk.Entry(frame, textvariable=self.api_key_var, width=50, show="*")
        self.api_key_entry.grid(row=row, column=1, sticky="ew", pady=(0, 4))
        self.show_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Show", variable=self.show_key_var, command=self._toggle_key_visibility).grid(row=row, column=2, padx=(4, 0))
        row += 1

        ttk.Label(frame, text="Log Level:").grid(row=row, column=0, sticky="w", pady=(0, 4))
        self.log_level_var = tk.StringVar(value=config.LOG_LEVEL)
        ttk.Combobox(frame, textvariable=self.log_level_var, values=LOG_LEVELS, state="readonly", width=12).grid(row=row, column=1, sticky="w", pady=(0, 4))
        row += 1

        ttk.Label(frame, text="Initial Prompt:").grid(row=row, column=0, sticky="nw", pady=(0, 4))
        self.prompt_text = tk.Text(frame, height=3, width=50, wrap="word")
        self.prompt_text.grid(row=row, column=1, columnspan=2, sticky="ew", pady=(0, 4))
        self.prompt_text.insert("1.0", config.INITIAL_PROMPT)
        row += 1

        ttk.Separator(frame, orient="horizontal").grid(row=row, column=0, columnspan=3, sticky="ew", pady=(8, 8))
        row += 1

        self.post_process_var = tk.BooleanVar(value=config.POST_PROCESS)
        ttk.Checkbutton(
            frame, text="Пост-обробка тексту (LLM)", variable=self.post_process_var,
            command=self._toggle_provider_fields
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))
        row += 1

        self.provider_label = ttk.Label(frame, text="Провайдер:")
        self.provider_label.grid(row=row, column=0, sticky="w", pady=(0, 4))
        self.provider_var = tk.StringVar(value=config.POST_PROCESS_PROVIDER)
        self.provider_combo = ttk.Combobox(frame, textvariable=self.provider_var, values=[v for _, v in PROVIDERS], state="readonly", width=15)
        self.provider_combo.grid(row=row, column=1, sticky="w", pady=(0, 4))
        self.provider_combo.bind("<<ComboboxSelected>>", lambda e: self._toggle_provider_fields())
        row += 1

        self._build_groq_fields(frame, row)
        row += 5

        self._build_gemini_fields(frame, row)
        row += 5

        self._toggle_provider_fields()

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=row, column=0, columnspan=3, pady=(12, 0), sticky="e")
        ttk.Button(btn_frame, text="Cancel", command=self._cancel).pack(side="right", padx=(8, 0))
        ttk.Button(btn_frame, text="Save", command=self._save).pack(side="right")

        frame.columnconfigure(1, weight=1)

        self.root.protocol("WM_DELETE_WINDOW", self._cancel)
        self.root.grab_set()

    def _build_groq_fields(self, frame, start_row):
        self.groq_frame = ttk.Frame(frame)

        r = 0
        ttk.Label(self.groq_frame, text="API Key:").grid(row=r, column=0, sticky="w", pady=(0, 4))
        self.groq_api_key_var = tk.StringVar(value=config.GROQ_API_KEY)
        self.groq_key_entry = ttk.Entry(self.groq_frame, textvariable=self.groq_api_key_var, width=50, show="*")
        self.groq_key_entry.grid(row=r, column=1, sticky="ew", pady=(0, 4))
        self.show_groq_key_var = tk.BooleanVar(value=False)
        self.groq_show_btn = ttk.Checkbutton(self.groq_frame, text="Show", variable=self.show_groq_key_var, command=self._toggle_groq_key_visibility)
        self.groq_show_btn.grid(row=r, column=2, padx=(4, 0))
        r += 1

        ttk.Label(self.groq_frame, text="Промпт:").grid(row=r, column=0, sticky="nw", pady=(0, 4))
        self.groq_prompt_text = tk.Text(self.groq_frame, height=3, width=50, wrap="word")
        self.groq_prompt_text.grid(row=r, column=1, columnspan=2, sticky="ew", pady=(0, 4))
        self.groq_prompt_text.insert("1.0", config.GROQ_PROMPT or DEFAULT_PROMPT)
        r += 1

        ttk.Label(self.groq_frame, text="Модель:").grid(row=r, column=0, sticky="w", pady=(0, 4))
        self.groq_model_var = tk.StringVar(value=config.GROQ_MODEL)
        self.groq_model_entry = ttk.Entry(self.groq_frame, textvariable=self.groq_model_var, width=30)
        self.groq_model_entry.grid(row=r, column=1, sticky="w", pady=(0, 4))
        r += 1

        ttk.Label(self.groq_frame, text="Temperature:").grid(row=r, column=0, sticky="w", pady=(0, 4))
        self.groq_temperature_var = tk.StringVar(value=str(config.GROQ_TEMPERATURE))
        self.groq_temperature_entry = ttk.Entry(self.groq_frame, textvariable=self.groq_temperature_var, width=10)
        self.groq_temperature_entry.grid(row=r, column=1, sticky="w", pady=(0, 4))

        self.groq_frame.grid(row=start_row, column=0, columnspan=3, sticky="ew")

    def _build_gemini_fields(self, frame, start_row):
        self.gemini_frame = ttk.Frame(frame)

        r = 0
        ttk.Label(self.gemini_frame, text="API Key:").grid(row=r, column=0, sticky="w", pady=(0, 4))
        self.gemini_api_key_var = tk.StringVar(value=config.GEMINI_API_KEY)
        self.gemini_key_entry = ttk.Entry(self.gemini_frame, textvariable=self.gemini_api_key_var, width=50, show="*")
        self.gemini_key_entry.grid(row=r, column=1, sticky="ew", pady=(0, 4))
        self.show_gemini_key_var = tk.BooleanVar(value=False)
        self.gemini_show_btn = ttk.Checkbutton(self.gemini_frame, text="Show", variable=self.show_gemini_key_var, command=self._toggle_gemini_key_visibility)
        self.gemini_show_btn.grid(row=r, column=2, padx=(4, 0))
        r += 1

        ttk.Label(self.gemini_frame, text="Промпт:").grid(row=r, column=0, sticky="nw", pady=(0, 4))
        self.gemini_prompt_text = tk.Text(self.gemini_frame, height=3, width=50, wrap="word")
        self.gemini_prompt_text.grid(row=r, column=1, columnspan=2, sticky="ew", pady=(0, 4))
        self.gemini_prompt_text.insert("1.0", config.GEMINI_PROMPT or DEFAULT_PROMPT)
        r += 1

        ttk.Label(self.gemini_frame, text="Модель:").grid(row=r, column=0, sticky="w", pady=(0, 4))
        self.gemini_model_var = tk.StringVar(value=config.GEMINI_MODEL)
        self.gemini_model_entry = ttk.Entry(self.gemini_frame, textvariable=self.gemini_model_var, width=30)
        self.gemini_model_entry.grid(row=r, column=1, sticky="w", pady=(0, 4))
        r += 1

        ttk.Label(self.gemini_frame, text="Temperature:").grid(row=r, column=0, sticky="w", pady=(0, 4))
        self.gemini_temperature_var = tk.StringVar(value=str(config.GEMINI_TEMPERATURE))
        self.gemini_temperature_entry = ttk.Entry(self.gemini_frame, textvariable=self.gemini_temperature_var, width=10)
        self.gemini_temperature_entry.grid(row=r, column=1, sticky="w", pady=(0, 4))

        self.gemini_frame.grid(row=start_row, column=0, columnspan=3, sticky="ew")

    def _toggle_key_visibility(self):
        self.api_key_entry.configure(show="" if self.show_key_var.get() else "*")

    def _toggle_groq_key_visibility(self):
        self.groq_key_entry.configure(show="" if self.show_groq_key_var.get() else "*")

    def _toggle_gemini_key_visibility(self):
        self.gemini_key_entry.configure(show="" if self.show_gemini_key_var.get() else "*")

    def _toggle_provider_fields(self):
        enabled = self.post_process_var.get()
        provider = self.provider_var.get()

        for w in [self.provider_label, self.provider_combo]:
            w.configure(state="normal" if enabled else "disabled")

        groq_state = "normal" if enabled and provider == "groq" else "disabled"
        for w in [self.groq_key_entry, self.groq_prompt_text, self.groq_show_btn,
                  self.groq_model_entry, self.groq_temperature_entry]:
            w.configure(state=groq_state)

        gemini_state = "normal" if enabled and provider == "gemini" else "disabled"
        for w in [self.gemini_key_entry, self.gemini_prompt_text, self.gemini_show_btn,
                  self.gemini_model_entry, self.gemini_temperature_entry]:
            w.configure(state=gemini_state)

    def _save(self):
        enabled = self.post_process_var.get()
        provider = self.provider_var.get() if enabled else ""

        settings = {
            "server_url": self.server_var.get().strip(),
            "language": self.language_var.get(),
            "hotkey": self.hotkey_var.get().strip(),
            "api_key": self.api_key_var.get().strip(),
            "log_level": self.log_level_var.get(),
            "initial_prompt": self.prompt_text.get("1.0", "end-1c").strip(),
            "post_process": enabled,
            "post_process_provider": provider,
            "groq_api_key": self.groq_api_key_var.get().strip() if provider == "groq" else "",
            "groq_prompt": self.groq_prompt_text.get("1.0", "end-1c").strip() if provider == "groq" else "",
            "groq_model": self.groq_model_var.get().strip() if provider == "groq" else "llama-3.3-70b-versatile",
            "groq_temperature": float(self.groq_temperature_var.get().strip()) if provider == "groq" else 0.2,
            "gemini_api_key": self.gemini_api_key_var.get().strip() if provider == "gemini" else "",
            "gemini_prompt": self.gemini_prompt_text.get("1.0", "end-1c").strip() if provider == "gemini" else "",
            "gemini_model": self.gemini_model_var.get().strip() if provider == "gemini" else "gemini-2.0-flash",
            "gemini_temperature": float(self.gemini_temperature_var.get().strip()) if provider == "gemini" else 0.2,
        }
        config.save_settings(**settings)
        logger.info(f"Preferences saved")
        if self.on_save:
            self.on_save(settings)
        self.root.destroy()

    def _cancel(self):
        self.root.destroy()
