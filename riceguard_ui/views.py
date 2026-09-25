"""
HTML for the static parts of the RiceGuard UI, copied from the React components in web/src/components
and web/src/pages (same markup and class names, styled by the same app.css). Interactive parts
(buttons, uploads, switches, sliders, the question box) are Streamlit widgets placed around these.
"""
import re
from html import escape
from urllib.parse import quote

from . import fmt
from .content import APP, CLASS_INFO, CLASSES, LIMITS, SEVERITIES, SEVERITY_INFO, STEPS, UPLOAD
from .icons import svg

LOGO_PATH = ("M16 26.5c0-7.5 1.2-12.6 7-17.5-.8 6.6-3 10.6-7 12.8M16 26.5c0-5.8-1.2-9.6-6.2-13.4.8 4.9 2.3 8 "
             "6.2 10")
LOGO_STALK = "url('data:image/svg+xml;charset=utf-8," + quote(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><path d="{LOGO_PATH}" fill="none" stroke="black" '
    f'stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/>'
    f'<ellipse cx="16" cy="7.4" rx="1.55" ry="2.25" fill="black"/></svg>') + "')"


def logo_mark(size: int = 28) -> str:
    """RiceGuard mark: a rice stalk with a single grain inside a rounded square (placeholder mark).
    Streamlit strips <svg> from HTML, so the square is a span in var(--brand) and the stalk a white mask."""
    return (f'<span class="logo-mark rg-logo" aria-hidden="true" style="width:{size}px;height:{size}px;'
            f'border-radius:{size / 4:g}px"><span class="rg-logo-stalk" style="--rg-icon:{LOGO_STALK}"></span></span>')


def logo() -> str:
    return f'<div class="logo">{logo_mark()}<span class="logo-word">RiceGuard</span></div>'


def marker(tone: str, size: str = "") -> str:
    cls = f"marker marker-{size}" if size else "marker"
    return f'<span class="{cls}" style="--tone: {tone}" aria-hidden="true"></span>'


# ---------------------------------------------------------------------------- shell
def topbar_left(title) -> str:
    t = f'<span class="topbar-title only-desktop">{escape(title)}</span>' if title else ""
    return f'<div class="topbar-left"><span class="only-mobile">{logo()}</span>{t}</div>'


def version_line() -> str:
    return f'<div class="version">{APP["name"]} v{APP["version"]} · {APP["stage"]}</div>'


# ---------------------------------------------------------------------------- welcome (components/scan)
def welcome() -> str:
    items = "".join(
        f'<li class="condition">{marker(CLASS_INFO[c]["tone"])}<span class="condition-text">'
        f'<span class="condition-name">{c}</span><span class="condition-kind">{CLASS_INFO[c]["kind"]}</span>'
        f'</span></li>' for c in CLASSES)
    return (f'<div class="welcome"><div class="welcome-mark">{logo_mark(44)}</div>'
            f'<h1>What would you like to check?</h1>'
            f'<p>Upload a photo of a rice leaf to get started. RiceGuard checks it for common leaf diseases, '
            f'shows which parts of the leaf it looked at, and suggests how to manage what it finds.</p>'
            f'<section class="conditions" aria-labelledby="conditions-title">'
            f'<h2 id="conditions-title" class="conditions-title">Common conditions RiceGuard can identify</h2>'
            f'<ul class="conditions-list">{items}</ul></section></div>')


def upload_card(error: bool) -> str:
    cls = "upload-area has-error" if error else "upload-area"
    return (f'<div class="{cls}" aria-label="Upload an image. Drag and drop or press Enter to browse.">'
            f'<div class="upload-icon">{svg("upload", 22, 1.8)}</div>'
            f'<div class="upload-title">Upload an image</div>'
            f'<div class="upload-sub">Drag and drop your image here or <span class="link">click to browse</span></div>'
            f'<div class="upload-meta">{UPLOAD["formats_label"]} · Maximum {UPLOAD["max_label"]}</div></div>')


def field_error(msg: str, extra: str = "") -> str:
    return f'<p class="field-error {extra}" role="alert">{escape(msg)}</p>'


def divider_or() -> str:
    return '<span class="divider-text">or</span>'


def photo_tips() -> str:
    tips = [("leaf", "One rice leaf per photo"), ("sun", "Even, natural lighting"),
            ("maximize", "Leaf fills most of the frame")]
    return '<ul class="tips">' + "".join(f"<li>{svg(i, 15)}{t}</li>" for i, t in tips) + "</ul>"


def camera_view() -> str:
    return (f'<div class="camera-view">{svg("camera", 26, 1.6)}'
            f'<p class="camera-view-title">Camera preview isn\'t available yet</p>'
            f'<p class="camera-view-sub">In-app capture will be added later. For now, use a sample leaf photo to '
            f'test the analysis, or open your device\'s camera or files.</p></div>')


def fake_button(label: str, icon: str, icon_size: int, cls: str) -> str:
    """Looks exactly like the React button; a transparent Streamlit file picker sits on top of it."""
    ic = svg(icon, icon_size) if icon else ""
    return f'<span class="btn {cls}" role="presentation">{ic}{escape(label)}</span>'


def fake_icon_button(icon: str, icon_size: int, extra: str = "") -> str:
    return f'<span class="icon-btn {extra}" role="presentation">{svg(icon, icon_size)}</span>'


# ---------------------------------------------------------------------------- session (components/session)
def turn_head(who: str, note: str, anchor: str) -> str:
    avatar = logo_mark(24) if who == "riceguard" else f'<span class="you-avatar" aria-hidden="true">{svg("user-round", 14)}</span>'
    n = f'<span class="turn-note">{escape(note)}</span>' if note else ""
    name = "You" if who == "user" else "RiceGuard"
    return (f'<header class="turn-head"><span class="turn-anchor" id="{anchor}"></span>{avatar}'
            f'<span class="turn-who">{name}</span>{n}</header>')


def attachment(image: dict) -> str:
    return (f'<figure class="attachment"><img src="{image["url"]}" '
            f'alt="Uploaded image: {escape(image["name"])}"/></figure>')


def file_meta(image: dict) -> str:
    dims = ""
    if image.get("width") and image.get("height"):
        dims = f'<span class="dot-sep"></span><span>{image["width"]} × {image["height"]}</span>'
    return (f'<div class="file-meta"><span class="file-name" title="{escape(image["name"])}">{escape(image["name"])}'
            f'</span><span class="dot-sep"></span><span>{fmt.file_type(image["type"])}</span>'
            f'<span class="dot-sep"></span><span>{fmt.file_bytes(image["size"])}</span>{dims}</div>')


def response_text(inner_html: str) -> str:
    return f'<p class="response-text">{inner_html}</p>'


def preview_tag(text: str) -> str:
    return f'<span class="preview-tag">{escape(text)}</span>'


def analyzing_label(text: str = "Analyzing your image…") -> str:
    return (f'<span class="pulse-dots" aria-hidden="true"><i></i><i></i><i></i></span>'
            f'<span class="shimmer-text">{escape(text)}</span>')


def analyzing_rest() -> str:
    return ('<div class="progress indeterminate" role="progressbar" aria-label="Analyzing"><span></span></div>'
            '<div class="skeleton-card" aria-hidden="true"><span class="sk sk-sm"></span>'
            '<span class="sk sk-lg"></span><span class="sk sk-md"></span></div>')


def notice_error(msg: str) -> str:
    return f'<div class="notice notice-error" role="alert">{svg("circle-alert", 16)}<span>{escape(msg)}</span></div>'


def question(text: str) -> str:
    return f'<p class="question-text">{escape(text)}</p>'


def thinking() -> str:
    return f'<div class="analyzing-row">{analyzing_label("Thinking about your question…")}</div>'


# ---------------------------------------------------------------------------- results (components/results)
def lead_in(result: dict) -> str:
    if result["disease"] == "Healthy":
        text = ("I've finished analyzing your image. This leaf looks healthy. I didn't find signs of Bacterial "
                "Blight, Leaf Blast, or Brown Spot.")
    else:
        text = f'I\'ve finished analyzing your image. I found signs of <strong>{result["disease"]}</strong> on this leaf:'
    tag = preview_tag("Mock result · detection model not connected yet") if result.get("is_mock") else ""
    return response_text(text) + tag


def _confidence(value: float) -> str:
    return (f'<div class="confidence"><span class="label">Confidence</span>'
            f'<div class="metric-value">{fmt.pct(value)}</div>'
            f'<div class="bar" role="meter" aria-valuemin="0" aria-valuemax="100" '
            f'aria-valuenow="{int(value * 100 + 0.5)}" aria-label="Confidence"><span style="width: {value * 100}%">'
            f'</span></div><p class="severity-note">How sure the model is about this result.</p></div>')


def _severity(severity, affected_pct: float) -> str:
    if not severity:
        return ('<div class="severity"><span class="label">Severity</span>'
                '<div class="metric-value" style="color: var(--c-healthy)">None</div>'
                '<div class="sev-none">No disease detected</div>'
                '<p class="severity-note">Severity is only estimated when a disease is detected.</p></div>')
    steps = "".join(
        f'<li class="sev-step{" active" if s == severity else ""}" style="--tone: {SEVERITY_INFO[s]["tone"]}"'
        f'{" aria-current=\"true\"" if s == severity else ""}>{s}</li>' for s in SEVERITIES)
    return (f'<div class="severity"><span class="label">Severity</span>'
            f'<div class="metric-value" style="color: {SEVERITY_INFO[severity]["tone"]}">{severity}</div>'
            f'<ol class="sev-scale" aria-label="Severity: {severity}, on a scale of Mild, Moderate, Severe">{steps}</ol>'
            f'<p class="severity-note">About {affected_pct:.1f}% of the leaf area is affected. '
            f'{SEVERITY_INFO[severity]["hint"]}</p></div>')


def _probabilities(probs: dict, top: str) -> str:
    rows = sorted(CLASSES, key=lambda c: -probs[c])
    return '<ul class="probs">' + "".join(
        f'<li class="{"top" if c == top else ""}"><span class="probs-name">{marker(CLASS_INFO[c]["tone"])}{c}</span>'
        f'<span class="probs-bar"><span style="width: {probs[c] * 100}%"></span></span>'
        f'<span class="probs-val">{fmt.pct(probs[c], 1)}</span></li>' for c in rows) + "</ul>"


def diagnosis_card(result: dict) -> str:
    """The "Detection result" card: condition, confidence, severity, all-class scores."""
    info = CLASS_INFO[result["disease"]]
    healthy = result["disease"] == "Healthy"
    icon = svg("circle-check", 22, cls="diag-icon healthy") if healthy else marker(info["tone"], "lg")
    kind = "" if healthy else f'<span class="diag-kind">{info["kind"]}</span>'
    probs = ""
    if result.get("probabilities"):
        probs = (f'<details class="expander"><summary>{svg("chevron-right", 16, cls="expander-icon")}'
                 f'Scores for all classes</summary>{_probabilities(result["probabilities"], result["disease"])}</details>')
    return (f'<section class="card result-card"><div class="card-eyebrow">Detection result</div>'
            f'<div class="diagnosis">{icon}<h2>{"Healthy" if healthy else result["disease"]}</h2>{kind}</div>'
            f'<p class="diag-cue">{info["cue"]}</p>'
            f'<div class="result-grid">{_confidence(result["confidence"])}'
            f'{_severity(result["severity"], result["affected_pct"])}</div>{probs}</section>')


def viewer_title() -> str:
    return '<span class="viewer-title">Image analysis</span>'


def viewer_stage(image: dict, heat_url: str, label: str, tone: str, heat_cls: str) -> str:
    return (f'<div class="viewer-stage"><div class="viewer-frame">'
            f'<img src="{image["url"]}" alt="Uploaded leaf: {escape(image["name"])}"/>'
            f'<img src="{heat_url}" alt="Highlighted areas (Grad-CAM heatmap)" class="viewer-heat {heat_cls}"/>'
            f'<span class="viewer-label">{marker(tone)}{escape(label)}</span></div></div>')


def viewer_legend() -> str:
    return ('<div class="legend"><span class="muted">Less influence</span><span class="legend-bar"></span>'
            '<span class="muted">More</span></div>')


def overlay_label() -> str:
    return '<span class="muted overlay-label">Overlay</span>'


def viewer_note() -> str:
    return ('<span class="muted">Switch to Highlighted areas to see which parts of the leaf influenced '
            'the result.</span>')


def guidance_card(result: dict) -> str:
    healthy = result["disease"] == "Healthy"
    what = ""
    if result.get("explanation"):
        what = (f'<div class="guidance-block"><div class="label">What this means</div>'
                f'<p>{escape(result["explanation"])}</p></div>')
    lines = [s for s in re.split(r"(?<=\.)\s+", result["treatment"]) if s]
    steps = "".join(f"<li>{escape(s)}</li>" for s in lines)
    return (f'<section class="card guidance"><header class="guidance-head">'
            f'<div class="guidance-icon">{svg("shield-check", 19, 1.8)}</div>'
            f'<div><h3>{"Recommendation" if healthy else "Treatment guidance"}</h3>'
            f'<div class="guidance-source">Based on Philippine agricultural guidelines</div></div></header>'
            f'<div class="guidance-body">{what}<div class="guidance-block">'
            f'<div class="label">{"Next steps" if healthy else "Recommended management"}</div>'
            f'<ul class="guidance-list">{steps}</ul></div>'
            f'<p class="guidance-note">{svg("info", 15)}<span>RiceGuard judges from the photo only. It does not '
            f'consider soil, weather, or irrigation. For serious outbreaks, consult your local agricultural '
            f'office.</span></p></div></section>')


def response_meta(created_label: str, model) -> str:
    m = f'<span class="dot-sep"></span>{escape(model)}' if model else ""
    return f'<div class="response-meta muted small">Analyzed {created_label}{m}</div>'


def composer_note() -> str:
    return ('<p class="composer-note muted small">RiceGuard judges from the photo only. Check important decisions '
            'with your local agricultural office.</p>')


# ---------------------------------------------------------------------------- pages
def page_head(title: str, sub: str) -> str:
    return f'<div class="page-head"><div><h1>{escape(title)}</h1><p class="muted">{escape(sub)}</p></div></div>'


def history_empty() -> str:
    return (f'<div class="empty-icon">{svg("history", 24)}</div><h2>No scans yet</h2>'
            f'<p class="muted">Analyze a rice leaf image and it will be saved here.</p>')


def history_row(scan: dict, date_label: str, relative: str, first: bool) -> str:
    r = scan["result"]
    sev_tone = SEVERITY_INFO[r["severity"]]["tone"] if r["severity"] else "var(--c-healthy)"
    sev_text = f'{r["severity"]} severity' if r["severity"] else "No disease"
    sep = "" if first else " history-sep"
    return (f'<div class="history-btn{sep}"><img class="history-thumb" src="{scan["image"]["url"]}" alt=""/>'
            f'<div class="history-main"><div class="history-title">{marker(CLASS_INFO[r["disease"]]["tone"])}'
            f'{r["disease"]}<span class="sev-pill" style="color: {sev_tone}">{sev_text}</span></div>'
            f'<div class="history-meta"><span title="{relative}">{date_label}</span><span class="dot-sep"></span>'
            f'<span class="history-file">{escape(scan["image"]["name"])}</span></div></div>'
            f'<div class="history-conf"><span class="label">Confidence</span><span>{fmt.pct(r["confidence"])}</span>'
            f'</div><span class="history-view"><span class="only-desktop-inline">View results</span>'
            f'{svg("chevron-right", 17)}</span></div>')


def about() -> str:
    classes = "".join(
        f'<div class="about-class">{marker(CLASS_INFO[c]["tone"])}<div><div class="about-class-name">{c}</div>'
        f'<div class="muted small">{CLASS_INFO[c]["cue"]}</div></div></div>' for c in CLASSES)
    steps = "".join(
        f'<li><span class="step-num">{i + 1}</span><div><div class="step-title">{t}</div>'
        f'<p class="muted">{b}</p></div></li>' for i, (t, b) in enumerate(STEPS))
    limits = "".join(f"<li>{l}</li>" for l in LIMITS)
    return (
        f'<header class="about-hero">{logo_mark(40)}<h1>About RiceGuard</h1><p class="lead">RiceGuard is a web '
        f'application that helps Filipino rice farmers identify common rice leaf diseases from a photo. It detects '
        f'the disease, estimates how severe it is, shows which part of the leaf the result is based on, and '
        f'recommends how to manage it.</p></header>'
        f'<section class="about-section"><h2>Why it matters</h2><p>Rice provides about half of the daily energy '
        f'intake of Filipinos, and pests and diseases cause an estimated 37% yield loss for rice farmers each year. '
        f'Brown Spot, Leaf Blast, and Bacterial Blight look alike and are hard to tell apart by eye, and manual '
        f'inspection is slow and error-prone. RiceGuard supports early detection while showing its reasoning, so '
        f'users can trust and verify the result.</p></section>'
        f'<section class="about-section"><h2>What it detects</h2><div class="about-classes">{classes}</div></section>'
        f'<section class="about-section"><h2>How it works</h2><ol class="steps">{steps}</ol></section>'
        f'<section class="about-section"><h2>Data</h2><p>The model is trained on public rice leaf datasets '
        f'(Mendeley Rice Leaf Disease Dataset and the Kaggle Five-Crop Diseases Dataset). It is tested on the '
        f'Zambales Rice Dataset, a separate set of field photos from Iba and Botolan, Zambales, verified with the '
        f'Provincial Agricultural Office.</p></section>'
        f'<section class="about-section"><h2>Limitations</h2><ul class="bullets">{limits}</ul></section>'
        f'<section class="about-section about-project"><h2>Project</h2><p class="project-title">{APP["full_title"]}</p>'
        f'<dl class="meta-grid"><dt>Type</dt><dd>{APP["degree"]}</dd><dt>Date</dt><dd>{APP["date"]}</dd>'
        f'<dt>Authors</dt><dd>{" · ".join(APP["authors"])}</dd><dt>Version</dt>'
        f'<dd>v{APP["version"]} ({APP["stage"]})</dd></dl></section>')


def settings_group_title(title: str) -> str:
    return f'<h2 class="settings-group-title">{escape(title)}</h2>'


def setting_text(title: str, sub: str) -> str:
    return f'<div><div class="setting-title">{escape(title)}</div><div class="muted small">{escape(sub)}</div></div>'


def opacity_value(v: float) -> str:
    return f'<span class="mono opacity-value">{int(v * 100 + 0.5)}%</span>'


def settings_foot() -> str:
    return f'<p class="muted small settings-foot">{APP["name"]} v{APP["version"]} · {APP["stage"]}</p>'
