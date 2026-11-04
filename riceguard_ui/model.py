"""
The real RiceGuard pipeline: the VGG16 / ResNet50 models trained by the notebooks (tools/make_notebook.py)
-> Grad-CAM (tf-keras-vis, as named in the thesis) -> severity from the share of the leaf the heatmap covers.

Model files: models/<folder>/model.keras next to app.py. They are only in the deploy repo (RiceGuard-Deploy);
the main repo ignores *.keras. TensorFlow is imported only when a model is used, so the app still runs with the
mock results (riceguard_ui/mock.py) wherever TensorFlow or the model files are missing.
"""
import importlib.util
import io
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
DEFAULT_MODEL = "ResNet50"                   # better test-set macro F1 (0.68 vs 0.67, dataset v5); the thesis uses the better one
STAGE_LABEL = "Stage 2"                      # shown next to the model name: the training run the files in models/ come from
MODEL_CLASSES = ["Bacterial Blight", "Leaf Blast", "Brown Spot", "Healthy"]   # the notebook's CLASS_NAMES order
IMG_SIZE = (224, 224)
STORED_LONG_SIDE = 384                       # training photos were stored at most this size (build_photo_split.py)

# Severity = share of the LEAF (plain paper/mat background left out, same rule as the notebook's shortcut checks)
# where the Grad-CAM heat is at least HEAT_THRESHOLD.
HEAT_THRESHOLD = 0.5
# Per-disease cut-offs (thesis Chapter III, Table 4). The manuals use whole percents, so severity_of() rounds first.
#   Bacterial Blight: Mild <= 24%, Moderate 25-50%, Severe > 50%  (PhilRice Rice Breeding Operations Manual, p. 79)
#   Leaf Blast:       Mild < 4%,   Moderate 4-25%,  Severe > 25%  (PhilRice manual, p. 77; IRRI SES, p. 15)
#   Brown Spot:       Mild <= 5%,  Moderate 6-25%,  Severe > 25%  (IRRI Standard Evaluation System, p. 13)
SEVERITY_CUTOFFS = {            # (highest whole % still Mild, highest whole % still Moderate); above -> Severe
    "Bacterial Blight": (24, 50),
    "Leaf Blast": (3, 25),
    "Brown Spot": (5, 25),
}


def _files() -> list:
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


def load(name: str):
    """(model, Grad-CAM) for one model. Slow (seconds); app.py caches it with st.cache_resource."""
    import keras
    from tf_keras_vis.gradcam import Gradcam

    _preprocess_layer()
    folder, layer = MODELS[name]
    model = keras.models.load_model(MODELS_DIR / folder / "model.keras", compile=False)
    # Grad-CAM on the score before softmax (the notebook's ReplaceToLinear), via the logits layer. This shares the
    # weights instead of cloning the whole model, which keeps memory low on Streamlit Cloud.
    scores = keras.Model(model.inputs, model.get_layer("logits").output)
    return model, Gradcam(scores, clone=False), layer


def stored_photo(data: bytes) -> bytes:
    """An upload as a training photo was stored: upright, at most 384 px, JPEG. Needs only Pillow (runs on upload).
    A JPEG that is already like that is kept byte for byte."""
    img = Image.open(io.BytesIO(data))
    if img.format == "JPEG" and img.getexif().get(0x0112, 1) == 1 and max(img.size) <= STORED_LONG_SIDE:
        return data
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((STORED_LONG_SIDE, STORED_LONG_SIDE), Image.LANCZOS)   # as tools/build_photo_split.py did
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92)
    return buf.getvalue()


def predict(loaded, stored: bytes) -> dict:
    """Class probabilities and the Grad-CAM heatmap (224x224, 0-1) for the predicted class.
    The photo is read exactly like image_dataset_from_directory read training photos: TensorFlow's JPEG decoder,
    then a bilinear resize to 224x224 (Pillow decodes JPEGs slightly differently, enough to flip close calls)."""
    import tensorflow as tf
    from tf_keras_vis.utils.scores import CategoricalScore

    model, gradcam, layer = loaded
    x = tf.image.resize(tf.io.decode_jpeg(stored, channels=3), IMG_SIZE, method="bilinear").numpy()
    probs = model(x[None], training=False).numpy()[0]
    top = int(probs.argmax())
    cam = np.asarray(gradcam(CategoricalScore([top]), x[None], penultimate_layer=layer)).reshape(IMG_SIZE)
    return {"probs": probs, "top": top, "cam": cam, "x": x}


def leaf_mask(x: np.ndarray) -> np.ndarray:
    """True where the pixel is NOT plain background (light, low-saturation paper or mat), as in the notebook."""
    rgb = x / 255.0
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-8), 0)
    return ~((sat < 0.18) & (mx > 0.55))


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
        leaf = leaf_mask(out["x"])
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
