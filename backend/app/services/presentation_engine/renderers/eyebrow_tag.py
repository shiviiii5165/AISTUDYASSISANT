"""
TeachGenie Renderer — Eyebrow Tag Component
=============================================
Renders a small pill-shaped section label (e.g. "TYPE 1", "CHAPTER OVERVIEW",
"TYPE 1 — APPLICATIONS") directly above a slide's title. Modeled on the Gamma
reference pattern where every content slide carries a structural label showing
the audience exactly where this slide sits in the deck's narrative.

Used by ALL five design templates when SlideSpec.section_label is present.
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from typing import Optional

from ..tokens import ThemeColors, Typography
from .base import add_filled_rect, add_text_box


def render_eyebrow_tag(
    slide: Slide,
    section_label: str,
    left: Emu,
    top: Emu,
    theme: ThemeColors,
    *,
    max_width: Emu = Inches(3.5),
    height: Emu = Inches(0.30),
) -> None:
    """
    Render a small eyebrow tag pill above the slide title.

    Parameters
    ----------
    slide : pptx Slide object
    section_label : text to display (e.g. "TYPE 1", "CHAPTER OVERVIEW")
    left : horizontal position (typically MARGIN_LEFT)
    top : vertical position (typically ZONE_TITLE_TOP - Inches(0.35))
    theme : current ThemeColors for consistent styling
    max_width : maximum pill width (auto-sized to text, capped here)
    height : pill height
    """
    if not section_label or not section_label.strip():
        return

    label_text = section_label.strip().upper()

    # Auto-size width based on character count, with padding
    # ~0.12" per character + 0.4" padding, capped at max_width
    char_width = len(label_text) * Inches(0.095)
    padding = Inches(0.45)
    pill_width = min(char_width + padding, max_width)
    # Ensure minimum width for very short labels
    pill_width = max(pill_width, Inches(1.2))

    # Pill background — uses primary_light for soft contrast
    add_filled_rect(
        slide, left, top, pill_width, height,
        fill_color=theme.primary_light,
        corner_radius=Inches(0.15),
    )

    # Label text — small caps, bold, primary color
    add_text_box(
        slide, label_text,
        left, top, pill_width, height,
        token=Typography.BADGE,
        color=theme.primary,
        alignment=PP_ALIGN.CENTER,
        anchor=MSO_ANCHOR.MIDDLE,
        bold=True,
    )
