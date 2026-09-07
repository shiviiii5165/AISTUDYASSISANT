"""
Design Template 3 — Technical Grid (Premium Edition)
=====================================================
Engineered for Computer Science, AI/ML, Cloud Architecture, DBMS, & Engineering.
- 12-column grid structure
- System component callouts & metric pills
- Architecture & flow diagrams
- Precision typography and parameters
- Premium gradient hero
- Section divider support
- 3-zone image+example layout
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from app.services.presentation_engine.tokens import ThemeColors, Typography, CONTENT_WIDTH, MARGIN_LEFT
from app.services.presentation_engine.renderers.base import (
    add_filled_rect, add_text_box, add_bullet_list, add_card, add_image,
    add_footer, add_speaker_notes, add_kpi_metrics, add_gradient_bar,
    add_category_pill
)
from ..diagrams import render_flow_diagram, render_architecture_diagram, render_timeline_diagram, render_comparison_diagram


def render_technical_slide(
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
    metrics = slide_spec.get("metrics", [])
    layers = slide_spec.get("layers", [])
    steps = slide_spec.get("steps", [])

    # Technical dark background for Hero & Closing
    if stype in ["hero", "qa"]:
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = theme.dark_bg
        
        # Gradient accent at top
        add_gradient_bar(slide, Inches(0), Inches(0), Inches(13.333), Inches(0.12),
                         theme.accent, theme.primary)

        add_category_pill(slide, "SYSTEM SPECIFICATION", MARGIN_LEFT, Inches(2.2),
                          bg_color=theme.primary, text_color=theme.text_on_dark,
                          width=Inches(2.5), height=Inches(0.35))
        add_text_box(slide, title or deck_title, MARGIN_LEFT, Inches(2.8), CONTENT_WIDTH, Inches(2.0),
                     token=Typography.HERO_TITLE, color=theme.text_on_dark, bold=True, word_wrap=True)
        if key_msg:
            add_text_box(slide, key_msg, MARGIN_LEFT, Inches(5.0), CONTENT_WIDTH - Inches(2.0), Inches(1.0),
                         token=Typography.BODY, color=theme.secondary, word_wrap=True)

        add_footer(slide, slide_number if stype == "qa" else 1, total_slides, theme)
        add_speaker_notes(slide, notes)
        return

    if stype == "section_divider":
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = theme.dark_bg
        add_gradient_bar(slide, Inches(0), Inches(0), Inches(13.333), Inches(0.08),
                         theme.accent, theme.primary)
        add_category_pill(slide, "MODULE", MARGIN_LEFT, Inches(2.6),
                          bg_color=theme.accent, text_color=theme.dark_bg,
                          width=Inches(1.5), height=Inches(0.32))
        add_text_box(slide, title, MARGIN_LEFT, Inches(3.1), Inches(10.0), Inches(1.8),
                     token=Typography.HERO_TITLE, color=theme.text_on_dark,
                     alignment=PP_ALIGN.LEFT, word_wrap=True)
        add_footer(slide, slide_number, total_slides, theme, section_name=deck_title)
        add_speaker_notes(slide, notes)
        return

    # Standard Light Canvas with Technical Top Border
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = theme.background
    add_gradient_bar(slide, Inches(0), Inches(0), Inches(13.333), Inches(0.06),
                     theme.primary, theme.accent)

    # Category / Tag Pill
    tag_str = stype.replace("_", " ").upper()
    add_category_pill(slide, tag_str, MARGIN_LEFT, Inches(0.45),
                      bg_color=theme.primary_light, text_color=theme.primary,
                      width=Inches(1.8), height=Inches(0.28))

    # Title
    add_text_box(slide, title, MARGIN_LEFT, Inches(0.8), CONTENT_WIDTH, Inches(0.85),
                 token=Typography.SLIDE_TITLE, color=theme.text, bold=True, word_wrap=True)

    content_top = Inches(1.8)
    content_h = Inches(4.8)

    from .dispatch import dispatch_pedagogical_component
    if dispatch_pedagogical_component(slide, slide_spec, theme, slide_number, total_slides, deck_title):
        return

    diagram_spec = visual.get("diagram_spec")
    img_bytes = visual.get("image_bytes")

    if stype == "kpi_metrics" and metrics:
        add_kpi_metrics(slide, metrics, MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h, theme)
    elif layers or (diagram_spec and diagram_spec.get("diagram_type") == "architecture"):
        render_architecture_diagram(slide, layers or diagram_spec.get("layers", []), MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h, theme)
    elif steps or (diagram_spec and diagram_spec.get("diagram_type") == "flow"):
        render_flow_diagram(slide, steps or diagram_spec.get("steps", []), MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h, theme)
    elif diagram_spec and diagram_spec.get("diagram_type") == "timeline":
        render_timeline_diagram(slide, slide_spec.get("milestones", []), MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h, theme)
    elif diagram_spec and diagram_spec.get("diagram_type") == "comparison":
        render_comparison_diagram(slide, slide_spec.get("columns", []), MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h, theme)
    elif img_bytes:
        if example and len(example.strip()) > 5:
            # 3-zone: bullets top-left, image right, spec card bottom-left
            text_w = Inches(6.8)
            bullet_h = content_h * 0.55
            add_bullet_list(slide, bullets, MARGIN_LEFT, content_top, text_w, bullet_h,
                            token=Typography.BULLET, text_color=theme.text, accent_color=theme.primary)

            img_left = MARGIN_LEFT + text_w + Inches(0.4)
            img_w = CONTENT_WIDTH - text_w - Inches(0.4)
            add_image(slide, img_bytes, img_left, content_top, img_w, content_h - Inches(0.3),
                      corner_radius=Inches(0.1))

            ex_top = content_top + bullet_h + Inches(0.2)
            ex_h = content_h - bullet_h - Inches(0.2)
            add_card(slide, MARGIN_LEFT, ex_top, text_w, ex_h,
                     fill_color=theme.surface, border_color=theme.border)
            add_text_box(slide, "SPECIFICATION", MARGIN_LEFT + Inches(0.2), ex_top + Inches(0.12),
                         text_w - Inches(0.4), Inches(0.28), token=Typography.BADGE, color=theme.primary)
            add_text_box(slide, example, MARGIN_LEFT + Inches(0.2), ex_top + Inches(0.42),
                         text_w - Inches(0.4), ex_h - Inches(0.55),
                         token=Typography.BODY, color=theme.text, italic=True, word_wrap=True)
        else:
            text_w = Inches(6.8)
            img_left = MARGIN_LEFT + text_w + Inches(0.4)
            img_w = CONTENT_WIDTH - text_w - Inches(0.4)
            add_bullet_list(slide, bullets, MARGIN_LEFT, content_top, text_w, content_h,
                            token=Typography.BULLET, text_color=theme.text, accent_color=theme.primary)
            add_image(slide, img_bytes, img_left, content_top, img_w, content_h - Inches(0.3),
                      corner_radius=Inches(0.1))
    else:
        # Technical 2-Column Grid with Component Metrics
        col1_w = Inches(7.2)
        col2_left = MARGIN_LEFT + col1_w + Inches(0.4)
        col2_w = CONTENT_WIDTH - col1_w - Inches(0.4)

        add_bullet_list(slide, bullets, MARGIN_LEFT, content_top, col1_w, content_h,
                        token=Typography.BULLET, text_color=theme.text, accent_color=theme.primary)

        # Right-side Technical Callout Card
        add_card(slide, col2_left, content_top, col2_w, content_h - Inches(0.2),
                 fill_color=theme.surface, border_color=theme.border)
        add_text_box(slide, "SPECIFICATION DETAILS", col2_left + Inches(0.2), content_top + Inches(0.2),
                     col2_w - Inches(0.4), Inches(0.3), token=Typography.BADGE, color=theme.primary)
        
        detail_text = example or key_msg or "Core architectural parameter specification and operational guarantees."
        add_text_box(slide, detail_text, col2_left + Inches(0.2), content_top + Inches(0.6),
                     col2_w - Inches(0.4), content_h - Inches(1.0), token=Typography.CAPTION,
                     color=theme.text, word_wrap=True)

    add_footer(slide, slide_number, total_slides, theme, section_name=deck_title)
    add_speaker_notes(slide, notes)
