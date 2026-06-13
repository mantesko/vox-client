import tkinter as tk
import logging
import ctypes
import ctypes.util
from typing import Callable, List, Dict, Any, Optional

logger = logging.getLogger("VoxMenu")


def _init_x11():
    try:
        xlib = ctypes.CDLL(ctypes.util.find_library("X11"))
        xlib.XOpenDisplay.argtypes = [ctypes.c_char_p]
        xlib.XOpenDisplay.restype = ctypes.c_void_p
        dpy = xlib.XOpenDisplay(None)
        if not dpy:
            return None, None

        xlib.XGetInputFocus.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_int),
        ]
        xlib.XGetInputFocus.restype = ctypes.c_int
        return xlib, dpy
    except Exception:
        return None, None


def _get_x11_focus_window(xlib, dpy) -> int:
    focus_return = ctypes.c_ulong()
    revert_to = ctypes.c_int()
    xlib.XGetInputFocus(dpy, ctypes.byref(focus_return), ctypes.byref(revert_to))
    return focus_return.value


class VoxMenu(tk.Toplevel):
    def __init__(self, parent, title="Vox - Hands-Free", on_action: Callable = None):
        super().__init__(parent)
        self.parent = parent
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg="#ffffff", bd=0, highlightthickness=0)
        self.withdraw()

        self.title_text = title
        self.current_menu_data = []
        self.menu_stack = []

        self._menu_bg = "#ffffff"
        self._hover_bg = "#f0f0f0"
        self._fg = "#1a1a1a"
        self._disabled_fg = "#999999"
        self._separator_color = "#e0e0e0"
        self._accent = "#2196F3"

        self.bind("<Escape>", lambda e: self.hide())

        self._poll_after_id = None
        self._my_focus_wid = None
        self._xlib, self._x11_dpy = _init_x11()

        self._click_listener = None
        self._click_listener_active = False

    def set_data(self, menu_data: List[Dict]):
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

        tk.Frame(self, bg=self._menu_bg, height=6).pack(fill="x")

        if self.menu_stack:
            back_frame = tk.Frame(self, bg=self._menu_bg)
            back_frame.pack(fill="x", padx=10, pady=(2, 0))
            back_btn = tk.Label(back_frame, text="\u2190", bg=self._menu_bg, fg=self._accent,
                                font=("Sans", 12, "bold"), cursor="hand2", padx=4)
            back_btn.pack(side="left")
            back_btn.bind("<Button-1>", lambda e: self._go_back())

        data = self.menu_stack[-1] if self.menu_stack else self.current_menu_data

        for menu_item in data:
            if menu_item.get("separator"):
                sep_wrapper = tk.Frame(self, bg=self._menu_bg)
                sep_wrapper.pack(fill="x")
                tk.Frame(sep_wrapper, bg=self._separator_color, height=1).pack(fill="x", padx=12, pady=4)
                continue

            frame = tk.Frame(self, bg=self._menu_bg, cursor="hand2")
            frame.pack(fill="x", padx=8, pady=1)

            label = menu_item.get("label", "")
            checked = menu_item.get("checked", False)
            enabled = menu_item.get("enabled", True)
            submenu = menu_item.get("submenu")
            callback = menu_item.get("callback")

            inner = tk.Frame(frame, bg=self._menu_bg)
            inner.pack(fill="x", padx=8, pady=5)

            if checked:
                lbl_check = tk.Label(inner, text="\u2713", bg=self._menu_bg, fg=self._accent,
                                     font=("Sans", 11), width=2, anchor="w")
                lbl_check.pack(side="left")

            lbl_text = tk.Label(inner, text=label, bg=self._menu_bg,
                                fg=self._fg if enabled else self._disabled_fg,
                                anchor="w", font=("Sans", 10), padx=4)
            lbl_text.pack(side="left", fill="x", expand=True)

            if submenu:
                lbl_arrow = tk.Label(inner, text="\u203a", bg=self._menu_bg, fg=self._disabled_fg,
                                     font=("Sans", 14))
                lbl_arrow.pack(side="right")

            if enabled:
                def make_enter(f):
                    return lambda e: f.configure(bg=self._hover_bg)

                def make_leave(f):
                    return lambda e: f.configure(bg=self._menu_bg)

                for w in [frame, inner, lbl_text]:
                    w.bind("<Enter>", make_enter(frame))
                    w.bind("<Leave>", make_leave(frame))

                if submenu:
                    def make_sub(s):
                        return lambda e: self._go_to_submenu(s)
                    h = make_sub(submenu)
                    for w in [frame, inner, lbl_text]:
                        w.bind("<Button-1>", h)
                elif callback:
                    def make_cb(c):
                        def handler(e):
                            self.hide()
                            c()
                        return handler
                    h = make_cb(callback)
                    for w in [frame, inner, lbl_text]:
                        w.bind("<Button-1>", h)

        tk.Frame(self, bg=self._menu_bg, height=6).pack(fill="x")

        self.update_idletasks()

    def _start_click_listener(self):
        if self._click_listener_active:
            return

        def on_click(x, y, button, pressed):
            if not pressed:
                return
            if not self.winfo_ismapped():
                return

            mx1 = self.winfo_rootx()
            my1 = self.winfo_rooty()
            mx2 = mx1 + self.winfo_width()
            my2 = my1 + self.winfo_height()

            if not (mx1 <= x <= mx2 and my1 <= y <= my2):
                self.after(0, self.hide)

        try:
            from pynput import mouse
            self._click_listener = mouse.Listener(on_click=on_click)
            self._click_listener.daemon = True
            self._click_listener.start()
            self._click_listener_active = True
        except ImportError:
            logger.warning("pynput not available, click-outside detection limited")
        except Exception as e:
            logger.warning(f"Failed to start click listener: {e}")

    def _stop_click_listener(self):
        if self._click_listener:
            try:
                self._click_listener.stop()
            except Exception:
                pass
            self._click_listener = None
            self._click_listener_active = False

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
        self.update_idletasks()
        self.focus_force()

        self._my_focus_wid = _get_x11_focus_window(self._xlib, self._x11_dpy) if self._xlib else None

        self._start_click_listener()
        self._start_poll()

    def _start_poll(self):
        if self._poll_after_id is not None:
            self.after_cancel(self._poll_after_id)
        self._poll_after_id = self.after(200, self._poll_focus)

    def _poll_focus(self):
        if not self.winfo_ismapped():
            self._stop_click_listener()
            return

        if self._xlib:
            current_focus = _get_x11_focus_window(self._xlib, self._x11_dpy)
            if self._my_focus_wid and current_focus != self._my_focus_wid:
                self.hide()
                return
        else:
            try:
                focused = self.focus_get()
                if focused is None:
                    self.hide()
                    return
            except KeyError:
                self.hide()
                return

        self._poll_after_id = self.after(100, self._poll_focus)

    def hide(self):
        if not self.winfo_ismapped():
            return

        logger.info("Hiding menu")

        if self._poll_after_id is not None:
            self.after_cancel(self._poll_after_id)
            self._poll_after_id = None

        self._stop_click_listener()
        self.withdraw()
        if self.parent:
            self.parent.focus_force()
