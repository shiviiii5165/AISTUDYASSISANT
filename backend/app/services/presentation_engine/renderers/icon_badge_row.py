"""
LearnByGenie Renderer — Icon Badge Row Component
==============================================
Renders a row of 3–6 small badge chips with single letters or short tags.
Crucially, all explanatory captions are placed strictly BENEATH badges
(never crammed inside) eliminating any text overflow.
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from .. import SlideContent, ThemeColors
from ..tokens import (
    MARGIN_LEFT, CONTENT_WIDTH, ZONE_TITLE_TOP, ZONE_TITLE_HEIGHT,
    ZONE_CONTENT_TOP, Typography
)
from .base import (
    add_filled_rect, add_text_box, add_card, add_accent_bar,
    add_footer, add_speaker_notes
)

def render_icon_badge_row(
    slide: Slide,
    content: SlideContent,
    theme: ThemeColors,
    **kw
) -> None:
    """Render a horizontal row of discrete badge chips with clean captions beneath."""
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

    items = []
    if content.body_bullets:
        for i, b in enumerate(content.body_bullets[:5]):
            if ":" in b:
                parts = b.split(":", 1)
                items.append((parts[0].strip(), parts[1].strip()))
            else:
                items.append((f"Item {i+1}", b.strip()))
    else:
        items = [
            ("Atomicity", "All transactions execute completely or abort cleanly."),
            ("Consistency", "State transitions preserve all integrity constraints."),
            ("Isolation", "Concurrent transactions produce serializable schedules."),
            ("Durability", "Committed results survive system restarts and failures.")
        ]

    n = len(items)
    gap = Inches(0.3)
    card_w = (CONTENT_WIDTH - gap * (n - 1)) // n
    content_top = ZONE_CONTENT_TOP + Inches(0.2)
    card_h = Inches(4.0)

    for idx, (label, detail) in enumerate(items):
        cx = MARGIN_LEFT + idx * (card_w + gap)

        # Card container
        add_card(slide, cx, content_top, card_w, card_h,
                 fill_color=theme.surface, border_color=theme.border)

        # Badge Circle at top of card
        badge_r = Inches(0.65)
        badge_x = cx + (card_w - badge_r) // 2
        badge_y = content_top + Inches(0.35)

        chip = slide.shapes.add_shape(MSO_SHAPE.OVAL, badge_x, badge_y, badge_r, badge_r)
        chip.fill.solid()
        chip.fill.fore_color.rgb = theme.primary
        chip.line.fill.background()
        tf = chip.text_frame
        p = tf.paragraphs[0]
        # First letter or short abbreviation
        p.text = label[:2].upper()
        p.font.name = Typography.BADGE.font_name
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = theme.text_on_dark
        p.alignment = PP_ALIGN.CENTER

        # Bold Label Strictly Beneath
        add_text_box(
            slide, label,
            cx + Inches(0.15), badge_y + badge_r + Inches(0.2),
            card_w - Inches(0.3), Inches(0.55),
            token=Typography.CARD_TITLE, color=theme.text, bold=True,
            alignment=PP_ALIGN.CENTER, word_wrap=True
        )

        # Detail Text
        add_text_box(
            slide, detail,
            cx + Inches(0.15), badge_y + badge_r + Inches(0.8),
            card_w - Inches(0.3), card_h - (badge_r + Inches(1.1)),
            token=Typography.BODY, color=theme.text_muted,
            alignment=PP_ALIGN.CENTER, word_wrap=True
        )

    add_footer(slide, kw.get("slide_number", 1), kw.get("total_slides", 1), theme, section_name=kw.get("deck_title", ""))
    add_speaker_notes(slide, content.speaker_note)
