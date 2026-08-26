"""Image + Insight renderer — Hero visual with insight callout overlay."""
from pptx.slide import Slide
from pptx.util import Inches
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from .. import SlideContent, ThemeColors
from ..tokens import (
    SLIDE_WIDTH, SLIDE_HEIGHT, MARGIN_LEFT, CONTENT_WIDTH,
    ZONE_TITLE_TOP, ZONE_TITLE_HEIGHT, ZONE_CONTENT_TOP,
    Typography, grid_x, grid_width,
)
from .base import (
    add_filled_rect, add_text_box, add_bullet_list, add_accent_bar,
    add_card, add_footer, add_speaker_notes, add_image,
)


def render_image_insight(slide: Slide, content: SlideContent, theme: ThemeColors, **kw) -> None:
    """Render a visual-led slide: large image + insight text."""
    add_filled_rect(slide, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, theme.background)

    has_image = content.image_bytes is not None

    if has_image:
        # 5/7 split: image left, text right
        img_w = grid_width(5)
        text_left = grid_x(5) + Inches(0.3)
        text_w = grid_width(7) - Inches(0.3)

        add_image(slide, content.image_bytes, MARGIN_LEFT, ZONE_TITLE_TOP, img_w, Inches(5.2))

        # Title on right
        add_accent_bar(
            slide, text_left - Inches(0.15), ZONE_TITLE_TOP + Inches(0.1),
            width=Inches(0.06), height=Inches(0.55),
            color=theme.primary,
        )
        add_text_box(
            slide, content.title, text_left, ZONE_TITLE_TOP,
            text_w, ZONE_TITLE_HEIGHT,
            token=Typography.SLIDE_TITLE, color=theme.text,
        )

        # Key insight or body
        body_top = ZONE_CONTENT_TOP
        if content.key_insight:
            add_card(
                slide, text_left, body_top, text_w, Inches(1.2),
                fill_color=theme.primary_light, border_color=theme.border_light,
            )
            add_text_box(
                slide, content.key_insight,
                text_left + Inches(0.2), body_top + Inches(0.15),
                text_w - Inches(0.4), Inches(0.9),
                token=Typography.BODY, color=theme.primary,
            )
            body_top += Inches(1.4)

        # Bullets
        if content.body_bullets:
            add_bullet_list(
                slide, content.body_bullets,
                text_left, body_top, text_w, Inches(2.8),
                token=Typography.BULLET, text_color=theme.text, accent_color=theme.primary,
            )
    else:
        # Fallback: no image — render as concept with insight card
        add_accent_bar(
            slide, MARGIN_LEFT - Inches(0.15), ZONE_TITLE_TOP + Inches(0.1),
            width=Inches(0.06), height=Inches(0.55), color=theme.primary,
        )
        add_text_box(
            slide, content.title, MARGIN_LEFT, ZONE_TITLE_TOP,
            CONTENT_WIDTH, ZONE_TITLE_HEIGHT,
            token=Typography.SLIDE_TITLE, color=theme.text,
        )

        if content.key_insight:
            add_card(
                slide, MARGIN_LEFT, ZONE_CONTENT_TOP,
                CONTENT_WIDTH, Inches(1.4),
                fill_color=theme.primary_light, border_color=theme.border_light,
            )
            add_text_box(
                slide, f"🔑  {content.key_insight}",
                MARGIN_LEFT + Inches(0.3), ZONE_CONTENT_TOP + Inches(0.2),
                CONTENT_WIDTH - Inches(0.6), Inches(1.0),
                token=Typography.BODY, color=theme.primary,
            )
            bullet_top = ZONE_CONTENT_TOP + Inches(1.7)
        else:
            bullet_top = ZONE_CONTENT_TOP

        if content.body_bullets:
            add_bullet_list(
                slide, content.body_bullets,
                MARGIN_LEFT, bullet_top, CONTENT_WIDTH, Inches(3.0),
                token=Typography.BULLET, text_color=theme.text, accent_color=theme.primary,
            )

    add_footer(slide, kw.get("slide_number", 0), kw.get("total_slides", 0), theme)
    add_speaker_notes(slide, content.speaker_note)
