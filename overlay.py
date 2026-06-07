import tkinter as tk
import logging
import queue
import math
import time

logger = logging.getLogger("VoxOverlay")

class TranscriptionOverlay:
    def __init__(self, audio_manager=None):
        self.audio_manager = audio_manager
        self.root = None
        self.canvas = None
        self.cmd_queue = queue.Queue()
        self.visible = False
        self.animation_enabled = False
        self.mode = "waveform"
        self.bar_items = []
        self.processing_items = []
        self.center_item = None
        self.bar_count = 23
        self.bar_width = 8
        self.bar_spacing = 6
        self.bar_min_height = 10
        self.bar_amplitude = 50
        self.processing_nodes = 16
        self.processing_radius = 30
        self.processing_spread = 24
        self.animation_speed = 4.0
        self.idle_level = 0.06
        self._init_window()

    def _init_window(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-alpha", 0.95)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#061426")

        width = self.bar_count * self.bar_width + (self.bar_count + 1) * self.bar_spacing
        height = 110
        x = (self.root.winfo_screenwidth() - width) // 2
        y = 24
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        self.canvas = tk.Canvas(self.root, width=width, height=height, bg="#061426", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        center_x = width // 2
        center_y = height // 2

        for index in range(self.bar_count):
            x0 = self.bar_spacing + index * (self.bar_width + self.bar_spacing) + self.bar_width // 2
            y0 = center_y - self.bar_min_height
            y1 = center_y + self.bar_min_height
            bar = self.canvas.create_line(
                x0, y0, x0, y1,
                fill="#ffffff",
                width=self.bar_width,
                capstyle="round",
                state="normal"
            )
            self.bar_items.append(bar)

        self.center_item = self.canvas.create_oval(
            center_x - 18, center_y - 18,
            center_x + 18, center_y + 18,
            outline="",
            fill="#8df2ff",
            state="hidden"
        )

        for index in range(self.processing_nodes):
            node = self.canvas.create_oval(
                center_x, center_y,
                center_x + 6, center_y + 6,
                fill="#ffffff",
                outline="",
                state="hidden"
            )
            self.processing_items.append(node)

        self.root.withdraw()

    def _update_waveform(self):
        height = int(self.root.winfo_height())
        center = height // 2
        t = time.time() * self.animation_speed
        level = self.idle_level
        if self.audio_manager:
            level = max(self.idle_level, self.audio_manager.get_last_level())

        for index, item in enumerate(self.bar_items):
            phase = t + index * 0.38
            value = (math.sin(phase) + 1) / 2
            bar_height = self.bar_min_height + value * self.bar_amplitude * level
            y0 = center - bar_height
            y1 = center + bar_height
            x = self.bar_spacing + index * (self.bar_width + self.bar_spacing) + self.bar_width // 2
            self.canvas.coords(item, x, y0, x, y1)
            brightness = int(180 + 75 * level)
            self.canvas.itemconfig(item, fill=f"#{brightness:02x}{brightness:02x}{brightness:02x}")

    def _update_processing(self):
        width = int(self.root.winfo_width())
        height = int(self.root.winfo_height())
        center_x = width // 2
        center_y = height // 2
        t = time.time() * (self.animation_speed * 0.6)
        level = self.idle_level
        if self.audio_manager:
            level = max(self.idle_level, self.audio_manager.get_last_level())

        glow = 18 + 8 * math.sin(t * 1.1)
        self.canvas.coords(
            self.center_item,
            center_x - glow, center_y - glow,
            center_x + glow, center_y + glow
        )
        self.canvas.itemconfig(self.center_item, fill=f"#{int(140 + level * 90):02x}{int(220 - level * 40):02x}{255:02x}")

        for index, item in enumerate(self.processing_items):
            angle = 2 * math.pi * index / len(self.processing_items)
            radius = self.processing_radius + math.sin(t + index * 0.6) * self.processing_spread * level
            x = center_x + math.cos(angle) * radius
            y = center_y + math.sin(angle) * radius
            self.canvas.coords(item, x - 4, y - 4, x + 4, y + 4)
            alpha = 0.45 + 0.55 * level * (0.5 + 0.5 * math.sin(t + index))
            color_value = int(220 + 15 * math.sin(t + index * 1.3))
            self.canvas.itemconfig(item, fill=f"#{color_value:02x}{255:02x}{255:02x}")

    def show_waveform(self):
        self.cmd_queue.put(("show_waveform", None))

    def show_processing(self):
        self.cmd_queue.put(("show_processing", None))

    def hide(self):
        self.cmd_queue.put(("hide", None))

    def update_text(self, text):
        # No live text updates for the pulsing AI overlay.
        pass

    def run_step(self):
        if not self.root:
            return
        try:
            while not self.cmd_queue.empty():
                cmd, _ = self.cmd_queue.get_nowait()
                if cmd == "show_waveform":
                    self.mode = "waveform"
                    self.visible = True
                    self.animation_enabled = True
                    self.root.deiconify()
                    for item in self.bar_items:
                        self.canvas.itemconfig(item, state="normal")
                    self.canvas.itemconfig(self.center_item, state="hidden")
                    for item in self.processing_items:
                        self.canvas.itemconfig(item, state="hidden")
                elif cmd == "show_processing":
                    self.mode = "processing"
                    self.visible = True
                    self.animation_enabled = True
                    self.root.deiconify()
                    for item in self.bar_items:
                        self.canvas.itemconfig(item, state="hidden")
                    self.canvas.itemconfig(self.center_item, state="normal")
                    for item in self.processing_items:
                        self.canvas.itemconfig(item, state="normal")
                elif cmd == "hide":
                    self.visible = False
                    self.animation_enabled = False
                    self.root.withdraw()

            if self.visible:
                if self.mode == "waveform":
                    self._update_waveform()
                else:
                    self._update_processing()
            self.root.update()
        except Exception as e:
            logger.error(f"Overlay error: {e}")

    def destroy(self):
        if self.root:
            try:
                self.root.destroy()
            except RuntimeError as e:
                logger.error(f"Overlay destroy error: {e}")
            finally:
                self.root = None
