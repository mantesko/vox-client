import tkinter as tk
import logging
import queue
import math
import time

logger = logging.getLogger("VoxOverlay")

BG = "#0c1020"


def _hex(r, g, b):
    return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"


WAVE_COLORS = [
    (88, 130, 255),
    (180, 90, 255),
    (255, 80, 180),
]

DOT_COLOR = (120, 180, 255)


class TranscriptionOverlay:
    def __init__(self, audio_manager=None):
        self.audio_manager = audio_manager
        self.root = None
        self.canvas = None
        self.cmd_queue = queue.Queue()
        self.visible = False
        self.mode = "waveform"
        self.idle_level = 0.04

        self.size = 90
        self.cy = self.size // 2

        self.wave_lines = []
        self.wave_points = 40
        self.wave_w = int(self.size * 0.6)
        self.wave_start_x = (self.size - self.wave_w) // 2

        self.dot_count = 3
        self.dot_items = []
        self.dot_base_r = 5
        self.dot_spacing = 16

        self._init_window()

    def _init_window(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=BG)
        self.root.attributes("-alpha", 0.0)

        x = (self.root.winfo_screenwidth() - self.size) // 2
        y = 16
        self.root.geometry(f"{self.size}x{self.size}+{x}+{y}")

        self.canvas = tk.Canvas(
            self.root, width=self.size, height=self.size,
            bg=BG, highlightthickness=0,
        )
        self.canvas.pack()

        # ── Wave lines (recording) ─────────────────────
        for color in WAVE_COLORS:
            coords = []
            for i in range(self.wave_points + 1):
                px = self.wave_start_x + i * (self.wave_w / self.wave_points)
                coords.extend([px, self.cy])
            line = self.canvas.create_line(
                *coords,
                fill=_hex(*color), width=2,
                smooth=True, state="hidden",
            )
            self.wave_lines.append(line)

        # ── Dots (processing) ──────────────────────────
        total_dots_w = (self.dot_count - 1) * self.dot_spacing
        dot_start_x = (self.size - total_dots_w) // 2
        for i in range(self.dot_count):
            dx = dot_start_x + i * self.dot_spacing
            dot = self.canvas.create_oval(
                dx - self.dot_base_r, self.cy - self.dot_base_r,
                dx + self.dot_base_r, self.cy + self.dot_base_r,
                fill=_hex(*DOT_COLOR), outline="", state="hidden",
            )
            self.dot_items.append(dot)

        self.root.withdraw()

    # ── Public API ─────────────────────────────────────
    def show_waveform(self):
        self.cmd_queue.put(("show_waveform", None))

    def show_processing(self):
        self.cmd_queue.put(("show_processing", None))

    def hide(self):
        self.cmd_queue.put(("hide", None))

    def destroy(self):
        if self.root:
            try:
                self.root.destroy()
            except RuntimeError:
                pass
            finally:
                self.root = None

    # ── Main loop ──────────────────────────────────────
    def run_step(self):
        if not self.root:
            return
        try:
            self._process_commands()
            if self.visible:
                self._animate()
            self.root.update()
        except Exception as e:
            logger.error(f"Overlay error: {e}")

    def _process_commands(self):
        while not self.cmd_queue.empty():
            cmd, _ = self.cmd_queue.get_nowait()
            if cmd == "show_waveform":
                self._switch_mode("waveform")
            elif cmd == "show_processing":
                self._switch_mode("processing")
            elif cmd == "hide":
                self.visible = False
                self.animation_enabled = False
                self.root.attributes("-alpha", 0.0)
                self.root.withdraw()

    def _switch_mode(self, new_mode):
        self.mode = new_mode
        self.visible = True
        self.animation_enabled = True
        self.root.attributes("-alpha", 0.93)
        self.root.deiconify()

        is_wave = new_mode == "waveform"
        for line in self.wave_lines:
            self.canvas.itemconfig(line, state="normal" if is_wave else "hidden")
        for dot in self.dot_items:
            self.canvas.itemconfig(dot, state="normal" if not is_wave else "hidden")

    def _animate(self):
        t = time.time()
        level = self.idle_level
        if self.audio_manager:
            level = max(self.idle_level, self.audio_manager.get_last_level())

        if self.mode == "waveform":
            self._draw_wave(t, level)
        else:
            self._draw_dots(t, level)

    # ── Recording: Quantum Wave ────────────────────────
    def _draw_wave(self, t, level):
        max_amp = 18.0

        for wi, line in enumerate(self.wave_lines):
            color_r, color_g, color_b = WAVE_COLORS[wi]
            phase_offset = wi * 1.2
            freq = 2.5 + wi * 0.8
            amp = max_amp * (0.3 + 0.7 * level) * (1.0 - wi * 0.15)

            coords = []
            for i in range(self.wave_points + 1):
                px = self.wave_start_x + i * (self.wave_w / self.wave_points)
                nx = i / self.wave_points

                wave = math.sin(nx * freq * math.pi + t * 3.0 + phase_offset)
                wave2 = math.sin(nx * (freq * 0.6) * math.pi + t * 2.1 + phase_offset * 0.7)
                combined = wave * 0.65 + wave2 * 0.35

                py = self.cy + combined * amp
                coords.extend([px, py])

            self.canvas.coords(line, *coords)

            brightness = 0.5 + 0.5 * level
            r = int(color_r * brightness + 80 * (1 - brightness))
            g = int(color_g * brightness + 60 * (1 - brightness))
            b = int(color_b * brightness + 120 * (1 - brightness))
            self.canvas.itemconfig(line, fill=_hex(r, g, b))

    # ── Processing: Live Dots ──────────────────────────
    def _draw_dots(self, t, level):
        anim = t * 3.5

        for i, dot in enumerate(self.dot_items):
            dot_cx = self.canvas.coords(dot)
            dx = (dot_cx[0] + dot_cx[2]) / 2

            wave = math.sin(anim + i * 0.9)
            dy = self.cy + wave * 10 * (0.4 + 0.6 * level)

            pulse = 1.0 + 0.25 * math.sin(t * 2.5 + i * 0.7)
            r = self.dot_base_r * pulse

            self.canvas.coords(dot, dx - r, dy - r, dx + r, dy + r)

            a = 0.5 + 0.5 * (0.5 + 0.5 * math.sin(t * 1.8 + i * 1.1))
            cr = int(DOT_COLOR[0] * a + 60)
            cg = int(DOT_COLOR[1] * a + 60)
            cb = int(DOT_COLOR[2] * a + 40)
            self.canvas.itemconfig(dot, fill=_hex(cr, cg, cb))
