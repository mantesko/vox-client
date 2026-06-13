import tkinter as tk
from tkinter import ttk
import logging

import config

logger = logging.getLogger("VoxPreferences")

LANGUAGES = [("Українська", "uk"), ("English", "en")]
LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]


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
        self.prompt_var = tk.StringVar(value=config.INITIAL_PROMPT)
        self.prompt_text = tk.Text(frame, height=3, width=50, wrap="word")
        self.prompt_text.grid(row=row, column=1, columnspan=2, sticky="ew", pady=(0, 4))
        self.prompt_text.insert("1.0", config.INITIAL_PROMPT)
        row += 1

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=row, column=0, columnspan=3, pady=(12, 0), sticky="e")
        ttk.Button(btn_frame, text="Cancel", command=self._cancel).pack(side="right", padx=(8, 0))
        ttk.Button(btn_frame, text="Save", command=self._save).pack(side="right")

        frame.columnconfigure(1, weight=1)

        self.root.protocol("WM_DELETE_WINDOW", self._cancel)
        self.root.grab_set()

    def _toggle_key_visibility(self):
        self.api_key_entry.configure(show="" if self.show_key_var.get() else "*")

    def _save(self):
        settings = {
            "server_url": self.server_var.get().strip(),
            "language": self.language_var.get(),
            "hotkey": self.hotkey_var.get().strip(),
            "api_key": self.api_key_var.get().strip(),
            "log_level": self.log_level_var.get(),
            "initial_prompt": self.prompt_text.get("1.0", "end-1c").strip(),
        }
        config.save_settings(**settings)
        logger.info(f"Preferences saved")
        if self.on_save:
            self.on_save(settings)
        self.root.destroy()

    def _cancel(self):
        self.root.destroy()
