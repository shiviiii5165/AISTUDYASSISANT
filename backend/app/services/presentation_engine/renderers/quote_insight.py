"""Quote / Insight renderer — Centered key insight with emphasis."""
from pptx.slide import Slide
from pptx.util import Inches
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from .. import SlideContent, ThemeColors
from ..tokens import (
    SLIDE_WIDTH, SLIDE_HEIGHT, MARGIN_LEFT, CONTENT_WIDTH,
    ZONE_TITLE_TOP, Typography,
)
from .base import add_filled_rect, add_text_box, add_footer, add_speaker_notes


def render_quote_insight(slide: Slide, content: SlideContent, theme: ThemeColors, **kw) -> None:
    """Render a quote/key insight slide with centered emphasis."""
    # Slightly tinted background for visual distinction
    add_filled_rect(slide, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, theme.surface_alt)

    # Large quote marks or decorative accent
    add_text_box(
        slide, "❝",
        Inches(1.5), Inches(1.2), Inches(1.5), Inches(1.0),
        token=Typography.HERO_TITLE, color=theme.primary_light,
        alignment=PP_ALIGN.LEFT,
    )

    # Main quote/insight text — centered
    quote_text = content.quote or content.key_insight or content.example or content.title
    add_text_box(
        slide, quote_text,
        Inches(2.0), Inches(2.2), Inches(9.3), Inches(2.5),
        token=Typography.QUOTE, color=theme.text,
        alignment=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
    )

    # Attribution or subtitle
    attribution = content.quote_attribution or content.subtitle or ""
    if attribution:
        add_text_box(
            slide, f"— {attribution}",
            Inches(3.0), Inches(4.8), Inches(7.3), Inches(0.4),
            token=Typography.CAPTION, color=theme.text_muted,
            alignment=PP_ALIGN.CENTER,
        )

    # Bottom accent line
    add_filled_rect(
        slide, Inches(5.5), Inches(5.5), Inches(2.3), Inches(0.04), theme.primary
    )

    add_footer(slide, kw.get("slide_number", 0), kw.get("total_slides", 0), theme)
    add_speaker_notes(slide, content.speaker_note)
