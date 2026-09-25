"""
RiceGuard — Streamlit app.

A copy of the React UI in web/ (same screens, wording, colours and flow), built in Streamlit so the whole
app — model, Grad-CAM, severity and LLM — can later run as one Python program on Streamlit Community Cloud.

The model is still MOCKED (riceguard_ui/mock.py): results are presets and the heatmap is random blobs,
exactly like the React preview. Replace build_mock_result() with the real pipeline later; the UI stays put.

Run locally:  streamlit run app.py
"""
import base64
import io
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import streamlit as st
from PIL import Image, ImageOps

from riceguard_ui import fmt, views
from riceguard_ui.brand import favicon
from riceguard_ui.content import (CLASS_INFO, CLASSES, DEFAULT_SETTINGS, MOCK_HISTORY, TITLES, UPLOAD, mock_answer,
                                  suggestions_for)
from riceguard_ui.icons import ICONS, mask_url
from riceguard_ui.mock import build_mock_result, draw_sample_leaf, hash_string, pick_mock, sample_leaf_file

STYLES = Path(__file__).parent / "riceguard_ui" / "styles"

st.set_page_config(page_title="RiceGuard", page_icon=favicon(), layout="wide", initial_sidebar_state="auto")
ss = st.session_state


# ============================================================================ helpers
def uid() -> str:
    return uuid.uuid4().hex[:12]


def now() -> datetime:
    return datetime.now(timezone.utc)


def data_uri(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def tz_offset():
    """The viewer's time zone, like the browser's getTimezoneOffset() (UTC+8 -> -480)."""
    try:
        return st.context.timezone_offset
    except Exception:
        return 0


def btn(label, name, *, variant="secondary", size="md", icon=None, icon_size=18, block=False,
        on_click=None, args=None, disabled=False):
    """A Streamlit button drawn like the React one. The key carries the look (see streamlit.css)."""
    key = f"b__{variant}__{size}__i-{icon or 'none'}__s{icon_size}__{name}"
    return st.button(label, key=key, on_click=on_click, args=args, disabled=disabled,
                     type="primary" if variant == "primary" else "secondary", width="stretch" if block else "content")


def html(markup: str):
    st.html(markup)


# ============================================================================ styles
_mask = mask_url


def _css_file(name: str) -> str:
    """A stylesheet without comments. Streamlit drops a style block that contains an angle bracket."""
    css = re.sub(r"/\*.*?\*/", "", (STYLES / name).read_text(encoding="utf-8"), flags=re.S)
    assert "<" not in css, f"{name} contains an angle bracket"
    return css


@lru_cache(maxsize=None)
def static_css() -> str:
    icons = "".join(f'[class*="__i-{n}__"] button{{--rg-icon:{_mask(n)}}}' for n in ICONS)
    parts = [
        f'[data-testid="stSidebarCollapseButton"] button{{--rg-icon:{_mask("panel-left-close")}}}',
        f'[data-testid="stExpandSidebarButton"]{{--rg-icon:{_mask("panel-left-open")}}}',
        f'@media (max-width: 860px){{[data-testid="stExpandSidebarButton"]{{--rg-icon:{_mask("menu")}}}}}',
        f'[data-testid="stChatInputSubmitButton"]{{--rg-icon:{_mask("arrow-up")}}}',
        f'[data-testid="stDialog"] section[role="dialog"] > button{{--rg-icon:{_mask("x")}}}',
        f'.st-key-theme_toggle button:nth-of-type(1){{--rg-icon:{_mask("sun")}}}',
        f'.st-key-theme_toggle button:nth-of-type(2){{--rg-icon:{_mask("moon")}}}',
        f'.st-key-set_theme button:nth-of-type(1){{--rg-icon:{_mask("sun")}}}',
        f'.st-key-set_theme button:nth-of-type(2){{--rg-icon:{_mask("moon")}}}',
        f'.st-key-set_theme button:nth-of-type(3){{--rg-icon:{_mask("monitor")}}}',
        f'[class*="st-key-segview__"] button:nth-of-type(1){{--rg-icon:{_mask("eye")}}}',
        f'[class*="st-key-segview__"] button:nth-of-type(2){{--rg-icon:{_mask("layers")}}}',
    ]
    return _css_file("app.css") + _css_file("streamlit.css") + icons + "".join(parts)


@lru_cache(maxsize=None)
def token_css(theme: str) -> str:
    """tokens.css with the light values, plus the dark values when the dark theme is on."""
    t = _css_file("tokens.css")
    light, dark = t.split(':root[data-theme="dark"]', 1)
    return light + (":root:root" + dark if theme == "dark" else "")


def resolved_theme() -> str:
    pref = ss.settings["theme"]
    if pref != "system":
        return pref
    try:
        return st.context.theme.type or "light"
    except Exception:
        return "light"


# ============================================================================ state
@st.cache_data(show_spinner=False)
def _sample_leaf(disease: str, seed: int) -> bytes:
    return draw_sample_leaf(disease, seed)


@st.cache_data(show_spinner=False)
def _mock_result(preset: dict, seed: int, width: int, height: int, lang: str) -> dict:
    r = build_mock_result(preset, seed, (width, height), lang)
    r["heatmap"] = data_uri(r["heatmap"], "image/jpeg")
    return r


def mock_history() -> list:
    """MOCK scan history for the Scan History page (web/src/data/mockHistory.ts)."""
    t0 = now()
    scans = []
    for i, s in enumerate(MOCK_HISTORY):
        name = s["name"]
        mime = "image/png" if name.endswith(".png") else "image/webp" if name.endswith(".webp") else "image/jpeg"
        image = {"name": name, "size": 1_200_000 + s["seed"] * 53_211, "type": mime, "width": 640, "height": 480,
                 "url": data_uri(_sample_leaf(s["preset"]["disease"], s["seed"]), "image/jpeg")}
        scans.append({"id": f"mock-{i}", "created_at": t0 - timedelta(hours=s["hours_ago"]), "image": image,
                      "result": _mock_result(s["preset"], s["seed"], 640, 480, "English")})
    return scans


def init_state():
    if "settings" in ss:
        return
    ss.settings = dict(DEFAULT_SETTINGS)
    ss.view = "new-scan"
    ss.turns = []
    ss.history = mock_history()
    ss.welcome_error = None
    ss.composer_error = None
    ss.upload_n = 0          # bumped after every upload so the file pickers start empty again
    ss.last_mock = None
    ss.pending = None        # work to finish at the end of this run: ("analysis", id) or ("answer", id, question)
    ss.scroll_to = None
    ss.camera_open = False
    ss.confirm_clear = False
    ss.close_sidebar = False
    ss.opacity = {}          # heatmap overlay strength per result (kept while the slider is hidden)


def find(tid):
    return next((t for t in ss.turns if t["id"] == tid), None)


def analysis_for(image_turn_id):
    return next((t for t in ss.turns if t["kind"] == "analysis" and t["image_turn_id"] == image_turn_id), None)


def last_done():
    return next((t for t in reversed(ss.turns) if t["kind"] == "analysis" and t["status"] == "done"), None)


# ============================================================================ actions (App.tsx)
def to_selected_image(name: str, data: bytes, mime: str):
    """Validate a file and read its dimensions. Returns an image or an error message."""
    if mime not in UPLOAD["accept"]:
        return f"That file type isn't supported. Upload a {UPLOAD['formats_label']} image."
    if len(data) > UPLOAD["max_bytes"]:
        return f"That file is too large. The maximum size is {UPLOAD['max_label']}."
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
        img.load()
    except Exception:
        return "This image couldn't be opened. Try a different file."
    w, h = img.size
    shown = img.copy()
    shown.thumbnail((1600, 1600))
    buf = io.BytesIO()
    if shown.mode in ("RGBA", "LA", "P") and mime == "image/png":
        shown.save(buf, "PNG")
        url = data_uri(buf.getvalue(), "image/png")
    else:
        shown.convert("RGB").save(buf, "JPEG", quality=88)
        url = data_uri(buf.getvalue(), "image/jpeg")
    return {"name": name, "size": len(data), "type": mime, "width": w, "height": h, "url": url}


def add_image(name: str, data: bytes, mime: str):
    """Add an image to the session: your image, then RiceGuard's "ready" response."""
    res = to_selected_image(name, data, mime)
    if isinstance(res, str):
        if not ss.turns:
            ss.welcome_error = res
        else:
            ss.composer_error = res
        return
    ss.welcome_error = ss.composer_error = None
    image_turn_id = uid()
    ss.turns += [{"id": image_turn_id, "kind": "image", "created_at": now(), "image": res},
                 {"id": uid(), "kind": "analysis", "created_at": now(), "image_turn_id": image_turn_id,
                  "status": "ready"}]
    ss.scroll_to = image_turn_id


def replace_image(image_turn_id: str, name: str, data: bytes, mime: str):
    res = to_selected_image(name, data, mime)
    if isinstance(res, str):
        ss.composer_error = res
        return
    ss.composer_error = None
    t = find(image_turn_id)
    if t:
        t["image"] = res


def remove_image(image_turn_id: str):
    ss.turns = [t for t in ss.turns if t["id"] != image_turn_id
                and not (t["kind"] == "analysis" and t["image_turn_id"] == image_turn_id)]


def on_upload(key: str, target):
    """A file picker got a file: add it (welcome, question box, camera dialog) or swap an image."""
    f = ss.get(key)
    if f is None:
        return
    if isinstance(target, tuple) and target[0] == "replace":
        replace_image(target[1], f.name, f.getvalue(), f.type)
    else:
        add_image(f.name, f.getvalue(), f.type)
    ss.upload_n += 1


def analyze(analysis_turn_id: str):
    t = find(analysis_turn_id)
    if not t:
        return
    t["status"], t["error"] = "loading", None
    ss.pending, ss.pending_started = ("analysis", analysis_turn_id), False
    ss.scroll_to = analysis_turn_id


def cancel(analysis_turn_id: str):
    t = find(analysis_turn_id)
    if t and t["status"] == "loading":
        t["status"] = "ready"
    if ss.pending and ss.pending[1] == analysis_turn_id:
        ss.pending = None


def ask(text: str):
    answer_id = uid()
    ss.turns += [{"id": uid(), "kind": "question", "created_at": now(), "text": text},
                 {"id": answer_id, "kind": "answer", "created_at": now(), "status": "loading"}]
    ss.pending, ss.pending_started = ("answer", answer_id, text), False
    ss.scroll_to = answer_id


def on_ask():
    text = (ss.get("followup") or "").strip()
    if text and last_done() and not busy():
        ask(text)


def navigate(view: str):
    if ss.view != view:
        ss.scroll_to = "__top__"
    ss.view = view
    ss.close_sidebar = True


def new_scan():
    """Clear the session and return to the welcome/upload state."""
    ss.pending = None
    ss.welcome_error = ss.composer_error = None
    navigate("new-scan")
    ss.turns = []
    ss.scroll_to = "__top__"


def open_from_history(scan_id: str):
    """Reopen a saved scan as a session (image + RiceGuard's response)."""
    s = next((x for x in ss.history if x["id"] == scan_id), None)
    if not s:
        return
    ss.pending = None
    image_turn_id = f"{s['id']}-img"
    ss.turns = [{"id": image_turn_id, "kind": "image", "created_at": s["created_at"], "image": s["image"],
                 "restored": True},
                {"id": s["id"], "kind": "analysis", "created_at": s["created_at"], "image_turn_id": image_turn_id,
                 "status": "done", "result": s["result"], "restored": True}]
    ss.opacity.pop(s["id"], None)
    ss.pop(f"segview__{s['id']}", None)
    ss.composer_error = None
    navigate("new-scan")


def open_camera():
    ss.camera_open = True


def close_camera():
    ss.camera_open = False


def set_setting(name: str, key: str):
    ss.settings[name] = ss[key]


def busy() -> bool:
    return any((t["kind"] in ("analysis", "answer")) and t.get("status") == "loading" for t in ss.turns)


def finish_pending():
    """Finish the analysis / answer shown as "in progress" (the mock waits like the React one).

    Two runs: the first only draws the "Analyzing…" state and ends, so Streamlit clears the buttons that
    no longer apply; a hidden button, clicked by the page, then starts the run that does the work."""
    p = ss.pending
    if not p:
        return
    btn("continue", "tick", variant="hidden")
    if not ss.get("pending_started"):
        ss.pending_started = True
        st.html(f"<script>/*{uid()}*/setTimeout(function(){{var b=document.querySelector("
                f"'[class*=\"__tick\"] button');b&&b.click();}},30);</script>", unsafe_allow_javascript=True)
        return
    if p[0] == "analysis":
        time.sleep(2.2)
        t = find(p[1])
        img_turn = t and find(t["image_turn_id"])
        if not t or t["status"] != "loading" or not img_turn:
            ss.pending = None
            return
        img = img_turn["image"]
        preset, ss.last_mock = pick_mock(img["name"], ss.settings["mock_result"], ss.last_mock)
        seed = hash_string(f"{img['name']}:{img['size']}:{int(time.time() * 1000)}")
        result = _mock_result(preset, seed, img["width"] or 800, img["height"] or 600,
                              ss.settings["explanation_language"])
        t.update(status="done", result=result, created_at=now())
        if ss.settings["save_history"]:
            ss.history.insert(0, {"id": t["id"], "created_at": t["created_at"], "image": img, "result": result})
        ss.scroll_to = t["id"]
    else:
        time.sleep(1.1)
        a = find(p[1])
        if a:
            d = last_done()
            a.update(status="done", text=mock_answer(p[2], d["result"] if d else None), is_mock=True)
            ss.scroll_to = a["id"]
    ss.pending = None
    st.rerun()


# ============================================================================ layout
def sidebar():
    with st.sidebar:
        html(f'<div class="sidebar-head">{views.logo()}</div>')
        btn("New Scan", "newscan", variant="primary", icon="plus", block=True, on_click=new_scan)
        for view, label, icon in (("new-scan", "New Scan", "scan-line"), ("history", "Scan History", "history"),
                                  ("about", "About", "info")):
            btn(label, f"nav_{view.replace('-', '')}", variant="navon" if ss.view == view else "nav", icon=icon,
                block=True, on_click=navigate, args=(view,))
        with st.container(key="sidebar_foot"):
            btn("Settings", "nav_settings", variant="navon" if ss.view == "settings" else "nav", icon="settings",
                block=True, on_click=navigate, args=("settings",))
            html(views.version_line())


def topbar(theme: str):
    ss["theme_toggle"] = theme
    with st.container(key="topbar", horizontal=True, vertical_alignment="center"):
        html(views.topbar_left(None if ss.view == "new-scan" else TITLES[ss.view]))
        st.segmented_control("Color theme", ["light", "dark"], key="theme_toggle", required=True,
                             format_func=lambda v: "Light mode" if v == "light" else "Dark mode",
                             label_visibility="collapsed", on_change=set_setting, args=("theme", "theme_toggle"))


def file_picker(label: str, key_name: str, target, disabled: bool = False):
    """An invisible Streamlit uploader laid over the React-styled card / button drawn just before it."""
    key = f"upl__{key_name}_{ss.upload_n}"
    st.file_uploader(label, key=key, label_visibility="collapsed", disabled=disabled,
                     max_upload_size=UPLOAD["max_bytes"] // (1024 * 1024), on_change=on_upload, args=(key, target))


# ---------------------------------------------------------------------------- New Scan: welcome
def welcome_page():
    with st.container(key="page__welcome"):
        html(views.welcome())
        with st.container(key="upload_wrap"):
            html(views.upload_card(bool(ss.welcome_error)))
            file_picker("Upload an image", "welcome", "welcome")
        if ss.welcome_error:
            html(views.field_error(ss.welcome_error))
        with st.container(key="upload_alt", horizontal=True, horizontal_alignment="center",
                          vertical_alignment="center"):
            html(views.divider_or())
            btn("Take a Photo", "takephoto", icon="camera", icon_size=17, on_click=open_camera)
        html(views.photo_tips())


# ---------------------------------------------------------------------------- New Scan: session
def turn(t: dict):
    kind, tid = t["kind"], t["id"]
    who = "user" if kind in ("image", "question") else "riceguard"
    note = {"image": "uploaded an image", "question": "asked"}.get(kind, "")
    anim = "still" if t.get("restored") else "anim"
    with st.container(key=f"turn__{anim}__{tid}"):
        html(views.turn_head(who, note, f"turn-{tid}"))
        with st.container(key=f"tbody__{tid}"):
            if kind == "image":
                image_turn(t)
            elif kind == "analysis":
                analysis_turn(t)
            elif kind == "question":
                html(views.question(t["text"]))
            elif t["status"] == "loading":
                html(views.thinking())
            else:
                html(views.response_text(t["text"]) + (
                    views.preview_tag("Mock response · explanation service not connected yet") if t.get("is_mock") else ""))


def image_turn(t: dict):
    tid, image = t["id"], t["image"]
    html(views.attachment(image))
    a = analysis_for(tid)
    editable = a is not None and a["status"] == "ready"
    with st.container(key=f"fileinfo__{tid}", horizontal=True, vertical_alignment="center"):
        html(views.file_meta(image))
        if editable:
            with st.container(key=f"factions__{tid}", horizontal=True, vertical_alignment="center"):
                with st.container(key=f"ovlbtn__chg_{tid}"):
                    html(views.fake_button("Change image", "refresh-cw", 14, "btn-ghost btn-sm"))
                    file_picker("Change image", f"chg_{tid}", ("replace", tid))
                btn("Remove", f"rm_{tid}", variant="ghostdanger", size="sm", icon="trash-2", icon_size=14,
                    on_click=remove_image, args=(tid,))


def analysis_turn(t: dict):
    tid, status = t["id"], t["status"]
    if status == "ready":
        with st.container(key=f"resp__{tid}"):
            html(views.response_text("Got your image. Check that the leaf is clear and in focus, then start the "
                                     "analysis.").replace('class="response-text"', 'class="response-text last"'))
            btn("Analyze Image", f"analyze_{tid}", variant="primary", size="lg", icon="scan-search", icon_size=19,
                on_click=analyze, args=(tid,))
    elif status == "loading":
        with st.container(key=f"analyzing__{tid}"):
            with st.container(key=f"anarow__{tid}", horizontal=True, vertical_alignment="center"):
                html(f'<div class="analyzing-row">{views.analyzing_label()}</div>')
                btn("Cancel", f"cancel_{tid}", variant="ghost", size="sm", on_click=cancel, args=(tid,))
            html(views.analyzing_rest())
    elif status == "error":
        with st.container(key=f"resp__{tid}"):
            html(views.notice_error(t.get("error") or "I couldn't analyze this image."))
            btn("Try again", f"retry_{tid}", icon="refresh-cw", icon_size=16, on_click=analyze, args=(tid,))
    elif t.get("result"):
        results(t)


def results(t: dict):
    """RiceGuard's completed response: lead-in → detection result → visual analysis → treatment guidance."""
    tid, r = t["id"], t["result"]
    image = find(t["image_turn_id"])["image"]
    rev = "still" if t.get("restored") else "anim"
    healthy = r["disease"] == "Healthy"
    with st.container(key=f"resp__{tid}"):
        with st.container(key=f"rev__{rev}__d0__{tid}_lead"):
            html(views.lead_in(r))
        with st.container(key=f"rev__{rev}__d1__{tid}_card"):
            html(views.diagnosis_card(r))
        with st.container(key=f"rev__{rev}__d2__{tid}_view"):
            html(views.response_text("These are the areas of the leaf that most influenced the result:"))
            heatmap_viewer(tid, r, image)
        with st.container(key=f"rev__{rev}__d3__{tid}_care"):
            html(views.response_text("Here's what to do next:" if healthy else f"Here's how to manage {r['disease']}:")
                 + views.guidance_card(r))
        with st.container(key=f"rev__{rev}__d4__{tid}_meta"):
            html(views.response_meta(fmt.date_time(t["created_at"], tz_offset()), r.get("model")))


def heatmap_viewer(tid: str, r: dict, image: dict):
    """The uploaded image with a toggleable Grad-CAM overlay of the areas that drove the result."""
    seg_key = f"segview__{tid}"
    if seg_key not in ss:
        ss[seg_key] = "heat" if ss.settings["show_heatmap_by_default"] else "original"
    opacity = ss.opacity.setdefault(tid, ss.settings["heatmap_opacity"])
    with st.container(key=f"viewer__{tid}"):
        with st.container(key=f"vtool__{tid}", horizontal=True, vertical_alignment="center"):
            html(views.viewer_title())
            st.segmented_control("Image view", ["original", "heat"], key=seg_key, required=True,
                                 format_func=lambda v: "Original" if v == "original" else "Highlighted areas",
                                 label_visibility="collapsed")
        show = ss[seg_key] == "heat"
        label = f"{r['disease']} · {fmt.pct(r['confidence'])}"
        html(views.viewer_stage(image, r["heatmap"], label, CLASS_INFO[r["disease"]]["tone"], f"heat-{tid}"))
        ss.dyn_css.append(f".heat-{tid}{{opacity:{opacity if show else 0}}}")
        with st.container(key=f"vfoot__{tid}", horizontal=True, vertical_alignment="center"):
            if show:
                html(views.viewer_legend())
                with st.container(key=f"opctl__{tid}", horizontal=True, vertical_alignment="center"):
                    html(views.overlay_label())
                    k = f"sl__op_{tid}"
                    ss[k] = opacity
                    st.slider("Overlay", 0.1, 0.9, step=0.05, key=k, label_visibility="collapsed",
                              on_change=lambda k=k, tid=tid: ss.opacity.__setitem__(tid, ss[k]))
            else:
                html(views.viewer_note())


def composer():
    """Persistent input at the bottom of the session: "Ask a question about this result…" + attach an image."""
    d = last_done()
    is_busy = busy()
    can_ask = d is not None
    asked_since = d is not None and any(t["kind"] == "question" for t in ss.turns[ss.turns.index(d):])
    suggestions = suggestions_for(d["result"]) if d and not asked_since else []
    placeholder = ("RiceGuard is working on it…" if is_busy else
                   "Ask a question about this result…" if can_ask else "Ask about the result once it's ready")
    with st.container(key="composer_wrap"):
        with st.container(key="composer", horizontal=True, vertical_alignment="center"):
            with st.container(key="ovlbtn__attach"):
                html(views.fake_icon_button("image-plus", 19, "is-disabled" if is_busy else ""))
                file_picker("Analyze another image", "attach", "attach", disabled=is_busy)
            st.chat_input(placeholder, key="followup", disabled=(not can_ask or is_busy), on_submit=on_ask)
        if ss.composer_error:
            html(views.field_error(ss.composer_error, "composer-note"))
        elif suggestions and can_ask and not is_busy:
            with st.container(key="suggestions", horizontal=True):
                for i, s in enumerate(suggestions):
                    btn(s, f"sugg_{i}", variant="sugg", on_click=ask, args=(s,))
        else:
            html(views.composer_note())


def session_page():
    with st.container(key="page__session"):
        with st.container(key="stream"):
            for t in ss.turns:
                if t["kind"] == "analysis" and not find(t["image_turn_id"]):
                    continue
                turn(t)
        composer()


# ---------------------------------------------------------------------------- other pages
def history_page():
    n = len(ss.history)
    with st.container(key="page__wide"):
        html(views.page_head("Scan History", f"{n} previous scans" if n else "Your previous scans will appear here."))
        if not n:
            with st.container(key="history_empty"):
                html(views.history_empty())
                btn("New Scan", "hist_newscan", variant="primary", icon="plus", icon_size=17, on_click=new_scan)
            return
        tz = tz_offset()
        with st.container(key="history_list"):
            for i, s in enumerate(ss.history):
                with st.container(key=f"histrow__{s['id']}"):
                    html(views.history_row(s, fmt.date_time(s["created_at"], tz), fmt.relative(s["created_at"], tz),
                                           i == 0))
                    btn(f"View results for {s['image']['name']}", f"open_{s['id']}", variant="overlay",
                        on_click=open_from_history, args=(s["id"],))


def about_page():
    with st.container(key="page__read"):
        html(views.about())


def settings_page():
    s = ss.settings
    with st.container(key="page__read"):
        html(views.page_head("Settings", "Preferences are saved in this browser."))

        with st.container(key="sgroup__appearance"):
            html(views.settings_group_title("Appearance"))
            with st.container(key="srow__only__theme", horizontal=True, vertical_alignment="center"):
                html(views.setting_text("Theme", "Choose light, dark, or match your device."))
                ss["set_theme"] = s["theme"]
                st.segmented_control("Theme", ["light", "dark", "system"], key="set_theme", required=True,
                                     format_func=str.capitalize, label_visibility="collapsed",
                                     on_change=set_setting, args=("theme", "set_theme"))

        with st.container(key="sgroup__results"):
            html(views.settings_group_title("Results"))
            with st.container(key="srow__first__showheat", horizontal=True, vertical_alignment="center"):
                html(views.setting_text("Show Grad-CAM heatmap by default",
                                        "Open results with the heatmap overlay turned on."))
                ss["sw__showheat"] = s["show_heatmap_by_default"]
                st.toggle("Show Grad-CAM heatmap by default", key="sw__showheat", label_visibility="collapsed",
                          on_change=set_setting, args=("show_heatmap_by_default", "sw__showheat"))
            with st.container(key="srow__mid__opacity", horizontal=True, vertical_alignment="center"):
                html(views.setting_text("Heatmap opacity", "Default strength of the overlay."))
                with st.container(key="opval", horizontal=True, vertical_alignment="center"):
                    ss["sl__settings_opacity"] = s["heatmap_opacity"]
                    st.slider("Heatmap opacity", 0.1, 0.9, step=0.05, key="sl__settings_opacity",
                              label_visibility="collapsed", on_change=set_setting,
                              args=("heatmap_opacity", "sl__settings_opacity"))
                    html(views.opacity_value(s["heatmap_opacity"]))
            with st.container(key="srow__last__lang", horizontal=True, vertical_alignment="center"):
                html(views.setting_text("Explanation language", "Language used for the plain-language explanation."))
                ss["sel__lang"] = s["explanation_language"]
                st.selectbox("Explanation language", ["English", "Filipino"], key="sel__lang",
                             label_visibility="collapsed", on_change=set_setting,
                             args=("explanation_language", "sel__lang"))

        with st.container(key="sgroup__history"):
            html(views.settings_group_title("Scan history"))
            with st.container(key="srow__first__savehist", horizontal=True, vertical_alignment="center"):
                html(views.setting_text("Save scans to history", "Keep a record of analyzed images on this device."))
                ss["sw__savehist"] = s["save_history"]
                st.toggle("Save scans to history", key="sw__savehist", label_visibility="collapsed",
                          on_change=set_setting, args=("save_history", "sw__savehist"))
            n = len(ss.history)
            with st.container(key="srow__last__clear", horizontal=True, vertical_alignment="center"):
                html(views.setting_text("Clear scan history", f"{n} saved {'scan' if n == 1 else 'scans'}"))
                if ss.confirm_clear:
                    with st.container(key="srowctl__confirm", horizontal=True, vertical_alignment="center"):
                        btn("Cancel", "clear_cancel", variant="ghost", size="sm",
                            on_click=lambda: ss.__setitem__("confirm_clear", False))
                        btn("Clear", "clear_yes", variant="danger", size="sm", on_click=clear_history)
                else:
                    btn("Clear", "clear_ask", variant="secondary", size="sm", icon="trash-2", icon_size=15,
                        disabled=n == 0, on_click=lambda: ss.__setitem__("confirm_clear", True))

        with st.container(key="sgroup__testing"):
            html(views.settings_group_title("Testing"))
            with st.container(key="srow__only__mock", horizontal=True, vertical_alignment="center"):
                html(views.setting_text("Mock detection result",
                                        "The detection model isn't connected yet. Choose what Analyze Image returns."))
                ss["sel__mock"] = s["mock_result"]
                st.selectbox("Mock detection result", ["Random"] + CLASSES, key="sel__mock",
                             label_visibility="collapsed", on_change=set_setting, args=("mock_result", "sel__mock"))

        html(views.settings_foot())


def clear_history():
    ss.history = []
    ss.confirm_clear = False


@st.dialog("Take a photo", width="small", on_dismiss=close_camera)
def camera_dialog():
    """Placeholder for "Take a Photo": a sample leaf photo for testing, or the device camera / file picker."""
    with st.container(key="dialog_body"):
        html(views.camera_view())
    with st.container(key="dialog_actions", horizontal=True, vertical_alignment="center"):
        if btn("Cancel", "cam_cancel", variant="ghost"):
            close_camera()
            st.rerun()
        with st.container(key="ovlbtn__camfiles"):
            html(views.fake_button("Open camera or files", "", 0, "btn-secondary"))
            f = st.file_uploader("Open camera or files", key=f"upl__cam_{ss.upload_n}",
                                 label_visibility="collapsed")
        if f is not None:
            add_image(f.name, f.getvalue(), f.type)
            ss.upload_n += 1
            close_camera()
            st.rerun()
        if btn("Use sample photo", "cam_sample", variant="primary"):
            name, data = sample_leaf_file()
            add_image(name, data, "image/jpeg")
            close_camera()
            st.rerun()


def scripts():
    """Small page scripts: scroll to the newest step (like the React session) and close the phone menu."""
    out = []
    if ss.scroll_to:
        target = ss.scroll_to
        ss.scroll_to = None
        if target == "__top__":
            out.append("document.querySelector('section.stMain')?.scrollTo({top: 0});")
        else:
            out.append(
                "(function(){var n=0,go=function(){var el=document.getElementById('turn-%s');if(!el)return false;"
                "var r=matchMedia('(prefers-reduced-motion: reduce)').matches;"
                "el.scrollIntoView({behavior:r?'auto':'smooth',block:'start'});return true;};"
                "var t=setInterval(function(){if(go()||++n>40)clearInterval(t);},50);})();" % target)
    if ss.close_sidebar:
        ss.close_sidebar = False
        out.append("if(matchMedia('(max-width: 860px)').matches&&document.querySelector("
                   "'section[data-testid=stSidebar][aria-expanded=true]')){var b=document.querySelector("
                   "'[data-testid=stSidebarCollapseButton] button');b&&b.click();}")
    if out:
        st.html(f"<script>/*{uid()}*/{''.join(out)}</script>", unsafe_allow_javascript=True)


# ============================================================================ page
init_state()
ss.dyn_css = []
theme = resolved_theme()
st.html(f"<style>{token_css(theme)}{static_css()}</style>")

sidebar()
topbar(theme)
if ss.view == "new-scan" and ss.turns:
    session_page()
elif ss.view == "new-scan":
    welcome_page()
elif ss.view == "history":
    history_page()
elif ss.view == "about":
    about_page()
else:
    settings_page()
if ss.camera_open:
    camera_dialog()

count = len(ss.history)
if count:
    ss.dyn_css.append(f'[class*="__nav_history"] button::after{{content:"{count}"}}')
st.html(f"<style>{''.join(ss.dyn_css)}</style>")
scripts()
finish_pending()
