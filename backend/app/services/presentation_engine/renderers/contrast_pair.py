"""
TeachGenie Renderer — Contrast Pair Component
=============================================
Renders two side-by-side contrasting cards:
- Left card: "The Trap" / "Common Misconception" (coral/red border, warning icon)
- Right card: "The Discipline" / "Best Practice" (teal/green border, check badge)
- Calculates maximum height dynamically from content volume so both sides align.
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from .. import SlideContent, ThemeColors
from ..tokens import (
    MARGIN_LEFT, CONTENT_WIDTH, ZONE_TITLE_TOP, ZONE_TITLE_HEIGHT,
    ZONE_CONTENT_TOP, Typography, TypeToken
)
from ..text_fitter import estimate_text_height
from .base import (
    add_filled_rect, add_text_box, add_bullet_list, add_card, add_accent_bar,
    add_footer, add_speaker_notes
)
from .icons import render_bundled_icon

CORAL = RGBColor(225, 29, 72)
TEAL = RGBColor(13, 148, 136)

def render_contrast_pair(
    slide: Slide,
    content: SlideContent,
    theme: ThemeColors,
    **kw
) -> None:
    """Render a contrast pair slide comparing misconceptions with correct principles."""
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
    card_w = (CONTENT_WIDTH - Inches(0.4)) // 2
    left_x = MARGIN_LEFT
    right_x = MARGIN_LEFT + card_w + Inches(0.4)

    # Split bullets or columns into Left (Trap) vs Right (Discipline)
    left_title = "THE TRAP / PITFALL"
    right_title = "THE DISCIPLINE / BEST PRACTICE"
    left_bullets = []
    right_bullets = []

    if content.columns and len(content.columns) >= 2:
        left_col = content.columns[0]
        right_col = content.columns[1]
        if left_col.heading and len(left_col.heading) > 2:
            left_title = left_col.heading.upper()
        if right_col.heading and len(right_col.heading) > 2:
            right_title = right_col.heading.upper()
        left_bullets = left_col.points if left_col.points else ([left_col.heading] if left_col.heading else [])
        right_bullets = right_col.points if right_col.points else ([right_col.heading] if right_col.heading else [])

    if not left_bullets and content.body_bullets:
        if len(content.body_bullets) == 1:
            left_bullets = content.body_bullets
            right_bullets = [content.key_insight] if content.key_insight else ["Follow verified architectural principles."]
        else:
            mid = (len(content.body_bullets) + 1) // 2
            left_bullets = content.body_bullets[:mid]
            right_bullets = content.body_bullets[mid:]

    if not left_bullets:
        left_bullets = ["Common misconception or naive assumption without formal invariants."]
    if not right_bullets:
        right_bullets = [content.key_insight] if content.key_insight else ["Rigorous, structured approach enforcing correct constraints."]

    # Dynamic height calculation
    lh = estimate_text_height("\n".join(left_bullets), Typography.BULLET, card_w - Inches(0.6))
    rh = estimate_text_height("\n".join(right_bullets), Typography.BULLET, card_w - Inches(0.6))
    card_h = max(Inches(3.2), min(max(lh, rh) + Inches(1.5), Inches(5.0)))

    # Left Card (The Trap)
    add_card(slide, left_x, content_top, card_w, card_h,
             fill_color=theme.surface, border_color=CORAL)
    render_bundled_icon(slide, "warning-trap", left_x + Inches(0.3), content_top + Inches(0.2), Inches(0.5), Inches(0.5))
    add_text_box(
        slide, left_title,
        left_x + Inches(0.9), content_top + Inches(0.25),
        card_w - Inches(1.2), Inches(0.4),
        token=Typography.BADGE, color=CORAL
    )
    add_bullet_list(
        slide, left_bullets,
        left_x + Inches(0.3), content_top + Inches(0.85),
        card_w - Inches(0.6), card_h - Inches(1.0),
        token=Typography.BULLET, text_color=theme.text, accent_color=CORAL
    )

    # Right Card (The Discipline)
    add_card(slide, right_x, content_top, card_w, card_h,
             fill_color=theme.surface, border_color=TEAL)
    render_bundled_icon(slide, "check-badge", right_x + Inches(0.3), content_top + Inches(0.2), Inches(0.5), Inches(0.5))
    add_text_box(
        slide, right_title,
        right_x + Inches(0.9), content_top + Inches(0.25),
        card_w - Inches(1.2), Inches(0.4),
        token=Typography.BADGE, color=TEAL
    )
    add_bullet_list(
        slide, right_bullets,
        right_x + Inches(0.3), content_top + Inches(0.85),
        card_w - Inches(0.6), card_h - Inches(1.0),
        token=Typography.BULLET, text_color=theme.text, accent_color=TEAL
    )

    add_footer(slide, kw.get("slide_number", 1), kw.get("total_slides", 1), theme, section_name=kw.get("deck_title", ""))
    add_speaker_notes(slide, content.speaker_note)
