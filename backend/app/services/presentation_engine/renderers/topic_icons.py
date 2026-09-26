"""
LearnByGenie — Topic-Agnostic Icon Library
==========================================
Provides cross-domain icon resolution for real-world examples that span
beyond the CS-specific icon set. Maps keyword tags to bundled PNG icons
covering ~50 domains: medicine, finance, security, transport, robotics,
education, environment, business, science, communication, law, etc.

Resolution order:
1. Exact alias match → bundled icon
2. Keyword overlap match → highest-scoring bundled icon
3. No match → return None (caller falls back to stock photo)
"""
import os
import re
from typing import Optional, List, Tuple
from pptx.slide import Slide
from pptx.util import Emu

TOPIC_ICONS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "icons", "topic")
)

# ═══════════════════════════════════════════════════════════════════════════
# ICON TAG REGISTRY — maps icon filename to keyword tag sets
# Each icon covers a domain/concept cluster. Keywords are lowercase.
# ═══════════════════════════════════════════════════════════════════════════

TOPIC_ICON_TAGS: dict = {
    # Healthcare & Medicine
    "medical-cross.png": {"medical", "medicine", "health", "healthcare", "hospital", "clinical", "diagnosis", "patient", "doctor"},
    "dna-helix.png": {"dna", "genetics", "gene", "genome", "heredity", "mutation", "crispr", "chromosome", "molecular"},
    "microscope.png": {"microscope", "laboratory", "lab", "research", "specimen", "biology", "cell", "microbiology"},
    "heartbeat.png": {"heart", "cardio", "cardiac", "pulse", "ecg", "vital", "cardiovascular"},
    "pill-capsule.png": {"drug", "pharmaceutical", "medication", "pharmacy", "therapeutic", "treatment", "dosage"},

    # Finance & Business
    "chart-upward.png": {"market", "stock", "growth", "revenue", "profit", "financial", "investment", "roi", "cagr"},
    "coin-stack.png": {"money", "currency", "cost", "pricing", "budget", "economic", "finance", "banking", "wealth"},
    "briefcase.png": {"business", "corporate", "enterprise", "company", "organization", "management", "executive"},
    "handshake.png": {"partnership", "collaboration", "deal", "contract", "agreement", "negotiation", "alliance"},

    # Technology & Computing
    "circuit-board.png": {"hardware", "chip", "processor", "semiconductor", "integrated", "circuit", "electronics"},
    "cloud-server.png": {"cloud", "server", "hosting", "saas", "paas", "iaas", "deployment", "infrastructure"},
    "shield-lock.png": {"security", "cybersecurity", "encryption", "firewall", "authentication", "privacy", "protection"},
    "robot-arm.png": {"robot", "robotics", "automation", "autonomous", "actuator", "manipulator", "industrial"},
    "neural-network.png": {"neural", "deep learning", "artificial intelligence", "ai", "machine learning", "ml", "perceptron"},
    "code-bracket.png": {"code", "programming", "software", "developer", "api", "syntax", "compiler", "ide"},

    # Education
    "graduation-cap.png": {"education", "university", "academic", "student", "learning", "school", "curriculum", "pedagogy"},
    "open-book.png": {"textbook", "reading", "literacy", "library", "publication", "literature", "knowledge"},

    # Environment & Nature
    "leaf-eco.png": {"environment", "ecology", "green", "sustainable", "renewable", "conservation", "climate", "carbon"},
    "solar-panel.png": {"solar", "energy", "renewable", "photovoltaic", "power", "electricity", "wind"},
    "water-drop.png": {"water", "hydro", "ocean", "marine", "aquatic", "irrigation", "rainfall", "precipitation"},
    "globe-earth.png": {"global", "world", "international", "geography", "continent", "planet", "earth"},

    # Transportation
    "car-vehicle.png": {"vehicle", "automobile", "car", "driving", "autonomous driving", "transportation", "traffic"},
    "airplane.png": {"aviation", "aircraft", "flight", "aerospace", "airline", "pilot"},
    "satellite.png": {"satellite", "space", "orbit", "gps", "navigation", "telescope", "cosmos", "astronomy"},

    # Communication
    "signal-tower.png": {"communication", "network", "wireless", "5g", "telecom", "broadcast", "signal", "antenna"},
    "speech-bubble.png": {"language", "nlp", "text", "chat", "conversation", "dialogue", "translation", "speech"},

    # Agriculture & Food
    "wheat-grain.png": {"agriculture", "farming", "crop", "harvest", "grain", "soil", "cultivation"},
    "food-plate.png": {"food", "nutrition", "diet", "cooking", "culinary", "meal", "recipe"},

    # Law & Government
    "scales-justice.png": {"law", "legal", "justice", "court", "regulation", "policy", "compliance", "ethics"},
    "government-building.png": {"government", "political", "parliament", "legislation", "democracy", "governance"},

    # Science
    "atom-model.png": {"atom", "physics", "quantum", "particle", "nuclear", "proton", "electron", "photon"},
    "beaker-chemistry.png": {"chemistry", "chemical", "reaction", "compound", "element", "periodic", "molecule"},
    "telescope.png": {"astronomy", "star", "galaxy", "cosmos", "universe", "celestial", "nebula"},

    # Manufacturing & Industry
    "factory-gear.png": {"manufacturing", "factory", "production", "assembly", "supply chain", "logistics", "industrial"},
    "wrench-tool.png": {"engineering", "mechanical", "tool", "maintenance", "repair", "construction", "blueprint"},

    # Art & Culture
    "palette-brush.png": {"art", "design", "creative", "painting", "visual", "aesthetic", "illustration"},
    "music-note.png": {"music", "audio", "sound", "acoustic", "melody", "rhythm", "instrument"},
    "camera-lens.png": {"photography", "camera", "image", "video", "film", "visual media", "cinema"},

    # Sports & Fitness
    "trophy-cup.png": {"sports", "competition", "athletic", "fitness", "exercise", "champion", "tournament"},

    # Weather & Climate
    "thermometer.png": {"temperature", "climate", "weather", "thermal", "heat", "cold", "warming"},

    # Math & Statistics
    "graph-chart.png": {"statistics", "data", "analytics", "visualization", "chart", "graph", "metric", "regression"},
    "calculator.png": {"mathematics", "calculation", "arithmetic", "algebra", "equation", "formula", "computation"},

    # History
    "hourglass.png": {"history", "historical", "timeline", "era", "century", "ancient", "medieval", "revolution"},
    "scroll-document.png": {"document", "archive", "manuscript", "record", "treaty", "declaration", "constitution"},
}

# Build reverse lookup: keyword -> [(filename, tag_set_size)]
_KEYWORD_INDEX: dict = {}
for _fname, _tags in TOPIC_ICON_TAGS.items():
    for _tag in _tags:
        if _tag not in _KEYWORD_INDEX:
            _KEYWORD_INDEX[_tag] = []
        _KEYWORD_INDEX[_tag].append((_fname, len(_tags)))


def resolve_topic_icon(text: str) -> Optional[str]:
    """
    Resolve the best-matching topic icon for a given text string.
    Returns absolute path to PNG icon, or None if no match found.

    Matching strategy:
    1. Direct keyword match in text → pick icon with most keyword hits
    2. Fall back to None → caller should use stock photo instead
    """
    if not text or not text.strip():
        return None

    text_lower = text.lower()
    text_words = set(re.sub(r"[^\w\s]", "", text_lower).split())

    # Score each icon by keyword overlap
    scores: dict = {}  # filename -> hit count
    for word in text_words:
        if word in _KEYWORD_INDEX:
            for fname, _ in _KEYWORD_INDEX[word]:
                scores[fname] = scores.get(fname, 0) + 1

    # Also check multi-word tags
    for fname, tags in TOPIC_ICON_TAGS.items():
        for tag in tags:
            if " " in tag and tag in text_lower:
                scores[fname] = scores.get(fname, 0) + 2  # bonus for multi-word match

    if not scores:
        return None

    # Pick highest-scoring icon
    best_fname = max(scores, key=scores.get)
    if scores[best_fname] < 1:
        return None

    path = os.path.join(TOPIC_ICONS_DIR, best_fname)
    if os.path.isfile(path):
        return path

    return None


def render_topic_icon(
    slide: Slide,
    text: str,
    left: Emu,
    top: Emu,
    width: Emu,
    height: Emu,
) -> bool:
    """
    Render a topic-specific icon on the slide if one matches the text.
    Returns True if icon was rendered, False if no match (caller should fall back).
    """
    path = resolve_topic_icon(text)
    if not path:
        return False

    try:
        slide.shapes.add_picture(path, left, top, width, height)
        return True
    except Exception as e:
        print(f"[TopicIcons] Warning: Failed to render icon for '{text[:30]}': {e}")
        return False


def get_all_icon_filenames() -> List[str]:
    """Return all registered icon filenames (for batch generation scripts)."""
    return sorted(TOPIC_ICON_TAGS.keys())
