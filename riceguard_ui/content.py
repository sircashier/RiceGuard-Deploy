"""
RiceGuard wording and settings: classes, treatments, severity labels, mock results and history, About page text,
explanations and follow-up answers. This is the only copy (the React prototype it came from has been removed).
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

CLASSES = ["Bacterial Leaf Blight", "Leaf Blast", "Brown Spot", "Healthy"]
SEVERITIES = ["Mild", "Moderate", "Severe"]

# Descriptions and treatments follow "RiceGuard Severity and Treatment Reference.docx" (Files and Links): management
# lists in section 4 (PhilRice and IRRI sources), lesion descriptions from the validating pathologist (8.3), residue
# plowed under rather than burned (8.2), and no fungicide product or variety names (4.4, 8.1).
# The app shows each treatment sentence as one bullet, so every practice is its own sentence.
CLASS_INFO = {
    "Bacterial Leaf Blight": {
        "kind": "Bacterial",
        "cue": "Yellowing that starts at the leaf tip and runs down the edges.",
        "about": "Bacterial Leaf Blight is caused by bacteria. It usually starts at the leaf tip as water-soaked to "
                 "yellowish stripes that run down the leaf edges, turn yellow to gray, and dry out. It spreads "
                 "through water, wind and rain.",
        "treatment": "Plant resistant varieties; they are the most effective and economical control. "
                     "Use healthy or treated seed. "
                     "Avoid high nitrogen and apply fertilizer at the proper rate. "
                     "Keep seedbeds and fields from flooding: keep about 2 to 3 cm of water, use shallow water in "
                     "nursery beds, and drain the field during severe flooding. "
                     "Use proper plant spacing and avoid injuring plants during transplanting. "
                     "Keep the field clean by removing weeds, ratoons and volunteer seedlings, and destroy infected "
                     "plant residues. "
                     "After harvest, plow under the stubble and straw and let the fallow field dry thoroughly. "
                     "Chemical sprays are not recommended, since copper compounds, antibiotics and other chemicals "
                     "have not proven highly effective against this disease.",
        "tone": "var(--c-blight)",
    },
    "Leaf Blast": {
        "kind": "Fungal",
        "cue": "Spindle-shaped lesions with gray centers.",
        "about": "Leaf Blast is caused by a fungus. It forms spindle-shaped lesions with gray centers and brown "
                 "margins, and it spreads quickly through airborne spores in humid weather.",
        "treatment": "Plant resistant varieties. "
                     "Sow healthy, disease-free seed early, after the rainy season starts. "
                     "Avoid dense planting: use proper plant spacing, and transplant rather than broadcast. "
                     "Avoid excess nitrogen and apply it in small, split doses. "
                     "Keep the field from drying out, since drought stress makes plants more susceptible. "
                     "Apply silicate fertilizer with compost, especially on soils low in silicon. "
                     "Avoid working in the field while the plants are wet. "
                     "Plow under rice stubble and infected residue right after harvest. "
                     "Before heading, check the leaf collars regularly for blast. "
                     "Use fungicide only when needed, as a last option: choose one recommended by your local "
                     "agricultural office or PhilRice and follow the label.",
        "tone": "var(--c-blast)",
    },
    "Brown Spot": {
        "kind": "Fungal",
        "cue": "Circular to oval dark brown spots.",
        "about": "Brown Spot is caused by a fungus. It forms small, circular to oval dark brown spots, often with a "
                 "light gray center, and is often linked to poor soil nutrition, especially low phosphorus and "
                 "potassium.",
        "treatment": "Plant resistant varieties. "
                     "Don't use seed harvested from a paddy infected with Brown Spot. "
                     "Treat seed before planting with a seed-treatment fungicide recommended by your local "
                     "agricultural office or PhilRice. "
                     "Apply balanced nitrogen, phosphorus and potassium, following the Leaf Color Chart (LCC) and "
                     "Minus-One Element Technique (MOET) recommendations. "
                     "Apply calcium silicate and compost. "
                     "Keep good water management and correct other stress in the field. "
                     "Prepare and level the field well before planting. "
                     "Destroy stubble and weeds that carry the fungus.",
        "tone": "var(--c-brownspot)",
    },
    "Healthy": {
        "kind": "No disease",
        "cue": "No visible disease symptoms.",
        "about": "No signs of Bacterial Leaf Blight, Leaf Blast, or Brown Spot were found on this leaf.",
        "treatment": "No disease detected. Continue regular monitoring and good field practices.",
        "tone": "var(--c-healthy)",
    },
}

SEVERITY_INFO = {
    "Mild": {"hint": "Early stage. Monitor closely and act early.", "tone": "var(--sev-mild)"},
    "Moderate": {"hint": "Spreading. Apply the recommended management soon.", "tone": "var(--sev-moderate)"},
    "Severe": {"hint": "Advanced. Prioritize treatment for this area.", "tone": "var(--sev-severe)"},
}

# MOCK detection results for frontend testing — one per class.
MOCK_RESULTS = {
    "Bacterial Leaf Blight": {"disease": "Bacterial Leaf Blight", "confidence": 0.96, "severity": "Severe", "affected_pct": 62.4},
    "Leaf Blast": {"disease": "Leaf Blast", "confidence": 0.92, "severity": "Moderate", "affected_pct": 23.6},
    "Brown Spot": {"disease": "Brown Spot", "confidence": 0.89, "severity": "Mild", "affected_pct": 3.6},
    "Healthy": {"disease": "Healthy", "confidence": 0.97, "severity": None, "affected_pct": 0.0},
}

# MOCK scan history.
MOCK_HISTORY = [
    {"preset": MOCK_RESULTS["Brown Spot"], "name": "field_iba_0412.jpg", "hours_ago": 2, "seed": 11},
    {"preset": MOCK_RESULTS["Healthy"], "name": "leaf_plot3_morning.jpg", "hours_ago": 5, "seed": 23},
    {"preset": MOCK_RESULTS["Leaf Blast"], "name": "IMG_20260921_0931.jpg", "hours_ago": 27, "seed": 37},
    {"preset": MOCK_RESULTS["Bacterial Leaf Blight"], "name": "botolan_row7.png", "hours_ago": 50, "seed": 41},
    {"preset": {**MOCK_RESULTS["Brown Spot"], "confidence": 0.84, "severity": "Moderate", "affected_pct": 21.5},
     "name": "IMG_20260918_1604.jpg", "hours_ago": 96, "seed": 58},
    {"preset": {**MOCK_RESULTS["Leaf Blast"], "confidence": 0.87, "severity": "Mild", "affected_pct": 2.4},
     "name": "sample_leaf_12.webp", "hours_ago": 170, "seed": 63},
]

DEFAULT_SETTINGS = {
    "theme": "system",
    "show_heatmap_by_default": True,
    "heatmap_opacity": 0.5,
    "explanation_language": "English",
    "save_history": True,
    "mock_result": "Random",
    "model": "VGG16",          # used when the trained models are installed; keep equal to model.py DEFAULT_MODEL
}

TITLES = {"new-scan": "New Scan", "history": "Scan History", "about": "About", "settings": "Settings"}

# ---------------------------------------------------------------------------- About page
USING = [
    ("Add a photo",
     f"Drag a {UPLOAD['formats_label']} image (up to {UPLOAD['max_label']}) onto the upload area or click it to "
     "browse. You can also use Take a Photo."),
    ("Analyze it",
     "Check that the leaf is clear and in focus, then select Analyze Image. The result appears below your photo in "
     "the same workspace."),
    ("Review the result",
     "Read the detected condition, confidence, severity, highlighted areas, and treatment guidance, explained below."),
    ("Ask follow-up questions",
     "Use the box at the bottom to ask about the result. Finished scans are saved to Scan History so you can reopen "
     "them."),
]

PHOTO_TIPS = [
    "One rice leaf per photo.",
    "Even, natural lighting, without strong shadows.",
    "The leaf fills most of the frame and is in focus.",
]

# Shown wherever the severity grading is mentioned. The per-disease cut-offs are in riceguard_ui/model.py
# SEVERITY_CUTOFFS (thesis Chapter III, Table 4).
# Both sentences it follows already name the PhilRice and IRRI manuals, so it doesn't repeat them.
SEVERITY_NOTE = "The cut-offs differ by disease. The affected area is estimated from the heatmap, not measured."

PIPELINE = [
    ("Classify the disease",
     "A CNN trained with transfer learning (VGG16 and ResNet50 are compared; the model with the better F1-score is "
     "used) classifies the leaf as Bacterial Leaf Blight, Leaf Blast, Brown Spot, or Healthy."),
    ("Show where it looked",
     "Grad-CAM produces a heatmap of the leaf regions that most influenced the result, so the prediction can be "
     "checked against visible symptoms."),
    ("Estimate severity",
     "The share of leaf area highlighted by the heatmap is mapped to Mild, Moderate, or Severe, following the PhilRice "
     f"Rice Breeding Operations Manual and the IRRI Standard Evaluation System. {SEVERITY_NOTE}"),
    ("Recommend treatment",
     "A language model turns the result into a plain-language explanation and management recommendation sourced "
     "from PhilRice guidelines."),
]

LIMITS = [
    "Results are a decision aid, not a confirmed diagnosis.",
    "Works on static images only; real-time video is not supported.",
    "Detects Bacterial Leaf Blight, Leaf Blast, and Brown Spot only. It cannot identify pests or nutrient deficiencies.",
    "Uses the image alone. Soil, weather, irrigation, and humidity are not considered.",
    "Needs a close-up of one leaf. Wide shots of the whole plant are not read reliably.",
]

# "Reading your results": (term, explanation). The severity legend is added after the Severity entry.
READING = [
    ("Detection result", "The condition RiceGuard finds on the leaf. Each photo gets one result."),
    ("Confidence",
     "How sure the model is about that result, from 0 to 100%. A low value can mean the photo is unclear or the "
     "symptoms are ambiguous, so try a clearer photo. Open Scores for all classes to see how the other conditions "
     "compared."),
    ("Severity",
     "How much of the leaf area shows symptoms, graded on the PhilRice Rice Breeding Operations Manual and the IRRI "
     f"Standard Evaluation System. It is only estimated when a disease is found. {SEVERITY_NOTE}"),
    ("Highlighted areas",
     "A Grad-CAM heatmap over your photo. Warmer colors mark the parts of the leaf that most influenced the result. "
     "They should sit on visible symptoms; if they fall on the background, retake the photo."),
    ("Treatment guidance",
     "General management steps based on Philippine agricultural guidelines (PhilRice). Treat them as a starting "
     "point, not a prescription: they don't account for your soil, weather, or irrigation. Before applying chemicals "
     "or for serious outbreaks, check with your local agricultural office."),
]


# ---------------------------------------------------------------------------- Explanations
def explain(disease: str, severity, affected_pct: float, lang: str = "English") -> str:
    pct = int(affected_pct + 0.5)
    if disease == "Healthy":
        if lang == "Filipino":
            return "Walang nakitang palatandaan ng Bacterial Leaf Blight, Leaf Blast, o Brown Spot sa dahong ito."
        return f"{CLASS_INFO['Healthy']['about']} Keep monitoring the field, since early symptoms can be small."
    if lang == "Filipino":
        return (f"May palatandaan ng {disease} ang dahon. Ang mga naka-highlight na bahagi ay sumasaklaw sa "
                f"humigit-kumulang {pct}% ng dahon, kaya {severity} ang antas ng kalubhaan.")
    return (f"{CLASS_INFO[disease]['about']} In this photo, the affected areas cover about {pct}% of the leaf, "
            f"which RiceGuard rates as {severity}.")


# ---------------------------------------------------------------------------- Follow-up
SPREAD = {
    "Bacterial Leaf Blight": "Bacterial Leaf Blight spreads through water, wind and rain, and plant injuries make infection "
                        "easier, so keep the field from flooding and avoid injuring plants during transplanting.",
    "Leaf Blast": "Leaf Blast spreads through airborne spores, especially in humid weather, so avoid excess nitrogen, "
                  "don't let the field dry out, and avoid working among wet plants.",
    "Brown Spot": "Brown Spot carries over through infected seeds, stubble and weeds, so use clean seed, destroy "
                  "stubble and weeds, and keep soil nutrients balanced, especially phosphorus and potassium.",
}


def mock_answer(question: str, r) -> str:
    """MOCK: a canned reply picked by keyword (replace with the LLM call)."""
    q = question.lower()
    if not r:
        return "Upload a leaf photo and run an analysis first, then ask me about the result."
    if r["disease"] == "Healthy":
        if re.search(r"detect|identify|disease", q):
            return ("RiceGuard can identify Bacterial Leaf Blight, Leaf Blast, and Brown Spot, or tell you a leaf looks "
                    "healthy. It can't detect pests or nutrient deficiencies.")
        if re.search(r"watch|look for|sign|symptom", q):
            return ("Watch for yellowing that starts at the leaf tip and runs down the edges (Bacterial Leaf Blight), "
                    "spindle-shaped lesions with gray centers (Leaf Blast), and circular to oval dark brown spots "
                    "(Brown Spot). Scan the leaf again if you see any of these.")
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
        if r["disease"] == "Bacterial Leaf Blight":
            return ("Fungicides don't work on Bacterial Leaf Blight because it's caused by bacteria. Focus on resistant "
                    "varieties, balanced nitrogen, good drainage, and removing infected plant debris.")
        if r["disease"] == "Brown Spot":
            return ("For Brown Spot, fungicide is recommended as a seed treatment before planting, together with "
                    "balanced fertilization and clean seed. Use only fungicides recommended by your local "
                    "agricultural office or PhilRice, and follow the label.")
        return ("For Leaf Blast, use fungicide only when needed, as a last option after resistant varieties and good "
                "crop management. Use only fungicides recommended by your local agricultural office or PhilRice, and "
                "follow the label.")
    return (f"For this {r['disease']} result, start with the recommended management steps above. Detailed answers "
            "will come from RiceGuard's explanation service once it's connected.")


def suggestions_for(r) -> list:
    """Suggested follow-up prompts, based on what RiceGuard's explanation layer covers."""
    if r["disease"] == "Healthy":
        return ["How do I keep my rice leaves healthy?", "What diseases can RiceGuard detect?",
                "What should I watch for?"]
    sev = r["severity"].lower() if r["severity"] else "this"
    return ["How do I stop it from spreading?", f"What does {sev} severity mean?", "Which varieties are resistant?"]
