"""
Design Template 2 — Modern Minimal (Premium Edition)
=====================================================
Clean, spacious, typography-first presentation inspired by Canva & NotebookLM.
- Ample whitespace
- Large, confident typography
- One prominent takeaway card per slide
- Minimalist line accents
- Premium hero with gradient
- Section divider support
- 3-zone layout for image+example slides
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from app.services.presentation_engine.tokens import ThemeColors, Typography, CONTENT_WIDTH, MARGIN_LEFT
from app.services.presentation_engine.renderers.base import (
    add_filled_rect, add_text_box, add_bullet_list, add_card, add_image,
    add_footer, add_speaker_notes, add_kpi_metrics, add_gradient_bar
)
from ..diagrams import render_flow_diagram, render_architecture_diagram, render_timeline_diagram, render_comparison_diagram


def render_minimal_slide(
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
    source_refs = slide_spec.get("source_refs", [])
    metrics = slide_spec.get("metrics", [])

    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = theme.background

    if stype == "hero":
        # Ultra clean hero with subtle gradient accent
        add_gradient_bar(slide, Inches(0), Inches(0), Inches(13.333), Inches(0.06),
                         theme.primary, theme.accent)
        add_text_box(
            slide, title or deck_title, MARGIN_LEFT, Inches(2.2), CONTENT_WIDTH, Inches(2.2),
            token=Typography.HERO_TITLE, color=theme.text, bold=True, word_wrap=True
        )
        if key_msg:
            add_text_box(
                slide, key_msg, MARGIN_LEFT, Inches(4.5), Inches(8.5), Inches(1.2),
                token=Typography.BODY, color=theme.text_muted, word_wrap=True
            )
        # Thin decorative line
        add_filled_rect(slide, MARGIN_LEFT, Inches(6.0), Inches(3.0), Inches(0.03), fill_color=theme.primary)
        add_footer(slide, 1, total_slides, theme)
        add_speaker_notes(slide, notes)
        return

    if stype == "section_divider":
        # Clean centered section title
        add_filled_rect(slide, Inches(5.5), Inches(3.2), Inches(2.3), Inches(0.03), fill_color=theme.primary)
        add_text_box(
            slide, title, Inches(1.5), Inches(2.5), Inches(10.3), Inches(1.8),
            token=Typography.HERO_TITLE, color=theme.text, alignment=PP_ALIGN.CENTER, word_wrap=True
        )
        add_footer(slide, slide_number, total_slides, theme, section_name=deck_title)
        add_speaker_notes(slide, notes)
        return

    # Title area
    add_text_box(
        slide, title, MARGIN_LEFT, Inches(0.8), CONTENT_WIDTH, Inches(1.0),
        token=Typography.SLIDE_TITLE, color=theme.text, bold=True, word_wrap=True
    )

    content_top = Inches(2.0)
    content_h = Inches(4.6)

    from .dispatch import dispatch_pedagogical_component
    if dispatch_pedagogical_component(slide, slide_spec, theme, slide_number, total_slides, deck_title):
        return

    diagram_spec = visual.get("diagram_spec")
    img_bytes = visual.get("image_bytes")

    if stype == "kpi_metrics" and metrics:
        add_kpi_metrics(slide, metrics, MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h, theme)
    elif diagram_spec and diagram_spec.get("diagram_type") == "architecture":
        render_architecture_diagram(slide, slide_spec.get("layers", []), MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h, theme)
    elif diagram_spec and diagram_spec.get("diagram_type") == "flow":
        render_flow_diagram(slide, slide_spec.get("steps", []), MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h, theme)
    elif diagram_spec and diagram_spec.get("diagram_type") == "timeline":
        render_timeline_diagram(slide, slide_spec.get("milestones", []), MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h, theme)
    elif diagram_spec and diagram_spec.get("diagram_type") == "comparison":
        render_comparison_diagram(slide, slide_spec.get("columns", []), MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h, theme)
    elif img_bytes:
        if example and len(example.strip()) > 5:
            # 3-zone: bullets top-left, image right, example bottom-left
            text_w = Inches(6.5)
            bullet_h = content_h * 0.55
            add_bullet_list(slide, bullets, MARGIN_LEFT, content_top, text_w, bullet_h,
                            token=Typography.BODY, text_color=theme.text, accent_color=theme.accent)

            img_left = MARGIN_LEFT + text_w + Inches(0.5)
            img_w = CONTENT_WIDTH - text_w - Inches(0.5)
            add_image(slide, img_bytes, img_left, content_top, img_w, content_h - Inches(0.3),
                      corner_radius=Inches(0.1))

            ex_top = content_top + bullet_h + Inches(0.2)
            ex_h = content_h - bullet_h - Inches(0.2)
            add_card(slide, MARGIN_LEFT, ex_top, text_w, ex_h,
                     fill_color=theme.surface, border_color=theme.border)
            add_text_box(slide, "EXAMPLE", MARGIN_LEFT + Inches(0.2), ex_top + Inches(0.12),
                         text_w - Inches(0.4), Inches(0.28), token=Typography.BADGE, color=theme.accent)
            add_text_box(slide, example, MARGIN_LEFT + Inches(0.2), ex_top + Inches(0.42),
                         text_w - Inches(0.4), ex_h - Inches(0.55),
                         token=Typography.BODY, color=theme.text, italic=True, word_wrap=True)
        else:
            text_w = Inches(6.5)
            img_left = MARGIN_LEFT + text_w + Inches(0.5)
            img_w = CONTENT_WIDTH - text_w - Inches(0.5)
            add_bullet_list(slide, bullets, MARGIN_LEFT, content_top, text_w, content_h,
                            token=Typography.BODY, text_color=theme.text, accent_color=theme.accent)
            add_image(slide, img_bytes, img_left, content_top, img_w, content_h - Inches(0.3),
                      corner_radius=Inches(0.1))
    else:
        # Key Takeaway Card + Clean Bullets
        if key_msg:
            card_h = Inches(1.3)
            add_card(slide, MARGIN_LEFT, content_top, CONTENT_WIDTH, card_h,
                     fill_color=theme.surface, border_color=theme.border)
            add_text_box(slide, "CORE TAKEAWAY", MARGIN_LEFT + Inches(0.3), content_top + Inches(0.18),
                         CONTENT_WIDTH - Inches(0.6), Inches(0.3), token=Typography.BADGE, color=theme.primary)
            add_text_box(slide, key_msg, MARGIN_LEFT + Inches(0.3), content_top + Inches(0.48),
                         CONTENT_WIDTH - Inches(0.6), Inches(0.7), token=Typography.BODY, color=theme.text,
                         bold=True, word_wrap=True)

            bullets_top = content_top + card_h + Inches(0.4)
            add_bullet_list(slide, bullets, MARGIN_LEFT, bullets_top, CONTENT_WIDTH,
                            content_h - card_h - Inches(0.5), token=Typography.BULLET,
                            text_color=theme.text, accent_color=theme.accent)
        else:
            add_bullet_list(slide, bullets, MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h,
                            token=Typography.BODY, text_color=theme.text, accent_color=theme.accent)

    add_footer(slide, slide_number, total_slides, theme)
    add_speaker_notes(slide, notes)
