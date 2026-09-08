"""
TeachGenie Renderer — Concept Split Component
===============================================
Split-screen concept layout modeled on the Gamma reference:
  - One side (~40-45% width): themed image from stock-photo pipeline
  - Other side: heading, 1-2 sentence definition with key term bolded,
    then 2 short icon-led sub-points underneath

Falls back cleanly to plain_concept if no image is available (never forces
a weak image just to fill the split).
"""
from pptx.slide import Slide
from pptx.util import Inches
from pptx.enum.text import PP_ALIGN
from .. import SlideContent, ThemeColors
from ..tokens import (
    MARGIN_LEFT, CONTENT_WIDTH, ZONE_TITLE_TOP, ZONE_TITLE_HEIGHT,
    ZONE_CONTENT_TOP, Typography, SLIDE_WIDTH, SLIDE_HEIGHT,
)
from .base import (
    add_filled_rect, add_text_box, add_bullet_list, add_accent_bar,
    add_card, add_image, add_footer, add_speaker_notes, add_icon_led_point,
)


def render_concept_split(
    slide: Slide,
    content: SlideContent,
    theme: ThemeColors,
    **kw
) -> None:
    """
    Render a split-screen concept slide.

    If image_bytes is available: image left (~42%), text+definition+sub-points right.
    If no image: falls back to a text-only card layout (never renders an empty image zone).
    """
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

    content_top = ZONE_CONTENT_TOP + Inches(0.1)
    content_h = Inches(4.5)
    has_image = content.image_bytes is not None and len(content.image_bytes) > 100

    if has_image:
        _render_split_with_image(slide, content, theme, content_top, content_h)
    else:
        _render_text_only_fallback(slide, content, theme, content_top, content_h)

    add_footer(slide, kw.get("slide_number", 1), kw.get("total_slides", 1), theme,
               section_name=kw.get("deck_title", ""))
    add_speaker_notes(slide, content.speaker_note)


def _render_split_with_image(
    slide: Slide,
    content: SlideContent,
    theme: ThemeColors,
    content_top,
    content_h,
) -> None:
    """Split layout: image left (~42%), definition + sub-points right (~55%)."""
    # Image zone (left side)
    img_w = Inches(4.8)  # ~42% of content width
    img_h = content_h
    add_image(
        slide, content.image_bytes,
        MARGIN_LEFT, content_top, img_w, img_h,
        corner_radius=Inches(0.12),
    )

    # Text zone (right side)
    text_left = MARGIN_LEFT + img_w + Inches(0.4)
    text_w = CONTENT_WIDTH - img_w - Inches(0.4)
    cursor_y = content_top

    # Definition / key insight (1-2 sentences)
    definition_text = content.key_insight or content.example or ""
    if not definition_text and content.body_bullets:
        definition_text = content.body_bullets[0]

    if definition_text:
        add_text_box(
            slide, definition_text,
            text_left, cursor_y, text_w, Inches(1.2),
            token=Typography.BODY, color=theme.text,
            alignment=PP_ALIGN.LEFT, word_wrap=True,
        )
        cursor_y += Inches(1.3)

    # Sub-points (icon-led, max 2-3)
    sub_points = _extract_sub_points(content)
    for label, desc in sub_points[:3]:
        cursor_y = add_icon_led_point(
            slide, label, desc,
            text_left, cursor_y, text_w,
            theme=theme,
        )


def _render_text_only_fallback(
    slide: Slide,
    content: SlideContent,
    theme: ThemeColors,
    content_top,
    content_h,
) -> None:
    """Fallback when no image: definition card + sub-points underneath."""
    # Definition card
    definition_text = content.key_insight or content.example or ""
    if not definition_text and content.body_bullets:
        definition_text = content.body_bullets[0]

    cursor_y = content_top

    if definition_text:
        card_h = Inches(1.4)
        add_card(slide, MARGIN_LEFT, cursor_y, CONTENT_WIDTH, card_h,
                 fill_color=theme.surface_alt, border_color=theme.border_light)
        add_text_box(
            slide, definition_text,
            MARGIN_LEFT + Inches(0.3), cursor_y + Inches(0.2),
            CONTENT_WIDTH - Inches(0.6), card_h - Inches(0.4),
            token=Typography.BODY, color=theme.text,
            alignment=PP_ALIGN.LEFT, word_wrap=True,
        )
        cursor_y += card_h + Inches(0.3)

    # Sub-points below
    sub_points = _extract_sub_points(content)
    for label, desc in sub_points[:3]:
        cursor_y = add_icon_led_point(
            slide, label, desc,
            MARGIN_LEFT, cursor_y, CONTENT_WIDTH,
            theme=theme,
        )

    # Remaining bullets if any
    remaining = content.body_bullets[len(sub_points) + 1:] if len(content.body_bullets) > len(sub_points) + 1 else []
    if remaining:
        add_bullet_list(
            slide, remaining,
            MARGIN_LEFT, cursor_y + Inches(0.1), CONTENT_WIDTH, Inches(2.0),
            token=Typography.BULLET, text_color=theme.text, accent_color=theme.primary,
        )


def _extract_sub_points(content: SlideContent) -> list:
    """
    Extract (label, description) pairs for icon-led sub-points.
    Looks for "Label: description" pattern in bullets, skipping the first
    bullet (which is used as the definition).
    """
    points = []
    bullets_to_parse = content.body_bullets[1:] if content.body_bullets else []

    for b in bullets_to_parse[:3]:
        b = b.strip()
        if ":" in b:
            parts = b.split(":", 1)
            points.append((parts[0].strip(), parts[1].strip()))
        elif " — " in b:
            parts = b.split(" — ", 1)
            points.append((parts[0].strip(), parts[1].strip()))
        elif " - " in b:
            parts = b.split(" - ", 1)
            points.append((parts[0].strip(), parts[1].strip()))
        else:
            # Use first 3-4 words as label, rest as description
            words = b.split()
            if len(words) > 4:
                points.append((" ".join(words[:3]), " ".join(words[3:])))
            else:
                points.append((b, ""))

    return points
