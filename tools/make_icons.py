"""Draw the app icons (original artwork: an upward 'path' with a goal dot).

Run once if you want to change colors:  python tools/make_icons.py
Output goes to static/icons/. Needs Pillow (requirements-dev.txt).
"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "static" / "icons"
TOP, BOTTOM = (99, 102, 241), (67, 56, 202)  # indigo gradient
SS = 4  # draw 4x larger, then shrink for smooth edges


def gradient(size):
    img = Image.new("RGB", (size, size))
    px = img.load()
    for y in range(size):
        t = y / (size - 1)
        row = tuple(round(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3))
        for x in range(size):
            px[x, y] = row
    return img


def artwork(size, scale=1.0):
    """White rising path ending in a dot, centered inside `scale` of the canvas."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pad = size * (1 - scale) / 2
    s = size * scale

    def p(x, y):
        return (pad + x * s, pad + y * s)

    pts = [p(0.22, 0.74), p(0.40, 0.56), p(0.54, 0.64), p(0.76, 0.30)]
    width = round(s * 0.085)
    d.line(pts, fill=(255, 255, 255, 255), width=width, joint="curve")
    for x, y in (pts[0], pts[-1]):
        r = width / 2
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 255))
    cx, cy = p(0.76, 0.30)
    r = s * 0.095
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 214, 102, 255))
    return layer


def make(size, rounded, art_scale, name):
    big = size * SS
    base = gradient(big).convert("RGBA")
    base.alpha_composite(artwork(big, art_scale))
    if rounded:
        mask = Image.new("L", (big, big), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, big - 1, big - 1), radius=round(big * 0.22), fill=255)
        base.putalpha(mask)
    base = base.resize((size, size), Image.LANCZOS)
    base.save(OUT / name, optimize=True)
    print("wrote", name)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    make(192, True, 0.9, "icon-192.png")
    make(512, True, 0.9, "icon-512.png")
    make(512, False, 0.62, "icon-maskable-512.png")  # full bleed; art stays inside the safe zone
    make(180, False, 0.8, "apple-touch-icon.png")  # iOS rounds the corners itself
