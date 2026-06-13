import subprocess
import time
import logging
import config

logger = logging.getLogger("VoxInjector")

TERMINAL_WM_CLASSES = {"gnome-terminal", "konsole", "alacritty", "kitty", "xterm", "urxvt", "tilix", "st", "terminator", "yakuake", "wezterm", "foot"}


class TextInjector:
    def __init__(self):
        self.has_xclip = self._has_command("xclip")
        self.has_xdotool = self._has_command("xdotool")
        self.has_xprop = self._has_command("xprop")
        if not self.has_xclip or not self.has_xdotool:
            logger.error("Потрібні xclip та xdotool!")

    def _get_clipboard(self) -> bytes:
        try:
            result = subprocess.run(
                ['xclip', '-selection', 'clipboard', '-o'],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=2
            )
            return result.stdout if result.returncode == 0 else b""
        except Exception:
            return b""

    def _set_clipboard(self, data: bytes):
        subprocess.run(
            ['xclip', '-selection', 'clipboard'],
            input=data, check=True, timeout=2
        )

    def _is_terminal(self) -> bool:
        try:
            wid = subprocess.check_output(
                ["xdotool", "getactivewindow"],
                stderr=subprocess.DEVNULL, timeout=2
            ).strip().decode()
            wm_class = subprocess.check_output(
                ["xprop", "-id", wid, "WM_CLASS"],
                stderr=subprocess.DEVNULL, timeout=2
            ).decode()
            wm_class = wm_class.lower()
            return any(cls in wm_class for cls in TERMINAL_WM_CLASSES)
        except Exception:
            return False

    def inject(self, text: str):
        if not text:
            logger.warning("inject: text is empty, skipping")
            return

        text = text.replace('\r\n', '\n').replace('\r', '')
        logger.info(f"inject: text={repr(text[:80])}, xclip={self.has_xclip}, xdotool={self.has_xdotool}")

        try:
            if self.has_xclip and self.has_xdotool:
                old_clipboard = self._get_clipboard()
                self._set_clipboard(text.encode('utf-8'))
                time.sleep(0.05)

                is_term = self._is_terminal()
                if is_term:
                    paste_key = "ctrl+shift+v"
                else:
                    paste_key = "ctrl+v"

                logger.info(f"inject: pasting via {paste_key} (terminal={is_term})")
                subprocess.run(["xdotool", "key", paste_key], check=True, timeout=5)
                time.sleep(0.05)

                if is_term:
                    subprocess.run(["xdotool", "key", "Right"], check=True, timeout=2)

                if getattr(config, 'AUTO_ENTER', False):
                    logger.info("inject: pressing Return (AUTO_ENTER=True)")
                    subprocess.run(["xdotool", "key", "Return"], check=True, timeout=2)

                if old_clipboard:
                    self._set_clipboard(old_clipboard)
            else:
                logger.error("Немає xclip/xdotool! Неможливо інжектувати текст.")

        except Exception as e:
            logger.error(f"inject: error: {e}")

    def _has_command(self, cmd: str) -> bool:
        try:
            subprocess.run(["which", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except:
            return False
