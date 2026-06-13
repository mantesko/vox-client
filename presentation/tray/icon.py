from PIL import Image, ImageDraw


class TrayIconGenerator:
    COLORS = {
        "recording": ((255, 59, 48, 255), (255, 59, 48, 80)),
        "listening": ((52, 199, 89, 255), (52, 199, 89, 80)),
        "paused":    ((142, 142, 147, 255), (142, 142, 147, 80)),
        "idle":      ((142, 142, 147, 255), (142, 142, 147, 80)),
    }

    def generate(self, state: str, paused: bool) -> Image.Image:
        width, height = 64, 64
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        dc = ImageDraw.Draw(image)

        if paused:
            color, glow = self.COLORS["paused"]
        else:
            color, glow = self.COLORS.get(state, self.COLORS["idle"])

        dc.ellipse((2, 2, width - 2, height - 2), fill=glow)
        dc.ellipse((12, 12, width - 12, height - 12), fill=color, outline=(255, 255, 255, 255), width=2)

        return image
