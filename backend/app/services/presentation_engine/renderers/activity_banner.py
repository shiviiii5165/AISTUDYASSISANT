"""
LearnByGenie Renderer — Activity Banner Component
===============================================
Renders an interactive classroom exercise or discussion prompt slide
with bold activity banner, clear task steps, and reflection prompts.
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from .. import SlideContent, ThemeColors
from ..tokens import (
    MARGIN_LEFT, CONTENT_WIDTH, ZONE_TITLE_TOP, ZONE_TITLE_HEIGHT,
    ZONE_CONTENT_TOP, Typography
)
from .base import (
    add_filled_rect, add_text_box, add_card, add_accent_bar,
    add_footer, add_speaker_notes
)
from .icons import render_bundled_icon

def render_activity_banner(
    slide: Slide,
    content: SlideContent,
    theme: ThemeColors,
    **kw
) -> None:
    """Render a dedicated interactive activity slide."""
    from ..tokens import SLIDE_WIDTH, SLIDE_HEIGHT
    add_filled_rect(slide, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, theme.background)

    # Accent bar & Title
    add_accent_bar(
        slide, MARGIN_LEFT - Inches(0.15), ZONE_TITLE_TOP + Inches(0.1),
        width=Inches(0.06), height=Inches(0.55),
        color=theme.accent,
    )
    add_text_box(
        slide, content.title,
        MARGIN_LEFT, ZONE_TITLE_TOP,
        CONTENT_WIDTH, ZONE_TITLE_HEIGHT,
        token=Typography.SLIDE_TITLE,
        color=theme.text,
    )

    content_top = ZONE_CONTENT_TOP + Inches(0.1)

    # Full-width Hero Banner with Activity Theme
    banner_h = Inches(1.3)
    add_card(slide, MARGIN_LEFT, content_top, CONTENT_WIDTH, banner_h,
             fill_color=theme.surface_alt, border_color=theme.accent)

    render_bundled_icon(slide, "activity-icon", MARGIN_LEFT + Inches(0.4), content_top + Inches(0.2), Inches(0.9), Inches(0.9))

    add_text_box(
        slide, "ACTIVE LEARNING EXERCISE",
        MARGIN_LEFT + Inches(1.5), content_top + Inches(0.15),
        CONTENT_WIDTH - Inches(1.8), Inches(0.3),
        token=Typography.BADGE, color=theme.accent
    )
    banner_sub = content.key_insight or "Apply the concept in pairs to solve the scenario below (5-7 minutes)."
    add_text_box(
        slide, banner_sub,
        MARGIN_LEFT + Inches(1.5), content_top + Inches(0.55),
        CONTENT_WIDTH - Inches(1.8), Inches(0.65),
        token=Typography.BODY, color=theme.text, bold=True, word_wrap=True
    )

    # Action Items / Task Card below
    task_top = content_top + banner_h + Inches(0.3)
    task_h = Inches(3.0)
    add_card(slide, MARGIN_LEFT, task_top, CONTENT_WIDTH, task_h,
             fill_color=theme.surface, border_color=theme.border)
    add_text_box(
        slide, "EXERCISE INSTRUCTIONS",
        MARGIN_LEFT + Inches(0.4), task_top + Inches(0.2),
        CONTENT_WIDTH - Inches(0.8), Inches(0.3),
        token=Typography.BADGE, color=theme.primary
    )

    bullets = content.body_bullets or [
        "Identify the primary input variables and state transitions.",
        "Draw the structural trace for an edge-case test vector.",
        "Compare your approach with the neighboring team."
    ]
    from .base import add_bullet_list
    add_bullet_list(
        slide, bullets,
        MARGIN_LEFT + Inches(0.4), task_top + Inches(0.65),
        CONTENT_WIDTH - Inches(0.8), task_h - Inches(0.85),
        token=Typography.BULLET, text_color=theme.text, accent_color=theme.accent
    )

    add_footer(slide, kw.get("slide_number", 1), kw.get("total_slides", 1), theme, section_name=kw.get("deck_title", ""))
    add_speaker_notes(slide, content.speaker_note)
