"""Concept slide renderer — Single idea with bullets + example callout."""
from pptx.slide import Slide
from pptx.util import Inches
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from .. import SlideContent, ThemeColors
from ..tokens import (
    MARGIN_LEFT, CONTENT_WIDTH, ZONE_TITLE_TOP, ZONE_TITLE_HEIGHT,
    ZONE_CONTENT_TOP, ZONE_CONTENT_HEIGHT, Typography, grid_x, grid_width,
)
from .base import (
    add_filled_rect, add_text_box, add_bullet_list, add_accent_bar,
    add_card, add_footer, add_speaker_notes, add_image,
)


def render_concept(slide: Slide, content: SlideContent, theme: ThemeColors, **kw) -> None:
    """Render a concept/definition slide: title + bullets + optional example card."""

    # Light background
    from ..tokens import SLIDE_WIDTH, SLIDE_HEIGHT
    add_filled_rect(slide, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, theme.background)

    # Accent bar beside title
    add_accent_bar(
        slide, MARGIN_LEFT - Inches(0.15), ZONE_TITLE_TOP + Inches(0.1),
        width=Inches(0.06), height=Inches(0.55),
        color=theme.primary,
    )

    # Title
    add_text_box(
        slide, content.title,
        MARGIN_LEFT, ZONE_TITLE_TOP,
        CONTENT_WIDTH, ZONE_TITLE_HEIGHT,
        token=Typography.SLIDE_TITLE,
        color=theme.text,
    )

    has_example = bool(content.example and len(content.example) > 10)
    has_image = content.image_bytes is not None

    if has_image:
        # Layout: 7-col text | 5-col image
        text_width = grid_width(7)
        img_left = grid_x(7) + Inches(0.15)
        img_width = grid_width(5)

        add_bullet_list(
            slide, content.body_bullets,
            MARGIN_LEFT, ZONE_CONTENT_TOP, text_width, Inches(3.5),
            token=Typography.BULLET,
            text_color=theme.text,
            accent_color=theme.primary,
        )

        add_image(
            slide, content.image_bytes,
            img_left, ZONE_CONTENT_TOP,
            img_width, Inches(3.5),
        )

    elif has_example:
        # Layout: bullets on top, example card on bottom
        add_bullet_list(
            slide, content.body_bullets,
            MARGIN_LEFT, ZONE_CONTENT_TOP, CONTENT_WIDTH, Inches(2.5),
            token=Typography.BULLET,
            text_color=theme.text,
            accent_color=theme.primary,
        )

        # Example callout card
        card_top = ZONE_CONTENT_TOP + Inches(2.8)
        card_height = Inches(1.5)
        add_card(
            slide, MARGIN_LEFT, card_top,
            CONTENT_WIDTH, card_height,
            fill_color=theme.surface_alt,
            border_color=theme.border_light,
        )
        add_text_box(
            slide, "Example",
            MARGIN_LEFT + Inches(0.3), card_top + Inches(0.15),
            Inches(2), Inches(0.3),
            token=Typography.BADGE,
            color=theme.primary,
        )
        add_text_box(
            slide, content.example,
            MARGIN_LEFT + Inches(0.3), card_top + Inches(0.45),
            CONTENT_WIDTH - Inches(0.6), Inches(0.9),
            token=Typography.BODY,
            color=theme.text,
        )
    else:
        # Bullets only — full width
        add_bullet_list(
            slide, content.body_bullets,
            MARGIN_LEFT, ZONE_CONTENT_TOP, CONTENT_WIDTH, ZONE_CONTENT_HEIGHT,
            token=Typography.BULLET,
            text_color=theme.text,
            accent_color=theme.primary,
        )

    # Footer + notes
    slide_num = kw.get("slide_number", 0)
    total = kw.get("total_slides", 0)
    add_footer(slide, slide_num, total, theme)
    add_speaker_notes(slide, content.speaker_note)
