"""
LearnByGenie Renderer — Case Study Block Component
================================================
Renders a 3-tier pedagogical case study block:
1. "The Problem" band across top
2. Two-column "Context & Challenge" vs "Architecture & Response" split
3. "Lesson Learned / Key Principle" callout banner at the bottom
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

def render_case_study_block(
    slide: Slide,
    content: SlideContent,
    theme: ThemeColors,
    **kw
) -> None:
    """Render a 3-tier case study pedagogical structure."""
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

    # Tier 1: Problem statement banner
    p_height = Inches(0.85)
    add_card(slide, MARGIN_LEFT, content_top, CONTENT_WIDTH, p_height,
             fill_color=theme.surface_alt, border_color=theme.border)
    add_text_box(
        slide, "THE PROBLEM / CHALLENGE",
        MARGIN_LEFT + Inches(0.3), content_top + Inches(0.1),
        Inches(3.0), Inches(0.3),
        token=Typography.BADGE, color=theme.accent
    )
    problem_txt = content.key_insight or (content.body_bullets[0] if content.body_bullets else "Production failure under peak load.")
    add_text_box(
        slide, problem_txt,
        MARGIN_LEFT + Inches(3.2), content_top + Inches(0.1),
        CONTENT_WIDTH - Inches(3.5), Inches(0.65),
        token=Typography.BODY, color=theme.text, word_wrap=True
    )

    # Tier 2: Split columns (Context vs Response)
    tier2_top = content_top + p_height + Inches(0.2)
    tier2_h = Inches(2.7)
    split_w = (CONTENT_WIDTH - Inches(0.4)) // 2
    left_x = MARGIN_LEFT
    right_x = MARGIN_LEFT + split_w + Inches(0.4)

    # Left: Context
    add_card(slide, left_x, tier2_top, split_w, tier2_h,
             fill_color=theme.surface, border_color=theme.border)
    add_text_box(
        slide, "SYSTEM CONTEXT",
        left_x + Inches(0.3), tier2_top + Inches(0.15),
        split_w - Inches(0.6), Inches(0.3),
        token=Typography.BADGE, color=theme.primary
    )
    ctx_bullets = content.body_bullets[1:3] if len(content.body_bullets) > 1 else ["Distributed state across microservices.", "High concurrency bottlenecks."]
    from .base import add_bullet_list
    add_bullet_list(
        slide, ctx_bullets,
        left_x + Inches(0.3), tier2_top + Inches(0.55),
        split_w - Inches(0.6), tier2_h - Inches(0.7),
        token=Typography.BULLET, text_color=theme.text, accent_color=theme.primary
    )

    # Right: Response / Solution
    add_card(slide, right_x, tier2_top, split_w, tier2_h,
             fill_color=theme.surface, border_color=theme.border)
    add_text_box(
        slide, "ENGINEERING RESPONSE",
        right_x + Inches(0.3), tier2_top + Inches(0.15),
        split_w - Inches(0.6), Inches(0.3),
        token=Typography.BADGE, color=theme.primary
    )
    resp_bullets = content.body_bullets[3:5] if len(content.body_bullets) > 3 else ["Decoupled writes using asynchronous message queues.", "Implemented exponential backoff with jitter."]
    add_bullet_list(
        slide, resp_bullets,
        right_x + Inches(0.3), tier2_top + Inches(0.55),
        split_w - Inches(0.6), tier2_h - Inches(0.7),
        token=Typography.BULLET, text_color=theme.text, accent_color=theme.primary
    )

    # Tier 3: Lesson Learned / Outcome Banner
    tier3_top = tier2_top + tier2_h + Inches(0.2)
    tier3_h = Inches(0.8)
    add_card(slide, MARGIN_LEFT, tier3_top, CONTENT_WIDTH, tier3_h,
             fill_color=theme.surface, border_color=theme.primary)
    add_text_box(
        slide, "LESSON LEARNED",
        MARGIN_LEFT + Inches(0.3), tier3_top + Inches(0.1),
        Inches(2.5), Inches(0.3),
        token=Typography.BADGE, color=theme.primary
    )
    lesson_txt = content.example or "Asynchronous boundary decoupling prevents cascade failures in distributed architectures."
    add_text_box(
        slide, lesson_txt,
        MARGIN_LEFT + Inches(2.8), tier3_top + Inches(0.1),
        CONTENT_WIDTH - Inches(3.1), Inches(0.6),
        token=Typography.BODY, color=theme.text, italic=True, word_wrap=True
    )

    add_footer(slide, kw.get("slide_number", 1), kw.get("total_slides", 1), theme, section_name=kw.get("deck_title", ""))
    add_speaker_notes(slide, content.speaker_note)
