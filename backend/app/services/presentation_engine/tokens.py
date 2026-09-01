"""
TeachGenie Presentation Design Engine — Design Tokens
=====================================================
Central source of truth for ALL visual decisions:
  • 6 curated Theme Families
  • Typography scales
  • 12-column grid system
  • Safe margin boundaries
  • Card / shadow / border tokens

NO renderer may use raw hex values or arbitrary geometry.
Everything flows through these tokens.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor


# ═══════════════════════════════════════════════════════════════════════════
# CANVAS
# ═══════════════════════════════════════════════════════════════════════════

SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)

SLIDE_WIDTH_IN = 13.333
SLIDE_HEIGHT_IN = 7.5


# ═══════════════════════════════════════════════════════════════════════════
# SAFE MARGINS — no important content may cross these boundaries
# ═══════════════════════════════════════════════════════════════════════════

MARGIN_LEFT   = Inches(0.8)
MARGIN_RIGHT  = Inches(0.8)
MARGIN_TOP    = Inches(0.6)
MARGIN_BOTTOM = Inches(0.6)

CONTENT_WIDTH  = Inches(SLIDE_WIDTH_IN - 0.8 - 0.8)   # 11.733"
CONTENT_HEIGHT = Inches(SLIDE_HEIGHT_IN - 0.6 - 0.6)   # 6.3"


# ═══════════════════════════════════════════════════════════════════════════
# 12-COLUMN GRID
# ═══════════════════════════════════════════════════════════════════════════

GRID_COLUMNS = 12
GRID_GUTTER = Inches(0.25)
_col_available = (SLIDE_WIDTH_IN - 0.8 - 0.8) - (0.25 * (GRID_COLUMNS - 1))
GRID_COL_WIDTH = Inches(_col_available / GRID_COLUMNS)


def grid_x(col: int) -> Emu:
    """Return the left edge x-position for a 0-indexed column."""
    return MARGIN_LEFT + col * (GRID_COL_WIDTH + GRID_GUTTER)


def grid_width(span: int) -> Emu:
    """Return the width spanning `span` columns (including internal gutters)."""
    return span * GRID_COL_WIDTH + (span - 1) * GRID_GUTTER


# ═══════════════════════════════════════════════════════════════════════════
# ZONE SYSTEM — standard vertical zones for slide layout
# ═══════════════════════════════════════════════════════════════════════════

ZONE_TITLE_TOP    = MARGIN_TOP
ZONE_TITLE_HEIGHT = Inches(0.9)

ZONE_SUBTITLE_TOP = MARGIN_TOP + Inches(0.95)
ZONE_SUBTITLE_HEIGHT = Inches(0.4)

ZONE_CONTENT_TOP  = MARGIN_TOP + Inches(1.5)
ZONE_CONTENT_HEIGHT = Inches(4.5)

ZONE_FOOTER_TOP   = Inches(SLIDE_HEIGHT_IN - 0.55)
ZONE_FOOTER_HEIGHT = Inches(0.35)


# ═══════════════════════════════════════════════════════════════════════════
# TYPOGRAPHY SCALE
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TypeToken:
    font_name: str
    size: Pt
    bold: bool = False
    italic: bool = False
    line_spacing: float = 1.15  # multiplier

class Typography:
    # Cover / Hero
    HERO_TITLE     = TypeToken("Georgia", Pt(44), bold=True, line_spacing=1.1)
    HERO_SUBTITLE  = TypeToken("Calibri", Pt(18), line_spacing=1.2)

    # Slide-level
    SLIDE_TITLE    = TypeToken("Georgia", Pt(32), bold=True, line_spacing=1.1)
    SLIDE_SUBTITLE = TypeToken("Calibri", Pt(13), bold=True, line_spacing=1.2)

    # Body
    BODY           = TypeToken("Calibri", Pt(16), line_spacing=1.35)
    BULLET         = TypeToken("Calibri", Pt(15), line_spacing=1.4)
    BULLET_SMALL   = TypeToken("Calibri", Pt(13), line_spacing=1.3)

    # Emphasis
    KPI_NUMBER     = TypeToken("Georgia", Pt(52), bold=True, line_spacing=1.0)
    KPI_LABEL      = TypeToken("Calibri", Pt(14), line_spacing=1.2)
    QUOTE          = TypeToken("Georgia", Pt(22), italic=True, line_spacing=1.4)

    # Metadata
    CAPTION        = TypeToken("Calibri", Pt(11), line_spacing=1.2)
    FOOTNOTE       = TypeToken("Calibri", Pt(10), italic=True, line_spacing=1.2)
    BADGE          = TypeToken("Calibri", Pt(10), bold=True, line_spacing=1.0)
    CATEGORY_PILL  = TypeToken("Calibri", Pt(11), bold=True, line_spacing=1.0)


# ═══════════════════════════════════════════════════════════════════════════
# COLOR ROLES — every theme maps these semantic roles
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ThemeColors:
    """Semantic color roles for a presentation theme."""
    name: str

    # Surfaces
    background:    RGBColor   # main slide bg (usually light)
    surface:       RGBColor   # cards, elevated containers
    surface_alt:   RGBColor   # alternate surface (section bg, callout tint)

    # Brand / Accent
    primary:       RGBColor   # primary accent (titles, headers, bars)
    primary_light: RGBColor   # lighter tint of primary (pill bg, tint fills)
    secondary:     RGBColor   # secondary accent (sparingly)
    accent:        RGBColor   # emphasis accent (badges, highlights)

    # Text
    text:          RGBColor   # primary body text
    text_muted:    RGBColor   # captions, footnotes
    text_on_dark:  RGBColor   # text on dark backgrounds

    # Borders
    border:        RGBColor   # card borders, dividers
    border_light:  RGBColor   # subtle dividers

    # Semantic states
    success:       RGBColor
    warning:       RGBColor
    danger:        RGBColor

    # Dark variant (for cover / closing)
    dark_bg:       RGBColor   # cover slide background
    dark_surface:  RGBColor   # elevated areas on dark bg


# ═══════════════════════════════════════════════════════════════════════════
# 6 CURATED THEME FAMILIES
# ═══════════════════════════════════════════════════════════════════════════

THEMES: Dict[str, ThemeColors] = {

    "blue_professional": ThemeColors(
        name="Blue Professional",
        background=RGBColor(0xF8, 0xFA, 0xFC),
        surface=RGBColor(0xFF, 0xFF, 0xFF),
        surface_alt=RGBColor(0xEF, 0xF6, 0xFF),
        primary=RGBColor(0x1E, 0x40, 0xAF),
        primary_light=RGBColor(0xDB, 0xEA, 0xFE),
        secondary=RGBColor(0x3B, 0x82, 0xF6),
        accent=RGBColor(0x06, 0xB6, 0xD4),
        text=RGBColor(0x0F, 0x17, 0x2A),
        text_muted=RGBColor(0x64, 0x74, 0x8B),
        text_on_dark=RGBColor(0xF1, 0xF5, 0xF9),
        border=RGBColor(0xE2, 0xE8, 0xF0),
        border_light=RGBColor(0xF1, 0xF5, 0xF9),
        success=RGBColor(0x05, 0x96, 0x69),
        warning=RGBColor(0xD9, 0x77, 0x06),
        danger=RGBColor(0xDC, 0x26, 0x26),
        dark_bg=RGBColor(0x0F, 0x17, 0x2A),
        dark_surface=RGBColor(0x1E, 0x29, 0x3B),
    ),

    "indigo_innovation": ThemeColors(
        name="Indigo Innovation",
        background=RGBColor(0xF5, 0xF3, 0xFF),
        surface=RGBColor(0xFF, 0xFF, 0xFF),
        surface_alt=RGBColor(0xED, 0xE9, 0xFE),
        primary=RGBColor(0x4F, 0x46, 0xE5),
        primary_light=RGBColor(0xE0, 0xE7, 0xFF),
        secondary=RGBColor(0x81, 0x8C, 0xF8),
        accent=RGBColor(0xA7, 0x8B, 0xFA),
        text=RGBColor(0x1E, 0x1B, 0x4B),
        text_muted=RGBColor(0x6B, 0x72, 0x80),
        text_on_dark=RGBColor(0xF5, 0xF3, 0xFF),
        border=RGBColor(0xE5, 0xE7, 0xEB),
        border_light=RGBColor(0xF3, 0xF4, 0xF6),
        success=RGBColor(0x05, 0x96, 0x69),
        warning=RGBColor(0xD9, 0x77, 0x06),
        danger=RGBColor(0xDC, 0x26, 0x26),
        dark_bg=RGBColor(0x1E, 0x1B, 0x4B),
        dark_surface=RGBColor(0x31, 0x2E, 0x81),
    ),

    "emerald_academic": ThemeColors(
        name="Emerald Academic",
        background=RGBColor(0xF0, 0xFD, 0xF4),
        surface=RGBColor(0xFF, 0xFF, 0xFF),
        surface_alt=RGBColor(0xDC, 0xFC, 0xE7),
        primary=RGBColor(0x05, 0x96, 0x69),
        primary_light=RGBColor(0xD1, 0xFA, 0xE5),
        secondary=RGBColor(0x10, 0xB9, 0x81),
        accent=RGBColor(0x14, 0xB8, 0xA6),
        text=RGBColor(0x0C, 0x4A, 0x3E),    # deep teal-green
        text_muted=RGBColor(0x6B, 0x72, 0x80),
        text_on_dark=RGBColor(0xEC, 0xFD, 0xF5),
        border=RGBColor(0xD1, 0xD5, 0xDB),
        border_light=RGBColor(0xF3, 0xF4, 0xF6),
        success=RGBColor(0x16, 0xA3, 0x4A),
        warning=RGBColor(0xD9, 0x77, 0x06),
        danger=RGBColor(0xDC, 0x26, 0x26),
        dark_bg=RGBColor(0x06, 0x4E, 0x3B),
        dark_surface=RGBColor(0x06, 0x5F, 0x46),
    ),

    "teal_corporate": ThemeColors(
        name="Teal Corporate",
        background=RGBColor(0xF0, 0xFD, 0xFA),
        surface=RGBColor(0xFF, 0xFF, 0xFF),
        surface_alt=RGBColor(0xCC, 0xFB, 0xF1),
        primary=RGBColor(0x0D, 0x94, 0x88),
        primary_light=RGBColor(0xCC, 0xFB, 0xF1),
        secondary=RGBColor(0x14, 0xB8, 0xA6),
        accent=RGBColor(0x06, 0xB6, 0xD4),
        text=RGBColor(0x0F, 0x17, 0x2A),
        text_muted=RGBColor(0x6B, 0x72, 0x80),
        text_on_dark=RGBColor(0xF0, 0xFD, 0xFA),
        border=RGBColor(0xD1, 0xD5, 0xDB),
        border_light=RGBColor(0xF3, 0xF4, 0xF6),
        success=RGBColor(0x05, 0x96, 0x69),
        warning=RGBColor(0xD9, 0x77, 0x06),
        danger=RGBColor(0xDC, 0x26, 0x26),
        dark_bg=RGBColor(0x0F, 0x24, 0x2E),    # deep dark teal
        dark_surface=RGBColor(0x13, 0x4E, 0x4A),
    ),

    "orange_energy": ThemeColors(
        name="Orange Energy",
        background=RGBColor(0xFF, 0xF7, 0xED),
        surface=RGBColor(0xFF, 0xFF, 0xFF),
        surface_alt=RGBColor(0xFF, 0xED, 0xD5),
        primary=RGBColor(0xC2, 0x41, 0x0C),
        primary_light=RGBColor(0xFF, 0xED, 0xD5),
        secondary=RGBColor(0xEA, 0x58, 0x0C),
        accent=RGBColor(0xF5, 0x9E, 0x0B),
        text=RGBColor(0x1C, 0x15, 0x05),    # warm dark
        text_muted=RGBColor(0x78, 0x71, 0x6C),
        text_on_dark=RGBColor(0xFF, 0xF7, 0xED),
        border=RGBColor(0xE7, 0xE5, 0xE4),
        border_light=RGBColor(0xF5, 0xF5, 0xF4),
        success=RGBColor(0x16, 0xA3, 0x4A),
        warning=RGBColor(0xD9, 0x77, 0x06),
        danger=RGBColor(0xDC, 0x26, 0x26),
        dark_bg=RGBColor(0x1C, 0x15, 0x05),
        dark_surface=RGBColor(0x44, 0x20, 0x3C),    # warm dark
    ),

    "minimal_charcoal": ThemeColors(
        name="Minimal Charcoal",
        background=RGBColor(0xFA, 0xFA, 0xFA),
        surface=RGBColor(0xFF, 0xFF, 0xFF),
        surface_alt=RGBColor(0xF4, 0xF4, 0xF5),
        primary=RGBColor(0x18, 0x18, 0x1B),
        primary_light=RGBColor(0xE4, 0xE4, 0xE7),
        secondary=RGBColor(0x52, 0x52, 0x5B),
        accent=RGBColor(0x3B, 0x82, 0xF6),    # single pop of blue
        text=RGBColor(0x09, 0x09, 0x0B),
        text_muted=RGBColor(0x71, 0x71, 0x7A),
        text_on_dark=RGBColor(0xFA, 0xFA, 0xFA),
        border=RGBColor(0xD4, 0xD4, 0xD8),
        border_light=RGBColor(0xE4, 0xE4, 0xE7),
        success=RGBColor(0x16, 0xA3, 0x4A),
        warning=RGBColor(0xD9, 0x77, 0x06),
        danger=RGBColor(0xEF, 0x44, 0x44),
        dark_bg=RGBColor(0x09, 0x09, 0x0B),
        dark_surface=RGBColor(0x27, 0x27, 0x2A),
    ),
}

DEFAULT_THEME = "blue_professional"


def get_theme(theme_id: str) -> ThemeColors:
    """Get a theme by ID, falling back to Blue Professional."""
    return THEMES.get(theme_id, THEMES[DEFAULT_THEME])


def pick_theme_for_topic(topic: str) -> str:
    """Deterministic semantic theme selection based on topic keywords."""
    t = topic.lower()
    if any(k in t for k in ["startup", "pitch", "marketing", "growth", "brand", "creative", "energy"]):
        return "orange_energy"
    if any(k in t for k in ["ai", "machine learning", "innovation", "future", "quantum", "deep learning", "saas", "tech"]):
        return "indigo_innovation"
    if any(k in t for k in ["health", "medical", "bio", "environment", "sustain", "green", "science", "research"]):
        return "emerald_academic"
    if any(k in t for k in ["enterprise", "corporate", "operations", "supply", "logistics", "management"]):
        return "teal_corporate"
    if any(k in t for k in ["law", "history", "philosophy", "executive", "minimal", "leadership"]):
        return "minimal_charcoal"
    return "blue_professional"


# ═══════════════════════════════════════════════════════════════════════════
# CARD TOKENS
# ═══════════════════════════════════════════════════════════════════════════

CARD_CORNER_RADIUS = Inches(0.15)
CARD_PADDING = Inches(0.25)
CARD_SHADOW = False          # restrained — no default shadows
CARD_BORDER_WIDTH = Pt(1)    # subtle 1pt borders only

# ═══════════════════════════════════════════════════════════════════════════
# BULLET GLYPHS
# ═══════════════════════════════════════════════════════════════════════════

BULLET_GLYPH = "▸"
TAKEAWAY_GLYPH = "-"
STEP_GLYPH = "●"  # for process flows
