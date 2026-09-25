"""
MOCK pipeline, ported from the React UI (web/src/services: random.ts, heatmap.ts, sampleLeaves.ts, analysis.ts).
Nothing here runs a model: it returns preset results, a fake Grad-CAM heatmap and drawn sample leaves so the
interface can be designed. Replace build_mock_result() with the real VGG16/ResNet50 + Grad-CAM + LLM pipeline.
"""
import io
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .content import CLASS_INFO, CLASSES, MOCK_RESULTS, explain


# ---------------------------------------------------------------------------- random.ts
def seeded(seed: int):
    """Small seeded PRNG (mulberry32), same sequence as the React mock so the pictures match."""
    state = [seed & 0xFFFFFFFF]

    def imul(a, b):
        return (a * b) & 0xFFFFFFFF

    def rand():
        state[0] = (state[0] + 0x6D2B79F5) & 0xFFFFFFFF
        t = state[0]
        t = imul(t ^ (t >> 15), t | 1)
        t ^= (t + imul(t ^ (t >> 7), t | 61)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return rand


def hash_string(s: str) -> int:
    h = 2166136261
    for ch in s:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h


def _round(x: float) -> int:
    return int(math.floor(x + 0.5))   # JavaScript Math.round


def _jpeg(img: Image.Image, quality: int = 85) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=quality)
    return buf.getvalue()


# ---------------------------------------------------------------------------- heatmap.ts
def _jet(t: np.ndarray) -> np.ndarray:
    """Classic "jet" colormap, t in [0,1] -> RGB 0..255."""
    c = lambda x: np.clip(x, 0, 1)
    return np.stack([c(1.5 - np.abs(4 * t - 3)), c(1.5 - np.abs(4 * t - 2)), c(1.5 - np.abs(4 * t - 1))], -1) * 255


def mock_heatmap(width: int, height: int, seed: int, blobs: int = 4) -> bytes:
    """MOCK Grad-CAM heatmap from random blobs (same look as a tf-keras-vis overlay). Does NOT analyze the image."""
    rand = seeded(seed)
    gw = 28
    gh = max(8, _round(gw * height / width))
    centers = []
    for _ in range(blobs):
        x = 0.2 + rand() * 0.6
        y = 0.2 + rand() * 0.6
        r = 0.08 + rand() * 0.14
        w = 0.5 + rand() * 0.5
        centers.append((x, y, r, w))
    xs = np.arange(gw)[None, :] / gw
    ys = np.arange(gh)[:, None] / gh
    field = np.zeros((gh, gw))
    for cx, cy, r, w in centers:
        dx = xs - cx
        dy = (ys - cy) * (gh / gw)
        field += w * np.exp(-(dx * dx + dy * dy) / (2 * r * r))
    small = Image.fromarray(_jet(field / (field.max() or 1)).astype(np.uint8), "RGB")
    scale = min(1, 720 / max(width, height))
    out = small.resize((max(1, _round(width * scale)), max(1, _round(height * scale))), Image.BICUBIC)
    return _jpeg(out, 85)


# ---------------------------------------------------------------------------- sampleLeaves.ts
def slug(disease: str) -> str:
    return disease.lower().replace(" ", "-")


def sample_file_name(disease: str) -> str:
    return f"sample-leaf_{slug(disease)}.jpg"


def class_from_sample_name(name: str):
    """The class a sample photo was drawn for (lets the mock return a matching result)."""
    return next((c for c in CLASSES if name == sample_file_name(c)), None)


def _hex(c: str, a: float = 1.0):
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), int(round(a * 255)))


def _cubic(p0, p1, p2, p3, n=64):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = map(np.array, (p0, p1, p2, p3))
    return ((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3).tolist()


def _quad(p0, p1, p2, n=48):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2 = map(np.array, (p0, p1, p2))
    return ((1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2).tolist()


def _gradient_rows(h: int, y0: float, y1: float, stops) -> np.ndarray:
    """Vertical linear gradient (canvas createLinearGradient(0,y0,0,y1)) as an (h, 4) RGBA array, rows in px."""
    ys = np.arange(h) + 0.5
    t = np.clip((ys - y0) / (y1 - y0), 0, 1)
    offs = np.array([s[0] for s in stops])
    cols = np.array([s[1] for s in stops], float)
    return np.stack([np.interp(t, offs, cols[:, k]) for k in range(4)], -1)


def draw_sample_leaf(disease: str, seed: int, w: int = 640, h: int = 480) -> bytes:
    """Simple illustrated rice leaf for mock history thumbnails and "Use sample photo" (demo only)."""
    S = 2                                        # supersampling for smooth edges
    W_, H_ = w * S, h * S
    rand = seeded(seed)

    # Soft field background: diagonal gradient + faint grass strokes
    yy, xx = np.mgrid[0:H_, 0:W_]
    t = np.clip((xx * W_ + yy * H_) / float(W_ * W_ + H_ * H_), 0, 1)[..., None]
    c0, c1 = np.array(_hex("#6f7d4f")[:3], float), np.array(_hex("#44502f")[:3], float)
    bg = Image.fromarray(((1 - t) * c0 + t * c1).astype(np.uint8), "RGB").convert("RGBA")
    for i in range(18):
        colour = "#9fae6c" if i % 2 else "#2f3a22"
        lw = 6 + rand() * 10
        x = rand() * w
        cx = x + (rand() - 0.5) * 120
        ex = x + (rand() - 0.5) * 220
        pts = [(px * S, py * S) for px, py in _quad((x, h + 20), (cx, h / 2), (ex, -20))]
        layer = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
        ImageDraw.Draw(layer).line(pts, fill=_hex(colour, 0.18), width=max(1, _round(lw * S)), joint="curve")
        bg = Image.alpha_composite(bg, layer)

    # Leaf blade in its own (unrotated) frame, centred; rotated into place afterwards
    angle = -0.42 + (rand() - 0.5) * 0.2
    L, W = w * 0.62, h * 0.13
    pad = 60
    LW, LH = int((2 * L + 2 * pad) * S), int((2.6 * W + 2 * pad) * S)
    ox, oy = LW / 2, LH / 2
    P = lambda x, y: (ox + x * S, oy + y * S)    # local -> layer pixels

    outline = _cubic((-L, 6), (-L * 0.4, -W * 1.1), (L * 0.5, -W * 0.9), (L, -4)) + \
        _cubic((L, -4), (L * 0.5, W * 0.7), (-L * 0.4, W * 1.2), (-L, 6))
    blade = Image.new("L", (LW, LH), 0)
    ImageDraw.Draw(blade).polygon([P(x, y) for x, y in outline], fill=255)

    grad = _gradient_rows(LH, oy - W * S, oy + W * S,
                          [(0, _hex("#8fbf4a")), (0.5, _hex("#6ea235")), (1, _hex("#557f27"))])
    fill = Image.fromarray(np.repeat(grad[:, None, :], LW, 1).astype(np.uint8), "RGBA")

    leaf = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    shadow_a = np.asarray(blade.filter(ImageFilter.GaussianBlur(9 * S)), float) * 0.35
    shadow = np.zeros((LH, LW, 4), np.uint8)
    shadow[..., 3] = shadow_a.astype(np.uint8)
    leaf = Image.alpha_composite(leaf, Image.fromarray(shadow, "RGBA"))
    leaf.paste(fill, (0, 0), blade)

    # Veins and disease marks, clipped to the blade
    detail = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))

    def over(draw_fn):
        nonlocal detail
        lay = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
        draw_fn(ImageDraw.Draw(lay))
        detail = Image.alpha_composite(detail, lay)

    for k in range(-3, 4):
        pts = [P(x, y) for x, y in _cubic((-L, k * 5), (-L * 0.4, k * 10 - 4), (L * 0.5, k * 8 - 2), (L, 0))]
        over(lambda d, pts=pts: d.line(pts, fill=(220, 240, 180, 89), width=2 * S, joint="curve"))

    def ellipse(d, x, y, rx, ry, colour):
        d.ellipse([P(x - rx, y - ry), P(x + rx, y + ry)], fill=colour)

    if disease == "Brown Spot":
        for _ in range(22):
            x = -L * 0.8 + rand() * L * 1.6
            y = (rand() - 0.5) * W * 1.1
            r = 5 + rand() * 7
            over(lambda d, x=x, y=y, r=r: ellipse(d, x, y, r * 1.6, r, (230, 200, 90, 140)))
            over(lambda d, x=x, y=y, r=r: (ellipse(d, x, y, r * 1.1 + 1.5, r * 0.7 + 1.5, _hex("#5a3312")),
                                           ellipse(d, x, y, r * 1.1, r * 0.7, _hex("#7a4a1e"))))
    elif disease == "Leaf Blast":
        for _ in range(9):
            x = -L * 0.7 + rand() * L * 1.4
            y = (rand() - 0.5) * W * 0.9
            ln = 22 + rand() * 20
            shape = _quad((x - ln, y), (x, y - 11), (x + ln, y)) + _quad((x + ln, y), (x, y + 11), (x - ln, y))
            pts = [P(px, py) for px, py in shape]
            over(lambda d, pts=pts: (d.polygon(pts, fill=_hex("#b9b6a6")),
                                     d.line(pts + [pts[0]], fill=_hex("#6b4a2a"), width=3 * S, joint="curve")))
    elif disease == "Bacterial Blight":
        band = _gradient_rows(LH, oy - W * S, oy + W * S,
                              [(0, (232, 214, 120, 242)), (0.35, (214, 196, 110, 153)), (0.55, (0, 0, 0, 0)),
                               (1, (0, 0, 0, 0))])
        band_img = np.zeros((LH, LW, 4), np.uint8)
        x0, x1 = int(P(-L * 0.1, 0)[0]), int(P(L * 1.1, 0)[0])
        band_img[:, x0:x1] = np.repeat(band[:, None, :], x1 - x0, 1).astype(np.uint8)
        detail = Image.alpha_composite(detail, Image.fromarray(band_img, "RGBA"))
        over(lambda d: d.rectangle([P(L * 0.55, -W * 1.2), P(L * 1.15, W * 1.2)], fill=(210, 190, 120, 230)))

    clipped = np.asarray(detail).copy()
    clipped[..., 3] = (clipped[..., 3].astype(float) * np.asarray(blade, float) / 255).astype(np.uint8)
    leaf = Image.alpha_composite(leaf, Image.fromarray(clipped, "RGBA"))

    # Midrib (not clipped)
    mid = [P(x, y) for x, y in _cubic((-L, 4), (-L * 0.4, -6), (L * 0.5, -4), (L, -3))]
    lay = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    ImageDraw.Draw(lay).line(mid, fill=(235, 245, 200, 140), width=3 * S, joint="curve")
    leaf = Image.alpha_composite(leaf, lay)

    # Rotate like ctx.rotate(angle) (canvas y points down, so a negative angle turns counter-clockwise)
    leaf = leaf.rotate(-math.degrees(angle), resample=Image.BICUBIC, expand=True)
    bg.alpha_composite(leaf, (int(W_ / 2 - leaf.width / 2), int(H_ / 2 - leaf.height / 2)))
    return _jpeg(bg.resize((w, h), Image.LANCZOS), 85)


def sample_leaf_file():
    """A sample leaf photo, so the upload flow can be tested without a real photo: (name, bytes)."""
    disease = random.choice(CLASSES)
    return sample_file_name(disease), draw_sample_leaf(disease, random.randrange(1_000_000))


# ---------------------------------------------------------------------------- analysis.ts (mock part)
def build_mock_result(preset: dict, seed: int, size, lang: str = "English") -> dict:
    """Build a full mock result from a preset. Same keys the real pipeline will return."""
    disease, confidence = preset["disease"], preset["confidence"]
    severity, affected = preset["severity"], preset["affected_pct"]
    shares = [0.6, 0.28, 0.12]
    others = [c for c in CLASSES if c != disease]
    probabilities = {disease: confidence, **{c: (1 - confidence) * shares[i] for i, c in enumerate(others)}}
    blobs = 5 if severity == "Severe" else 3 if severity == "Moderate" else 2
    return {
        "disease": disease,
        "confidence": confidence,
        "severity": severity,
        "affected_pct": affected,
        "heatmap": mock_heatmap(size[0], size[1], seed, blobs),
        "treatment": CLASS_INFO[disease]["treatment"],
        "explanation": explain(disease, severity, affected, lang),
        "probabilities": probabilities,
        "model": "Model pending",
        "is_mock": True,
    }


def pick_mock(image_name: str, choice: str, last):
    """Which preset to return: the Settings choice, the class a sample photo was drawn for, or a random class
    (never the same one twice in a row). Returns (preset, new_last)."""
    if choice != "Random":
        return MOCK_RESULTS[choice], last
    from_sample = class_from_sample_name(image_name)
    if from_sample:
        return MOCK_RESULTS[from_sample], last
    pick = random.choice([c for c in CLASSES if c != last])
    return MOCK_RESULTS[pick], pick
