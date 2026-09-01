"""Two-column renderer — Asymmetric split for text+visual or text+text."""
from pptx.slide import Slide
from pptx.util import Inches
from pptx.enum.text import PP_ALIGN
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


def render_two_column(slide: Slide, content: SlideContent, theme: ThemeColors, **kw) -> None:
    """Render a two-column layout: 7/5 or 8/4 split."""
    add_filled_rect(slide, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, theme.background)

    # Title with accent bar
    add_accent_bar(
        slide, MARGIN_LEFT - Inches(0.15), ZONE_TITLE_TOP + Inches(0.1),
        width=Inches(0.06), height=Inches(0.55),
        color=theme.primary,
    )
    add_text_box(
        slide, content.title,
        MARGIN_LEFT, ZONE_TITLE_TOP, CONTENT_WIDTH, ZONE_TITLE_HEIGHT,
        token=Typography.SLIDE_TITLE,
        color=theme.text,
    )

    has_image = content.image_bytes is not None
    col_height = Inches(4.2)

    if has_image:
        # 7/5 split: text left, image right
        text_w = grid_width(7)
        img_left = grid_x(7) + Inches(0.2)
        img_w = grid_width(5)

        add_bullet_list(
            slide, content.body_bullets,
            MARGIN_LEFT, ZONE_CONTENT_TOP, text_w, col_height,
            token=Typography.BULLET,
            text_color=theme.text,
            accent_color=theme.primary,
        )
        add_image(slide, content.image_bytes, img_left, ZONE_CONTENT_TOP, img_w, Inches(3.5))

    else:
        # 6/6 split: text left, example/insight card right
        left_w = grid_width(6) - Inches(0.15)
        right_left = grid_x(6) + Inches(0.15)
        right_w = grid_width(6)

        add_bullet_list(
            slide, content.body_bullets,
            MARGIN_LEFT, ZONE_CONTENT_TOP, left_w, col_height,
            token=Typography.BULLET,
            text_color=theme.text,
            accent_color=theme.primary,
        )

        # Right side: example or key insight card
        card_text = content.example or content.key_insight or content.body_text or ""
        if card_text:
            add_card(
                slide, right_left, ZONE_CONTENT_TOP,
                right_w, Inches(3.5),
                fill_color=theme.surface_alt,
                border_color=theme.border_light,
            )
            badge = "💡 Example" if content.example else "🔑 Key Insight"
            add_text_box(
                slide, badge,
                right_left + Inches(0.25), ZONE_CONTENT_TOP + Inches(0.2),
                Inches(2.5), Inches(0.3),
                token=Typography.BADGE, color=theme.primary,
            )
            add_text_box(
                slide, card_text,
                right_left + Inches(0.25), ZONE_CONTENT_TOP + Inches(0.55),
                right_w - Inches(0.5), Inches(2.7),
                token=Typography.BODY, color=theme.text,
            )

    add_footer(slide, kw.get("slide_number", 0), kw.get("total_slides", 0), theme)
    add_speaker_notes(slide, content.speaker_note)
