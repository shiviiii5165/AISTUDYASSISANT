"""Cover slide renderer — Hero title + branded dark background."""
from pptx.slide import Slide
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from .. import SlideContent, ThemeColors
from ..tokens import (
    SLIDE_WIDTH, SLIDE_HEIGHT, MARGIN_LEFT, MARGIN_TOP,
    CONTENT_WIDTH, Typography, grid_x, grid_width,
)
from .base import add_filled_rect, add_text_box, add_accent_bar


def render_cover(slide: Slide, content: SlideContent, theme: ThemeColors, **kw) -> None:
    """Render a premium hero cover slide with dark branded background."""
    # Full dark background
    add_filled_rect(slide, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, theme.dark_bg)

    # Top accent bar
    add_filled_rect(
        slide, 0, 0, SLIDE_WIDTH, Inches(0.12), theme.primary
    )

    # Category pill area
    add_text_box(
        slide, kw.get("preset_label", "PRESENTATION").upper(),
        MARGIN_LEFT, Inches(1.8), Inches(4), Inches(0.35),
        token=Typography.CATEGORY_PILL,
        color=theme.primary,
        alignment=PP_ALIGN.LEFT,
    )

    # Main title
    add_text_box(
        slide, content.title or kw.get("deck_title", ""),
        MARGIN_LEFT, Inches(2.4), CONTENT_WIDTH, Inches(2.0),
        token=Typography.HERO_TITLE,
        color=theme.text_on_dark,
        alignment=PP_ALIGN.LEFT,
        anchor=MSO_ANCHOR.TOP,
    )

    # Subtitle line
    subtitle = content.subtitle or kw.get("subtitle", "")
    if subtitle:
        add_text_box(
            slide, subtitle,
            MARGIN_LEFT, Inches(4.6), Inches(8), Inches(0.6),
            token=Typography.HERO_SUBTITLE,
            color=theme.text_muted,
            alignment=PP_ALIGN.LEFT,
        )

    # Bottom branding bar
    add_filled_rect(
        slide, 0, SLIDE_HEIGHT - Inches(0.8),
        SLIDE_WIDTH, Inches(0.8), theme.dark_surface
    )
    add_text_box(
        slide, "TeachGenie AI",
        MARGIN_LEFT, SLIDE_HEIGHT - Inches(0.65),
        Inches(3), Inches(0.4),
        token=Typography.CAPTION,
        color=theme.border,
        alignment=PP_ALIGN.LEFT,
    )
    # Date
    import datetime
    add_text_box(
        slide, datetime.date.today().strftime("%B %Y"),
        SLIDE_WIDTH - Inches(3.5), SLIDE_HEIGHT - Inches(0.65),
        Inches(2.5), Inches(0.4),
        token=Typography.CAPTION,
        color=theme.border,
        alignment=PP_ALIGN.RIGHT,
    )

    # Vertical accent bar next to title
    add_accent_bar(
        slide,
        MARGIN_LEFT - Inches(0.2), Inches(2.4),
        width=Inches(0.06), height=Inches(1.8),
        color=theme.primary,
    )
