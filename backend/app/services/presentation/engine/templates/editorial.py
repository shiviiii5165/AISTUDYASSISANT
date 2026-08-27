"""
Design Template 4 — Editorial
=============================
Magazine and research-report inspired layout.
- Asymmetrical but controlled composition
- Sophisticated typographic contrast
- Large visual/insight areas
- Premium professional appearance
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from app.services.presentation_engine.tokens import ThemeColors, Typography, CONTENT_WIDTH, MARGIN_LEFT
from app.services.presentation_engine.renderers.base import (
    add_filled_rect, add_text_box, add_bullet_list, add_card, add_image, add_footer, add_speaker_notes
)
from ..diagrams import render_flow_diagram, render_architecture_diagram, render_timeline_diagram, render_comparison_diagram


def render_editorial_slide(
    slide: Slide,
    slide_spec: dict,
    theme: ThemeColors,
    slide_number: int,
    total_slides: int,
    deck_title: str = "",
) -> None:
    stype = slide_spec.get("type", "concept")
    title = slide_spec.get("title", "")
    key_msg = slide_spec.get("key_message", "")
    bullets = slide_spec.get("body_bullets", [])
    example = slide_spec.get("example", "")
    notes = slide_spec.get("speaker_notes", "")
    visual = slide_spec.get("visual") or slide_spec.get("visual_spec") or {}

    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = theme.background

    if stype == "hero":
        add_text_box(slide, "SPECIAL REPORT", MARGIN_LEFT, Inches(1.8), CONTENT_WIDTH, Inches(0.4), token=Typography.BADGE, color=theme.primary)
        add_text_box(slide, title or deck_title, MARGIN_LEFT, Inches(2.3), Inches(9.5), Inches(2.2), token=Typography.HERO_TITLE, color=theme.text, bold=True, word_wrap=True)
        if key_msg:
            add_text_box(slide, key_msg, MARGIN_LEFT, Inches(4.7), Inches(8.5), Inches(1.2), token=Typography.QUOTE, color=theme.text_muted, italic=True, word_wrap=True)
        add_footer(slide, 1, total_slides, theme)
        add_speaker_notes(slide, notes)
        return

    # Asymmetric Header: Title left, key message right
    add_text_box(slide, title, MARGIN_LEFT, Inches(0.6), Inches(7.5), Inches(1.1), token=Typography.SLIDE_TITLE, color=theme.text, bold=True, word_wrap=True)

    if key_msg:
        add_card(slide, Inches(8.8), Inches(0.6), Inches(3.7), Inches(1.1), fill_color=theme.surface_alt, border_color=theme.border)
        add_text_box(slide, key_msg, Inches(8.95), Inches(0.7), Inches(3.4), Inches(0.9), token=Typography.CAPTION, color=theme.primary, italic=True, word_wrap=True)

    content_top = Inches(1.9)
    content_h = Inches(4.8)

    # Check for diagrams
    diagram_spec = visual.get("diagram_spec")
    img_bytes = visual.get("image_bytes")

    if diagram_spec and diagram_spec.get("diagram_type") == "architecture":
        render_architecture_diagram(slide, slide_spec.get("layers", []), MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h, theme)
    elif diagram_spec and diagram_spec.get("diagram_type") == "flow":
        render_flow_diagram(slide, slide_spec.get("steps", []), MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h, theme)
    elif diagram_spec and diagram_spec.get("diagram_type") == "timeline":
        render_timeline_diagram(slide, slide_spec.get("milestones", []), MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h, theme)
    elif diagram_spec and diagram_spec.get("diagram_type") == "comparison":
        render_comparison_diagram(slide, slide_spec.get("columns", []), MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h, theme)
    elif img_bytes:
        img_w = Inches(5.2)
        text_w = CONTENT_WIDTH - img_w - Inches(0.4)
        add_image(slide, img_bytes, MARGIN_LEFT, content_top, img_w, content_h - Inches(0.2))
        add_bullet_list(slide, bullets, MARGIN_LEFT + img_w + Inches(0.4), content_top, text_w, content_h, token=Typography.BULLET, text_color=theme.text, accent_color=theme.primary)
    else:
        add_bullet_list(slide, bullets, MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h, token=Typography.BODY, text_color=theme.text, accent_color=theme.primary)

    add_footer(slide, slide_number, total_slides, theme)
    add_speaker_notes(slide, notes)
