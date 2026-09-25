"""
RiceGuard wording and settings, copied from the React UI in web/src
(config/riceguard.ts, data/mockResults.ts, data/mockHistory.ts, pages/About.tsx, services/followUp.ts,
services/analysis.ts explain()). Keep the two in sync if either changes.
"""
import re

APP = {
    "name": "RiceGuard",
    "version": "0.1.0",
    "stage": "UI preview",
    "full_title": "RiceGuard: Explainable Deep Learning for Detection and Severity Classification of Common Leaf "
                  "Diseases in Philippine Rice (Oryza sativa L.) Using CNN with Grad-CAM",
    "authors": ["Joemark Vincent Benico", "Matt Lawrence M. Cablao", "Marcus John Francisco", "Franzys Danille Llagas"],
    "degree": "BS Computer Science thesis",
    "date": "May 2026",
}

# Upload constraints — keep in sync with the backend when it exists.
UPLOAD = {
    "accept": ["image/jpeg", "image/png", "image/webp"],
    "formats_label": "JPG, PNG, WEBP",
    "max_bytes": 200 * 1024 * 1024,
    "max_label": "200 MB",
}

CLASSES = ["Bacterial Blight", "Leaf Blast", "Brown Spot", "Healthy"]
SEVERITIES = ["Mild", "Moderate", "Severe"]

CLASS_INFO = {
    "Bacterial Blight": {
        "kind": "Bacterial",
        "cue": "Yellowing along the leaf margins.",
        "about": "Bacterial Blight is caused by bacteria. It usually starts as water-soaked streaks along the leaf "
                 "edges that turn yellow and then dry out, and it spreads through water and wind-driven rain.",
        "treatment": "Use certified disease-free seeds and resistant varieties. Avoid excess nitrogen; ensure good "
                     "field drainage. Remove infected debris.",
        "tone": "var(--c-blight)",
    },
    "Leaf Blast": {
        "kind": "Fungal",
        "cue": "Grayish lesions on the leaf blade.",
        "about": "Leaf Blast is caused by a fungus. It forms diamond-shaped lesions with gray centers and brown edges, "
                 "and it spreads quickly through airborne spores in humid weather.",
        "treatment": "Apply recommended fungicide at early lesion stage. Avoid drought stress and over-fertilizing "
                     "with nitrogen. Use resistant varieties.",
        "tone": "var(--c-blast)",
    },
    "Brown Spot": {
        "kind": "Fungal",
        "cue": "Brown lesions scattered across the leaf.",
        "about": "Brown Spot is caused by a fungus. It forms small, round brown spots across the leaf and is often "
                 "linked to poor soil nutrition, especially low potassium.",
        "treatment": "Correct soil nutrient deficiency (especially potassium). Treat seeds and apply fungicide if "
                     "severe. Improve water management.",
        "tone": "var(--c-brownspot)",
    },
    "Healthy": {
        "kind": "No disease",
        "cue": "No visible disease symptoms.",
        "about": "No signs of Bacterial Blight, Leaf Blast, or Brown Spot were found on this leaf.",
        "treatment": "No disease detected. Continue regular monitoring and good field practices.",
        "tone": "var(--c-healthy)",
    },
}

SEVERITY_INFO = {
    "Mild": {"hint": "Early stage. Monitor closely and act early.", "tone": "var(--sev-mild)"},
    "Moderate": {"hint": "Spreading. Apply the recommended management soon.", "tone": "var(--sev-moderate)"},
    "Severe": {"hint": "Advanced. Prioritize treatment for this area.", "tone": "var(--sev-severe)"},
}

# MOCK detection results for frontend testing — one per class (web/src/data/mockResults.ts).
MOCK_RESULTS = {
    "Bacterial Blight": {"disease": "Bacterial Blight", "confidence": 0.96, "severity": "Severe", "affected_pct": 41.8},
    "Leaf Blast": {"disease": "Leaf Blast", "confidence": 0.92, "severity": "Moderate", "affected_pct": 23.6},
    "Brown Spot": {"disease": "Brown Spot", "confidence": 0.89, "severity": "Mild", "affected_pct": 8.4},
    "Healthy": {"disease": "Healthy", "confidence": 0.97, "severity": None, "affected_pct": 0.0},
}

# MOCK scan history (web/src/data/mockHistory.ts).
MOCK_HISTORY = [
    {"preset": MOCK_RESULTS["Brown Spot"], "name": "field_iba_0412.jpg", "hours_ago": 2, "seed": 11},
    {"preset": MOCK_RESULTS["Healthy"], "name": "leaf_plot3_morning.jpg", "hours_ago": 5, "seed": 23},
    {"preset": MOCK_RESULTS["Leaf Blast"], "name": "IMG_20260921_0931.jpg", "hours_ago": 27, "seed": 37},
    {"preset": MOCK_RESULTS["Bacterial Blight"], "name": "botolan_row7.png", "hours_ago": 50, "seed": 41},
    {"preset": {**MOCK_RESULTS["Brown Spot"], "confidence": 0.84, "severity": "Moderate", "affected_pct": 21.5},
     "name": "IMG_20260918_1604.jpg", "hours_ago": 96, "seed": 58},
    {"preset": {**MOCK_RESULTS["Leaf Blast"], "confidence": 0.87, "severity": "Mild", "affected_pct": 11.2},
     "name": "sample_leaf_12.webp", "hours_ago": 170, "seed": 63},
]

DEFAULT_SETTINGS = {
    "theme": "system",
    "show_heatmap_by_default": True,
    "heatmap_opacity": 0.5,
    "explanation_language": "English",
    "save_history": True,
    "mock_result": "Random",
}

TITLES = {"new-scan": "New Scan", "history": "Scan History", "about": "About", "settings": "Settings"}

# ---------------------------------------------------------------------------- About page (pages/About.tsx)
STEPS = [
    ("Upload a leaf photo", "Take or upload a clear photo of a single rice leaf."),
    ("Classify the disease",
     "A CNN trained with transfer learning (VGG16 and ResNet50 are compared; the model with the better F1-score is "
     "used) classifies the leaf as Bacterial Blight, Leaf Blast, Brown Spot, or Healthy."),
    ("Show where it looked",
     "Grad-CAM produces a heatmap of the leaf regions that most influenced the result, so the prediction can be "
     "checked against visible symptoms."),
    ("Estimate severity",
     "The share of leaf area highlighted by the heatmap is mapped to Mild, Moderate, or Severe, following the IRRI "
     "Standard Evaluation System."),
    ("Recommend treatment",
     "A language model turns the result into a plain-language explanation and management recommendation sourced "
     "from PhilRice guidelines."),
]

LIMITS = [
    "Works on static images only; real-time video is not supported.",
    "Detects Bacterial Blight, Leaf Blast, and Brown Spot only. It cannot identify pests or nutrient deficiencies.",
    "Uses the image alone. Soil, weather, irrigation, and humidity are not considered.",
    "Trained and tuned for Philippine rice-growing conditions.",
]


# ---------------------------------------------------------------------------- Explanations (services/analysis.ts)
def explain(disease: str, severity, affected_pct: float, lang: str = "English") -> str:
    pct = int(affected_pct + 0.5)
    if disease == "Healthy":
        if lang == "Filipino":
            return "Walang nakitang palatandaan ng Bacterial Blight, Leaf Blast, o Brown Spot sa dahong ito."
        return f"{CLASS_INFO['Healthy']['about']} Keep monitoring the field, since early symptoms can be small."
    if lang == "Filipino":
        return (f"May palatandaan ng {disease} ang dahon. Ang mga naka-highlight na bahagi ay sumasaklaw sa "
                f"humigit-kumulang {pct}% ng dahon, kaya {severity} ang antas ng kalubhaan.")
    return (f"{CLASS_INFO[disease]['about']} In this photo, the affected areas cover about {pct}% of the leaf, "
            f"which RiceGuard rates as {severity}.")


# ---------------------------------------------------------------------------- Follow-up (services/followUp.ts)
SPREAD = {
    "Bacterial Blight": "Bacterial Blight spreads through irrigation water and wind-driven rain, so keep the field "
                        "well drained and avoid working among wet plants.",
    "Leaf Blast": "Leaf Blast spreads through airborne spores, especially in humid weather, so avoid excess nitrogen "
                  "and don't let the field dry out.",
    "Brown Spot": "Brown Spot carries over through infected seeds and crop residue, so use clean seeds and correct "
                  "soil nutrients, especially potassium.",
}


def mock_answer(question: str, r) -> str:
    """MOCK: a canned reply picked by keyword (replace with the LLM call)."""
    q = question.lower()
    if not r:
        return "Upload a leaf photo and run an analysis first, then ask me about the result."
    if r["disease"] == "Healthy":
        if re.search(r"detect|identify|disease", q):
            return ("RiceGuard can identify Bacterial Blight, Leaf Blast, and Brown Spot, or tell you a leaf looks "
                    "healthy. It can't detect pests or nutrient deficiencies.")
        if re.search(r"watch|look for|sign|symptom", q):
            return ("Watch for yellowing along the leaf edges (Bacterial Blight), gray diamond-shaped lesions (Leaf "
                    "Blast), and small brown spots (Brown Spot). Scan the leaf again if you see any of these.")
        return ("Keep the field healthy with certified seeds, balanced fertilizer (avoid excess nitrogen), and good "
                "water management. Check your plants regularly and scan again if you notice spots or yellowing.")
    if re.search(r"spread|stop|prevent|contain", q):
        return ("Follow the recommended management steps above and remove affected plant material when appropriate. "
                + SPREAD[r["disease"]])
    if re.search(r"severity|severe|moderate|mild|mean|serious", q) and r["severity"]:
        return (f"{r['severity']} means the affected areas cover about {int(r['affected_pct'] + 0.5)}% of this leaf. "
                f"{SEVERITY_INFO[r['severity']]['hint']} Check other leaves in the same area to see how far it has "
                "spread.")
    if re.search(r"variet|resistant", q):
        return ("Resistant varieties differ by region and season. Ask your local agricultural office or PhilRice "
                "which varieties are recommended for your area.")
    if re.search(r"fungicide|spray|chemical|pesticide", q):
        if r["disease"] == "Bacterial Blight":
            return ("Fungicides don't work on Bacterial Blight because it's caused by bacteria. Focus on resistant "
                    "varieties, balanced nitrogen, good drainage, and removing infected plant debris.")
        return ("Use only fungicides recommended by your local agricultural office or PhilRice, and follow the label "
                "for dose and timing. Apply early, when lesions first appear.")
    return (f"For this {r['disease']} result, start with the recommended management steps above. Detailed answers "
            "will come from RiceGuard's explanation service once it's connected.")


def suggestions_for(r) -> list:
    """Suggested follow-up prompts, based on what RiceGuard's explanation layer covers."""
    if r["disease"] == "Healthy":
        return ["How do I keep my rice leaves healthy?", "What diseases can RiceGuard detect?",
                "What should I watch for?"]
    sev = r["severity"].lower() if r["severity"] else "this"
    return ["How do I stop it from spreading?", f"What does {sev} severity mean?", "Which varieties are resistant?"]
