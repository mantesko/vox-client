import tkinter as tk
import logging
from typing import Callable, List, Dict, Any, Optional

logger = logging.getLogger("VoxMenu")

class VoxMenu(tk.Toplevel):
    def __init__(self, parent, title="Vox - Hands-Free", on_action: Callable = None):
        super().__init__(parent)
        self.parent = parent
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg="#061426", bd=1, highlightbackground="#1e2d3d", highlightthickness=1)
        self.withdraw()

        self.title_text = title
        self.current_menu_data = []
        self.menu_stack = []  # Для навігації підменю

        self.bg = "#061426"
        self.hover_bg = "#1c2c3e"
        self.fg = "#ffffff"
        self.accent = "#8df2ff"
        self.disabled_fg = "#555555"
        self.separator_color = "#1e2d3d"

        self.bind("<Escape>", lambda e: self.hide())

        self._outside_click_bind_id = None
        self._root_click_bind_id = None
        self._poll_after_id = None

    def _on_outside_click(self, event):
        """Приховує меню, якщо клік відбувся поза його межами."""
        if not (self.winfo_rootx() <= event.x_root <= self.winfo_rootx() + self.winfo_width() and
                self.winfo_rooty() <= event.y_root <= self.winfo_rooty() + self.winfo_height()):
            self.hide()

    def set_data(self, menu_data: List[Dict]):
        """
        Встановлює дані меню.
        menu_data: Список словників:
        { "label": str, "callback": func, "checked": bool, "enabled": bool, "submenu": List[Dict], "separator": bool }
        """
        self.current_menu_data = menu_data
        self.menu_stack = []

    def _go_to_submenu(self, submenu_data: List[Dict]):
        self.menu_stack.append(submenu_data)
        self._render()

    def _go_back(self):
        if self.menu_stack:
            self.menu_stack.pop()
            self._render()

    def _render(self):
        for widget in self.winfo_children():
            widget.destroy()

        # Header
        header_frame = tk.Frame(self, bg=self.bg)
        header_frame.pack(fill="x")

        if self.menu_stack:
            back_btn = tk.Label(header_frame, text=" ← ", bg=self.bg, fg=self.accent, font=("Sans", 11, "bold"), cursor="hand2")
            back_btn.pack(side="left", padx=5)
            back_btn.bind("<Button-1>", lambda e: self._go_back())

        title_lbl = tk.Label(header_frame, text=self.title_text, bg=self.bg, fg=self.accent, font=("Sans", 9, "bold"), pady=10)
        title_lbl.pack(side="left", fill="x", expand=True)

        tk.Frame(self, height=1, bg=self.separator_color).pack(fill="x", padx=5)

        data = self.menu_stack[-1] if self.menu_stack else self.current_menu_data

        for item in data:
            if item.get("separator"):
                tk.Frame(self, height=1, bg=self.separator_color).pack(fill="x", padx=5, pady=4)
                continue

            frame = tk.Frame(self, bg=self.bg)
            frame.pack(fill="x")

            label = item.get("label", "")
            checked = item.get("checked", False)
            enabled = item.get("enabled", True)
            submenu = item.get("submenu")
            callback = item.get("callback")

            indicator_text = "●" if checked else " "
            suffix = "  ›" if submenu else ""

            lbl_indicator = tk.Label(frame, text=f" {indicator_text} ", bg=self.bg, fg=self.accent if checked else self.bg, font=("Sans", 10))
            lbl_indicator.pack(side="left")

            lbl_text = tk.Label(frame, text=f"{label}{suffix}", bg=self.bg, fg=self.fg if enabled else self.disabled_fg,
                                anchor="w", padx=5, pady=7, font=("Sans", 10))
            lbl_text.pack(side="left", fill="x", expand=True)

            if enabled:
                def make_on_enter(f, li, lt):
                    return lambda e: [f.configure(bg=self.hover_bg), li.configure(bg=self.hover_bg), lt.configure(bg=self.hover_bg)]

                def make_on_leave(f, li, lt):
                    return lambda e: [f.configure(bg=self.bg), li.configure(bg=self.bg), lt.configure(bg=self.bg)]

                on_enter = make_on_enter(frame, lbl_indicator, lbl_text)
                on_leave = make_on_leave(frame, lbl_indicator, lbl_text)

                frame.bind("<Enter>", on_enter)
                lbl_text.bind("<Enter>", on_enter)
                lbl_indicator.bind("<Enter>", on_enter)

                frame.bind("<Leave>", on_leave)
                lbl_text.bind("<Leave>", on_leave)
                lbl_indicator.bind("<Leave>", on_leave)

                if submenu:
                    frame.bind("<Button-1>", lambda e, s=submenu: self._go_to_submenu(s))
                    lbl_text.bind("<Button-1>", lambda e, s=submenu: self._go_to_submenu(s))
                elif callback:
                    def make_click_handler(c):
                        return lambda e: [self.hide(), c()]

                    handler = make_click_handler(callback)
                    frame.bind("<Button-1>", handler)
                    lbl_text.bind("<Button-1>", handler)

        self.update_idletasks()

    def show(self, x, y):
        self._render()

        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        if x + width > screen_width:
            x = screen_width - width - 10
        if y + height > screen_height:
            y = screen_height - height - 10

        self.geometry(f"+{x}+{y}")
        self.deiconify()
        self.lift()
        self.focus_force()

        root = self.winfo_toplevel()
        if self._outside_click_bind_id is None:
            self._outside_click_bind_id = root.bind("<Button-1>", self._on_outside_click, add="+")
        if self._root_click_bind_id is None:
            self._root_click_bind_id = root.bind("<FocusOut>", lambda e: self.after(50, self.hide), add="+")
        self._start_poll()

    def _start_poll(self):
        if self._poll_after_id is not None:
            self.after_cancel(self._poll_after_id)
        self._poll_after_id = self.after(200, self._poll_focus)

    def _poll_focus(self):
        if not self.winfo_ismapped():
            return
        try:
            focused = self.focus_get()
            if focused is None:
                self.hide()
                return
        except KeyError:
            self.hide()
            return
        self._poll_after_id = self.after(200, self._poll_focus)

    def hide(self):
        if not self.winfo_ismapped():
            return

        logger.info("Hiding menu")

        if self._poll_after_id is not None:
            self.after_cancel(self._poll_after_id)
            self._poll_after_id = None

        root = self.winfo_toplevel()
        if self._outside_click_bind_id is not None:
            root.unbind("<Button-1>", self._outside_click_bind_id)
            self._outside_click_bind_id = None
        if self._root_click_bind_id is not None:
            root.unbind("<FocusOut>", self._root_click_bind_id)
            self._root_click_bind_id = None

        self.withdraw()
        if self.parent:
            self.parent.focus_force()
