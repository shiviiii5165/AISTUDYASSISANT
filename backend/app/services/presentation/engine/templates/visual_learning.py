"""
Design Template 5 — Visual Learning
===================================
Visual-first pedagogy for teaching complex scientific & technical concepts.
- Large diagrams & graphics
- Minimal, scannable text
- Concept anchors & summary callouts
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from app.services.presentation_engine.tokens import ThemeColors, Typography, CONTENT_WIDTH, MARGIN_LEFT
from app.services.presentation_engine.renderers.base import (
    add_filled_rect, add_text_box, add_bullet_list, add_card, add_image, add_footer, add_speaker_notes
)
from ..diagrams import render_flow_diagram, render_architecture_diagram, render_timeline_diagram, render_comparison_diagram


def render_visual_learning_slide(
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
        add_text_box(slide, "VISUAL LEARNING MODULE", MARGIN_LEFT, Inches(2.0), CONTENT_WIDTH, Inches(0.4), token=Typography.BADGE, color=theme.primary)
        add_text_box(slide, title or deck_title, MARGIN_LEFT, Inches(2.6), CONTENT_WIDTH, Inches(2.0), token=Typography.HERO_TITLE, color=theme.text, bold=True, word_wrap=True)
        if key_msg:
            add_text_box(slide, key_msg, MARGIN_LEFT, Inches(4.8), Inches(9.0), Inches(1.0), token=Typography.BODY, color=theme.text_muted, word_wrap=True)
        add_footer(slide, 1, total_slides, theme)
        add_speaker_notes(slide, notes)
        return

    # Title header
    add_text_box(slide, title, MARGIN_LEFT, Inches(0.6), CONTENT_WIDTH, Inches(0.9), token=Typography.SLIDE_TITLE, color=theme.text, bold=True, word_wrap=True)

    content_top = Inches(1.6)
    content_h = Inches(5.0)

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
        # Large visual hero taking 60% of width
        img_w = Inches(7.2)
        text_w = CONTENT_WIDTH - img_w - Inches(0.4)
        add_image(slide, img_bytes, MARGIN_LEFT, content_top, img_w, content_h - Inches(0.2))
        add_bullet_list(slide, bullets, MARGIN_LEFT + img_w + Inches(0.4), content_top, text_w, content_h, token=Typography.BULLET, text_color=theme.text, accent_color=theme.primary)
    else:
        # Visual-first layout with 3 horizontal cards or 2 columns
        if len(bullets) >= 3:
            card_w = (CONTENT_WIDTH - Inches(0.4)) / 2
            card_h = (content_h - Inches(0.4)) / 2
            
            for idx, b in enumerate(bullets[:4]):
                row = idx // 2
                col = idx % 2
                c_left = MARGIN_LEFT + col * (card_w + Inches(0.4))
                c_top = content_top + row * (card_h + Inches(0.4))

                add_card(slide, c_left, c_top, card_w, card_h, fill_color=theme.surface, border_color=theme.border)
                add_text_box(slide, f"KEY POINT 0{idx+1}", c_left + Inches(0.2), c_top + Inches(0.15), card_w - Inches(0.4), Inches(0.3), token=Typography.BADGE, color=theme.primary)
                add_text_box(slide, str(b), c_left + Inches(0.2), c_top + Inches(0.45), card_w - Inches(0.4), card_h - Inches(0.6), token=Typography.BODY, color=theme.text, word_wrap=True)
        else:
            add_bullet_list(slide, bullets, MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h, token=Typography.BODY, text_color=theme.text, accent_color=theme.primary)

    add_footer(slide, slide_number, total_slides, theme)
    add_speaker_notes(slide, notes)
