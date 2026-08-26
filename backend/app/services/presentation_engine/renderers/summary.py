"""Summary renderer — Key takeaways with highlighted cards."""
from pptx.slide import Slide
from pptx.util import Inches
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from .. import SlideContent, ThemeColors
from ..tokens import (
    SLIDE_WIDTH, SLIDE_HEIGHT, MARGIN_LEFT, CONTENT_WIDTH,
    ZONE_TITLE_TOP, ZONE_TITLE_HEIGHT, ZONE_CONTENT_TOP,
    Typography, TAKEAWAY_GLYPH,
)
from .base import (
    add_filled_rect, add_text_box, add_accent_bar, add_card,
    add_bullet_list, add_footer, add_speaker_notes,
)


def render_summary(slide: Slide, content: SlideContent, theme: ThemeColors, **kw) -> None:
    """Render a summary/takeaways slide with numbered key points."""
    add_filled_rect(slide, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, theme.background)

    add_accent_bar(
        slide, MARGIN_LEFT - Inches(0.15), ZONE_TITLE_TOP + Inches(0.1),
        width=Inches(0.06), height=Inches(0.55), color=theme.primary,
    )
    add_text_box(
        slide, content.title or "Key Takeaways",
        MARGIN_LEFT, ZONE_TITLE_TOP, CONTENT_WIDTH, ZONE_TITLE_HEIGHT,
        token=Typography.SLIDE_TITLE, color=theme.text,
    )

    takeaways = content.body_bullets or kw.get("key_takeaways", [])
    if not takeaways:
        return

    num = min(len(takeaways), 6)

    # Render as numbered takeaway cards
    card_height = Inches(0.65)
    gap = Inches(0.12)

    for i, tw in enumerate(takeaways[:num]):
        y = ZONE_CONTENT_TOP + i * (card_height + gap)

        # Card background with subtle tint
        bg = theme.surface if i % 2 == 0 else theme.surface_alt
        add_card(
            slide, MARGIN_LEFT, y, CONTENT_WIDTH, card_height,
            fill_color=bg, border_color=theme.border_light,
        )

        # Number badge
        badge_size = Inches(0.38)
        add_filled_rect(
            slide, MARGIN_LEFT + Inches(0.2), y + Inches(0.13),
            badge_size, badge_size, theme.primary,
            corner_radius=Inches(0.19),
        )
        add_text_box(
            slide, str(i + 1),
            MARGIN_LEFT + Inches(0.2), y + Inches(0.13),
            badge_size, badge_size,
            token=Typography.BADGE, color=theme.text_on_dark,
            alignment=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
        )

        # Takeaway text
        add_text_box(
            slide, tw,
            MARGIN_LEFT + Inches(0.75), y + Inches(0.1),
            CONTENT_WIDTH - Inches(1.0), card_height - Inches(0.2),
            token=Typography.BULLET, color=theme.text,
            anchor=MSO_ANCHOR.MIDDLE,
        )

    add_footer(slide, kw.get("slide_number", 0), kw.get("total_slides", 0), theme)
    add_speaker_notes(slide, content.speaker_note)
