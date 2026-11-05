"""
The real RiceGuard pipeline:
photo -> leaf segmenter (U-Net, MobileNetV2 encoder) finds the outlined leaf -> leaf cut-out made like the training
images (tools/build_final_dataset.py: box around the leaf + 5%, grey outside the leaf, long side <= 512) -> padded to
320 x 320 -> the final VGG16 / ResNet50 model (tools/make_final_notebook.py, seed 1) -> Grad-CAM (tf-keras-vis, as
named in the thesis) -> severity from the share of the leaf the heatmap covers.

Model files: models/<folder>/model.keras (+ preprocessing.json / segmenter.json) next to app.py. They are only in the
deploy repo (RiceGuard-Deploy); the main repo ignores *.keras. TensorFlow is imported only when a model is used, so
the app still runs with the mock results (riceguard_ui/mock.py) wherever TensorFlow or the model files are missing.
"""
import importlib.util
import io
import json
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from .content import CLASS_INFO, explain
from .mock import _jet, _jpeg

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODELS = {                                   # name shown in the app: (folder in models/, Grad-CAM layer)
    "ResNet50": ("resnet50", "conv5_block3_out"),
    "VGG16": ("vgg16", "block5_conv3"),
}
# Seed-1 models had the better macro F1 with VGG16, both on the true cut-outs of the test set (0.863 vs 0.855) and
# through this app pipeline (0.870 vs 0.836, riceguard results/app_check/segmenter/segmenter_check.json).
DEFAULT_MODEL = "VGG16"
STAGE_LABEL = "Final"                        # shown next to the model name: the training run the files in models/ come from
# The notebook's CLASS_NAMES order (the model's output index). The notebooks and dataset call class 0 "Bacterial
# Blight"; the app shows "Bacterial Leaf Blight", the name the validating plant pathologist asked for.
MODEL_CLASSES = ["Bacterial Leaf Blight", "Leaf Blast", "Brown Spot", "Healthy"]
SEGMENTER = "segmenter"                      # folder in models/
STORED_LONG_SIDE = 1024                      # uploads are kept at most this size (the app pipeline check used 1024)

# Classifier input (models/<folder>/preprocessing.json) and leaf cut-out (models/segmenter/segmenter.json); these
# defaults are the values the final models were trained with.
CLS_SIZE, GREY = 320, (124, 116, 104)
SEG_SIZE, SEG_THRESHOLD, MIN_PART, CUT_MARGIN, CUT_LONG = 320, 0.5, 0.05, 0.05, 512

# Severity = share of the LEAF (the segmenter's outline) where the Grad-CAM heat is at least HEAT_THRESHOLD.
HEAT_THRESHOLD = 0.5
# Per-disease cut-offs (thesis Chapter III, Table 4). The manuals use whole percents, so severity_of() rounds first.
#   Bacterial Leaf Blight: Mild <= 24%, Moderate 25-50%, Severe > 50%  (PhilRice Rice Breeding Operations Manual, p. 79)
#   Leaf Blast:            Mild < 4%,   Moderate 4-25%,  Severe > 25%  (PhilRice manual, p. 77; IRRI SES, p. 15)
#   Brown Spot:            Mild <= 5%,  Moderate 6-25%,  Severe > 25%  (IRRI Standard Evaluation System, p. 13)
SEVERITY_CUTOFFS = {            # (highest whole % still Mild, highest whole % still Moderate); above -> Severe
    "Bacterial Leaf Blight": (24, 50),
    "Leaf Blast": (3, 25),
    "Brown Spot": (5, 25),
}


def _files() -> list:
    """Classifiers whose file is present. They are only usable together with the leaf segmenter."""
    if not (MODELS_DIR / SEGMENTER / "model.keras").is_file():
        return []
    return [n for n, (folder, _) in MODELS.items() if (MODELS_DIR / folder / "model.keras").is_file()]


def _tensorflow() -> bool:
    return all(importlib.util.find_spec(m) for m in ("tensorflow", "tf_keras_vis"))


def available() -> list:
    """Models whose file is present and TensorFlow is installed, default first. Empty -> the app uses mock results."""
    return sorted(_files(), key=lambda n: n != DEFAULT_MODEL) if _tensorflow() else []


def unavailable_reason() -> str:
    """Why the app is using mock results (shown next to the version, so a deployment problem is visible)."""
    if not _files():
        return "no model files"
    if not _tensorflow():
        return f"TensorFlow not installed (Python {sys.version_info.major}.{sys.version_info.minor})"
    return ""


@lru_cache(maxsize=None)
def _preprocess_layer():
    """The notebook's BackbonePreprocess layer. The saved models contain it, so it must exist before loading."""
    import keras

    @keras.saving.register_keras_serializable(package="riceguard")
    class BackbonePreprocess(keras.layers.Layer):
        """The backbone's own preprocess_input, run INSIDE the model. Input: raw RGB 0-255."""
        def __init__(self, backbone="vgg16", **kwargs):
            super().__init__(**kwargs)
            self.backbone = backbone

        def call(self, x):
            if self.backbone == "vgg16":
                return keras.applications.vgg16.preprocess_input(x)
            return keras.applications.resnet50.preprocess_input(x)

        def get_config(self):
            return {**super().get_config(), "backbone": self.backbone}

    return BackbonePreprocess


def _settings(folder: str, name: str) -> dict:
    path = MODELS_DIR / folder / name
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def load(name: str):
    """(model, Grad-CAM, layer, input settings) for one classifier. Slow (seconds); app.py caches it with
    st.cache_resource."""
    import keras
    from tf_keras_vis.gradcam import Gradcam

    _preprocess_layer()
    folder, layer = MODELS[name]
    model = keras.models.load_model(MODELS_DIR / folder / "model.keras", compile=False)
    # Grad-CAM on the score before softmax (the notebook's ReplaceToLinear), via the logits layer. This shares the
    # weights instead of cloning the whole model, which keeps memory low on Streamlit Cloud.
    scores = keras.Model(model.inputs, model.get_layer("logits").output)
    pre = _settings(folder, "preprocessing.json")
    return model, Gradcam(scores, clone=False), layer, (pre.get("size", CLS_SIZE), tuple(pre.get("grey", GREY)))


@lru_cache(maxsize=1)
def _segmenter():
    """The leaf segmenter (one per server, shared by both classifiers) and its settings."""
    import keras

    return (keras.models.load_model(MODELS_DIR / SEGMENTER / "model.keras", compile=False),
            _settings(SEGMENTER, "segmenter.json"))


def stored_photo(data: bytes) -> bytes:
    """An upload ready for the pipeline: upright, at most 1024 px, JPEG. Needs only Pillow (runs on upload).
    A JPEG that is already like that is kept byte for byte."""
    img = Image.open(io.BytesIO(data))
    if img.format == "JPEG" and img.getexif().get(0x0112, 1) == 1 and max(img.size) <= STORED_LONG_SIDE:
        return data
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((STORED_LONG_SIDE, STORED_LONG_SIDE), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92)
    return buf.getvalue()


def _fit(w: int, h: int, size: int):
    """Size and offset that put a w x h picture in the middle of a size x size square (the notebooks' "pad")."""
    s = size / max(w, h)
    nw, nh = max(1, round(w * s)), max(1, round(h * s))
    return nw, nh, (size - nw) // 2, (size - nh) // 2


def _pad(img: Image.Image, size: int, grey) -> np.ndarray:
    nw, nh, ox, oy = _fit(*img.size, size)
    canvas = Image.new("RGB", (size, size), grey)
    canvas.paste(img.resize((nw, nh), Image.BILINEAR), (ox, oy))
    return np.asarray(canvas, np.float32)


def leaf_mask(img: Image.Image) -> np.ndarray | None:
    """The outlined leaf (or leaves) at the photo's own size, as found by the segmenter; specks are dropped.
    None when no leaf is found."""
    from scipy import ndimage

    seg, cfg = _segmenter()
    size, grey = cfg.get("input_size", SEG_SIZE), tuple(cfg.get("grey", GREY))
    w, h = img.size
    nw, nh, ox, oy = _fit(w, h, size)
    p = seg(_pad(img, size, grey)[None], training=False).numpy()[0, ..., 0]
    p = np.asarray(Image.fromarray(p[oy:oy + nh, ox:ox + nw]).resize((w, h), Image.BILINEAR))
    mask = p > cfg.get("threshold", SEG_THRESHOLD)
    parts, n = ndimage.label(mask)
    if n == 0:
        return None
    sizes = ndimage.sum(mask, parts, range(1, n + 1))
    return np.isin(parts, 1 + np.where(sizes >= cfg.get("min_part", MIN_PART) * sizes.sum())[0])


def cut_out(img: Image.Image, mask: np.ndarray, grey):
    """The leaf cut-out the classifiers were trained on (tools/build_final_dataset.py): box around the leaf + 5%,
    grey outside the leaf, long side at most 512. Also returns the box, to put the heatmap back on the photo."""
    w, h = img.size
    ys, xs = np.where(mask)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    mx, my = (x1 - x0) * CUT_MARGIN, (y1 - y0) * CUT_MARGIN
    box = (max(0, int(x0 - mx)), max(0, int(y0 - my)), min(w, int(np.ceil(x1 + mx))), min(h, int(np.ceil(y1 + my))))
    cut = Image.composite(img, Image.new("RGB", (w, h), grey), Image.fromarray(mask.astype(np.uint8) * 255)).crop(box)
    s = min(1.0, CUT_LONG / max(cut.size))
    if s < 1:
        cut = cut.resize((round(cut.size[0] * s), round(cut.size[1] * s)), Image.LANCZOS)
    return cut, box


def predict(loaded, stored: bytes) -> dict:
    """Class probabilities, plus the Grad-CAM heatmap (0-1) and the leaf mask, both at the photo's size.
    The heatmap is computed on the leaf cut-out and put back where the leaf is; outside the leaf it is 0.
    When the segmenter finds no leaf, only {"leaf_found": False} is returned: the photo is not classified."""
    from tf_keras_vis.utils.scores import CategoricalScore

    model, gradcam, layer, (size, grey) = loaded
    img = Image.open(io.BytesIO(stored)).convert("RGB")
    w, h = img.size
    mask = leaf_mask(img)
    if mask is None:
        return {"leaf_found": False}
    cut, box = cut_out(img, mask, grey)
    x = _pad(cut, size, grey)
    probs = model(x[None], training=False).numpy()[0]
    top = int(probs.argmax())
    cam = np.asarray(gradcam(CategoricalScore([top]), x[None], penultimate_layer=layer)).reshape(size, size)
    nw, nh, ox, oy = _fit(*cut.size, size)
    heat = np.zeros((h, w), np.float32)
    heat[box[1]:box[3], box[0]:box[2]] = np.asarray(
        Image.fromarray(cam[oy:oy + nh, ox:ox + nw].astype(np.float32)).resize((box[2] - box[0], box[3] - box[1]),
                                                                              Image.BILINEAR))
    return {"probs": probs, "top": top, "cam": np.clip(heat, 0, 1) * mask, "mask": mask, "leaf_found": True}


def severity_of(disease: str, affected_pct: float) -> str:
    # Round half up (round() is banker's rounding: 24.5 -> 24 but 25.5 -> 26).
    pct = math.floor(affected_pct + 0.5)
    mild, moderate = SEVERITY_CUTOFFS[disease]
    if pct <= mild:
        return "Mild"
    if pct <= moderate:
        return "Moderate"
    return "Severe"


def heatmap_jpeg(cam: np.ndarray, size) -> bytes:
    """The heatmap as a jet-coloured picture at the photo's shape (the result viewer lays it over the photo)."""
    heat = Image.fromarray(_jet(cam).astype(np.uint8), "RGB")
    w, h = size
    scale = min(1, 720 / max(w, h))
    return _jpeg(heat.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.BICUBIC), 85)


def result(name: str, out: dict, size, lang: str = "English") -> dict:
    """A result with the same keys as mock.build_mock_result(), so the interface doesn't change."""
    disease = MODEL_CLASSES[out["top"]]
    if disease == "Healthy":
        severity, affected = None, 0.0
    else:
        leaf = out["mask"]
        hot = out["cam"] >= HEAT_THRESHOLD
        affected = round(100.0 * (hot & leaf).sum() / max(1, leaf.sum()), 1)
        severity = severity_of(disease, affected)
    return {
        "disease": disease,
        "confidence": float(out["probs"][out["top"]]),
        "severity": severity,
        "affected_pct": affected,
        "heatmap": heatmap_jpeg(out["cam"], size),
        "treatment": CLASS_INFO[disease]["treatment"],
        "explanation": explain(disease, severity, affected, lang),
        "probabilities": {c: float(p) for c, p in zip(MODEL_CLASSES, out["probs"])},
        "model": f"{name} · {STAGE_LABEL}",
        "is_mock": False,
    }
