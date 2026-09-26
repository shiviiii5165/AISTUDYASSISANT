"""
LearnByGenie Renderer — Annotated Tiers Component
=================================================
Renders hierarchical concepts as annotated explanatory diagrams:

- For 3 tiers: Pyramid layout with trapezoids narrowing upward, each tier
  labeled internally with a thin leader-line connecting to external caption.
- For 4+ tiers: Stacked rounded rectangles with left-aligned tier labels
  and right-aligned annotation captions connected by thin leader lines.

Fully deterministic — tier count and shape style derived from input data.
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor
from typing import List, Dict, Any
from .. import SlideContent, ThemeColors
from ..tokens import (
    MARGIN_LEFT, CONTENT_WIDTH, ZONE_TITLE_TOP, ZONE_TITLE_HEIGHT,
    ZONE_CONTENT_TOP, Typography, SLIDE_WIDTH, SLIDE_HEIGHT,
)
from .base import (
    add_filled_rect, add_text_box, add_accent_bar,
    add_footer, add_speaker_notes,
)


def _lerp_color(c1: RGBColor, c2: RGBColor, t: float) -> RGBColor:
    """Linear interpolation between two RGB colors. t=0 -> c1, t=1 -> c2."""
    r = int(c1[0] + (c2[0] - c1[0]) * t)
    g = int(c1[1] + (c2[1] - c1[1]) * t)
    b = int(c1[2] + (c2[2] - c1[2]) * t)
    return RGBColor(r, g, b)


def _extract_tiers(content: SlideContent) -> List[Dict[str, str]]:
    """Extract tier data from content. Looks for tiers, steps, or bullets."""
    tiers = []

    # Check for explicit tiers data (passed via extra_data or columns)
    if content.steps:
        for s in content.steps:
            tiers.append({"name": s.title, "description": s.detail})
    elif content.columns:
        for c in content.columns:
            desc = ", ".join(c.points) if c.points else ""
            tiers.append({"name": c.heading, "description": desc})
    elif content.body_bullets:
        for b in content.body_bullets:
            b = b.strip()
            if ":" in b:
                parts = b.split(":", 1)
                tiers.append({"name": parts[0].strip(), "description": parts[1].strip()})
            elif " — " in b:
                parts = b.split(" — ", 1)
                tiers.append({"name": parts[0].strip(), "description": parts[1].strip()})
            else:
                tiers.append({"name": b, "description": ""})

    return tiers[:6]  # Cap at 6 tiers


def _render_pyramid_variant(
    slide: Slide,
    tiers: List[Dict[str, str]],
    content_top: Emu,
    content_h: Emu,
    theme: ThemeColors,
) -> None:
    """Pyramid layout for 3 tiers — trapezoids narrowing upward."""
    n = len(tiers)
    gutter = Inches(0.1)
    tier_h = (content_h - gutter * (n - 1)) // n

    # Pyramid: widest at bottom, narrowest at top
    max_width = Inches(8.0)
    min_width = Inches(3.0)
    diagram_center_x = MARGIN_LEFT + CONTENT_WIDTH // 2

    for i in range(n):
        # i=0 is top (narrowest), i=n-1 is bottom (widest)
        rev_i = n - 1 - i
        t = rev_i / max(n - 1, 1)
        tier_w = int(min_width + (max_width - min_width) * t)
        tier_left = diagram_center_x - tier_w // 2
        tier_top = content_top + i * (tier_h + gutter)

        # Fill color: gradient from accent (top) to primary (bottom)
        fill = _lerp_color(theme.accent, theme.primary, i / max(n - 1, 1))

        add_filled_rect(
            slide, tier_left, tier_top, tier_w, tier_h,
            fill_color=fill,
            corner_radius=Inches(0.08),
        )

        # Internal tier label (centered, white text)
        tier_name = tiers[i].get("name", f"Tier {i+1}")
        add_text_box(
            slide, tier_name,
            tier_left, tier_top, tier_w, tier_h,
            token=Typography.CARD_TITLE, color=theme.text_on_dark,
            alignment=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
            bold=True,
        )

        # External annotation caption (right side, connected by leader line)
        desc = tiers[i].get("description", "")
        if desc:
            ann_left = diagram_center_x + max_width // 2 + Inches(0.4)
            ann_w = MARGIN_LEFT + CONTENT_WIDTH - ann_left
            if ann_w > Inches(0.5):
                # Thin leader line
                line_y = tier_top + tier_h // 2
                line_start_x = tier_left + tier_w
                line_end_x = ann_left - Inches(0.05)
                add_filled_rect(
                    slide, line_start_x, line_y,
                    line_end_x - line_start_x, Inches(0.02),
                    fill_color=theme.border,
                )

                # Caption text
                add_text_box(
                    slide, desc,
                    ann_left, tier_top, ann_w, tier_h,
                    token=Typography.BULLET_SMALL, color=theme.text_muted,
                    alignment=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE,
                    word_wrap=True,
                )


def _render_stacked_variant(
    slide: Slide,
    tiers: List[Dict[str, str]],
    content_top: Emu,
    content_h: Emu,
    theme: ThemeColors,
) -> None:
    """Stacked rounded rectangles for 4+ tiers."""
    n = len(tiers)
    gutter = Inches(0.08)
    tier_h = (content_h - gutter * (n - 1)) // n

    # Left column: tier shapes (55% width), Right column: annotations (42%)
    shape_w = int(CONTENT_WIDTH * 0.52)
    ann_left = MARGIN_LEFT + shape_w + Inches(0.35)
    ann_w = CONTENT_WIDTH - shape_w - Inches(0.35)

    for i in range(n):
        tier_top = content_top + i * (tier_h + gutter)
        t = i / max(n - 1, 1)
        fill = _lerp_color(theme.primary, theme.accent, t)

        # Tier shape
        add_filled_rect(
            slide, MARGIN_LEFT, tier_top, shape_w, tier_h,
            fill_color=fill,
            corner_radius=Inches(0.06),
        )

        # Tier label
        tier_name = tiers[i].get("name", f"Tier {i+1}")
        add_text_box(
            slide, tier_name,
            MARGIN_LEFT + Inches(0.2), tier_top, shape_w - Inches(0.4), tier_h,
            token=Typography.CARD_TITLE, color=theme.text_on_dark,
            alignment=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE,
            bold=True,
        )

        # Leader line
        line_y = tier_top + tier_h // 2
        add_filled_rect(
            slide, MARGIN_LEFT + shape_w, line_y,
            Inches(0.3), Inches(0.02),
            fill_color=theme.border,
        )

        # Annotation caption
        desc = tiers[i].get("description", "")
        if desc:
            add_text_box(
                slide, desc,
                ann_left, tier_top, ann_w, tier_h,
                token=Typography.BULLET_SMALL, color=theme.text_muted,
                alignment=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE,
                word_wrap=True,
            )


def render_annotated_tiers(
    slide: Slide,
    content: SlideContent,
    theme: ThemeColors,
    **kw
) -> None:
    """Render a hierarchical annotated tier diagram."""
    add_filled_rect(slide, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, theme.background)

    # Title
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

    tiers = _extract_tiers(content)
    if not tiers:
        tiers = [{"name": "Top", "description": ""}, {"name": "Middle", "description": ""}, {"name": "Base", "description": ""}]

    content_top = ZONE_CONTENT_TOP + Inches(0.15)
    content_h = Inches(4.2)

    if len(tiers) <= 3:
        _render_pyramid_variant(slide, tiers, content_top, content_h, theme)
    else:
        _render_stacked_variant(slide, tiers, content_top, content_h, theme)

    add_footer(slide, kw.get("slide_number", 1), kw.get("total_slides", 1), theme,
               section_name=kw.get("deck_title", ""))
    add_speaker_notes(slide, content.speaker_note)
