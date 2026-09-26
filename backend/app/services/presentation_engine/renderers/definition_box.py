"""
LearnByGenie Renderer — Definition Box Component
==============================================
Renders an academic definition box:
- Colored header bar ("DEFINITION" or term) + clean definition body text.
- Paired side-by-side or stacked with an Example / Key Takeaway box when present.
- Height calculated dynamically based on content volume (never oversized).
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from .. import SlideContent, ThemeColors
from ..tokens import (
    MARGIN_LEFT, CONTENT_WIDTH, ZONE_TITLE_TOP, ZONE_TITLE_HEIGHT,
    ZONE_CONTENT_TOP, ZONE_CONTENT_HEIGHT, Typography, TypeToken,
    CARD_CORNER_RADIUS, CARD_PADDING, CARD_BORDER_WIDTH
)
from ..text_fitter import estimate_text_height
from .base import (
    add_filled_rect, add_text_box, add_card, add_accent_bar,
    add_footer, add_speaker_notes, add_category_pill
)
from .icons import render_bundled_icon


def render_definition_box(
    slide: Slide,
    content: SlideContent,
    theme: ThemeColors,
    **kw
) -> None:
    """Render a dedicated definition box slide."""
    from ..tokens import SLIDE_WIDTH, SLIDE_HEIGHT
    add_filled_rect(slide, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, theme.background)

    # Accent bar & Title
    add_accent_bar(
        slide, MARGIN_LEFT - Inches(0.15), ZONE_TITLE_TOP + Inches(0.1),
        width=Inches(0.06), height=Inches(0.55),
        color=theme.primary,
    )
    add_text_box(
        slide, content.title,
        MARGIN_LEFT, ZONE_TITLE_TOP,
        CONTENT_WIDTH, ZONE_TITLE_HEIGHT,
        token=Typography.SLIDE_TITLE,
        color=theme.text,
    )

    content_top = ZONE_CONTENT_TOP + Inches(0.1)
    has_example = bool(content.example and len(content.example.strip()) > 5)
    def_text = content.body_text or "\n".join(content.body_bullets) or content.key_insight or ""

    # Estimate needed height
    est_height = estimate_text_height(def_text, Typography.BODY, CONTENT_WIDTH - Inches(1.0))
    box_height = max(Inches(2.0), min(est_height + Inches(1.2), Inches(4.8)))

    if has_example:
        # 2-column layout: Definition Left (7 cols), Example Right (5 cols)
        left_w = Inches(7.2)
        right_w = CONTENT_WIDTH - left_w - Inches(0.4)
        right_left = MARGIN_LEFT + left_w + Inches(0.4)

        # Definition Card (Left)
        add_card(slide, MARGIN_LEFT, content_top, left_w, box_height,
                 fill_color=theme.surface, border_color=theme.primary)
        # Header banner inside card
        add_filled_rect(slide, MARGIN_LEFT, content_top, left_w, Inches(0.45),
                        fill_color=theme.primary, corner_radius=None)
        add_text_box(
            slide, "FORMAL DEFINITION",
            MARGIN_LEFT + Inches(0.3), content_top + Inches(0.08),
            left_w - Inches(0.6), Inches(0.3),
            token=Typography.BADGE, color=theme.text_on_dark
        )
        add_text_box(
            slide, def_text,
            MARGIN_LEFT + Inches(0.3), content_top + Inches(0.65),
            left_w - Inches(0.6), box_height - Inches(0.8),
            token=Typography.BODY, color=theme.text, word_wrap=True
        )

        # Example Card (Right)
        add_card(slide, right_left, content_top, right_w, box_height,
                 fill_color=theme.surface_alt, border_color=theme.border)
        add_text_box(
            slide, "CONCRETE EXAMPLE",
            right_left + Inches(0.3), content_top + Inches(0.18),
            right_w - Inches(0.6), Inches(0.3),
            token=Typography.BADGE, color=theme.accent
        )
        add_text_box(
            slide, content.example,
            right_left + Inches(0.3), content_top + Inches(0.65),
            right_w - Inches(0.6), box_height - Inches(0.8),
            token=Typography.BODY, color=theme.text, italic=True, word_wrap=True
        )
    else:
        # Single full-width definition card
        add_card(slide, MARGIN_LEFT, content_top, CONTENT_WIDTH, box_height,
                 fill_color=theme.surface, border_color=theme.primary)
        add_filled_rect(slide, MARGIN_LEFT, content_top, CONTENT_WIDTH, Inches(0.45),
                        fill_color=theme.primary, corner_radius=None)
        add_text_box(
            slide, "CORE DEFINITION & PRINCIPLE",
            MARGIN_LEFT + Inches(0.3), content_top + Inches(0.08),
            CONTENT_WIDTH - Inches(0.6), Inches(0.3),
            token=Typography.BADGE, color=theme.text_on_dark
        )
        add_text_box(
            slide, def_text,
            MARGIN_LEFT + Inches(0.4), content_top + Inches(0.7),
            CONTENT_WIDTH - Inches(0.8), box_height - Inches(0.9),
            token=Typography.BODY, color=theme.text, word_wrap=True
        )

    # Optional icon placement if definition book icon available
    render_bundled_icon(slide, "definition-book", MARGIN_LEFT + CONTENT_WIDTH - Inches(1.0), ZONE_TITLE_TOP, Inches(0.8), Inches(0.8))

    add_footer(slide, kw.get("slide_number", 1), kw.get("total_slides", 1), theme, section_name=kw.get("deck_title", ""))
    add_speaker_notes(slide, content.speaker_note)
