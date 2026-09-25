"""The RiceGuard mark as a PNG (browser-tab icon), drawn like the SVG favicon in web/index.html."""
from PIL import Image, ImageDraw

from .mock import _cubic


def favicon(size: int = 128) -> Image.Image:
    s = size / 32
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=8 * s, fill=(45, 106, 71, 255))
    strokes = [
        _cubic((16, 26.5), (16, 19), (17.2, 13.9), (23, 9)) + _cubic((23, 9), (22.2, 15.6), (20, 19.6), (16, 21.8)),
        _cubic((16, 26.5), (16, 20.7), (14.8, 16.9), (9.8, 13.1)) + _cubic((9.8, 13.1), (10.6, 18), (12.1, 21.1), (16, 23.1)),
    ]
    for pts in strokes:
        d.line([(x * s, y * s) for x, y in pts], fill="white", width=round(2.3 * s), joint="curve")
        for x, y in (pts[0], pts[-1]):
            r = 1.15 * s
            d.ellipse([x * s - r, y * s - r, x * s + r, y * s + r], fill="white")
    d.ellipse([(16 - 1.7) * s, (7.4 - 2.4) * s, (16 + 1.7) * s, (7.4 + 2.4) * s], fill="white")
    return img
