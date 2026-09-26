"""
Design Template 4 — Editorial (Premium Edition)
=================================================
Magazine and research-report inspired layout.
- Asymmetrical but controlled composition
- Sophisticated typographic contrast
- Large visual/insight areas
- Premium professional appearance
- Section divider support
- 3-zone image+example layout
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from app.services.presentation_engine.tokens import ThemeColors, Typography, CONTENT_WIDTH, MARGIN_LEFT
from app.services.presentation_engine.renderers.base import (
    add_filled_rect, add_text_box, add_bullet_list, add_card, add_image,
    add_footer, add_speaker_notes, add_kpi_metrics, add_gradient_bar
)
from app.services.presentation_engine.renderers.eyebrow_tag import render_eyebrow_tag
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
    metrics = slide_spec.get("metrics", [])

    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = theme.background

    if stype == "hero":
        # Editorial hero — bold magazine style
        add_gradient_bar(slide, Inches(0), Inches(0), Inches(13.333), Inches(0.12),
                         theme.primary, theme.accent)
        add_text_box(slide, "SPECIAL REPORT", MARGIN_LEFT, Inches(1.8), CONTENT_WIDTH, Inches(0.4),
                     token=Typography.BADGE, color=theme.primary)
        add_text_box(slide, title or deck_title, MARGIN_LEFT, Inches(2.3), Inches(9.5), Inches(2.2),
                     token=Typography.HERO_TITLE, color=theme.text, bold=True, word_wrap=True)
        if key_msg:
            add_text_box(slide, key_msg, MARGIN_LEFT, Inches(4.7), Inches(8.5), Inches(1.2),
                         token=Typography.QUOTE, color=theme.text_muted, italic=True, word_wrap=True)
        add_footer(slide, 1, total_slides, theme)
        add_speaker_notes(slide, notes)
        return

    if stype == "section_divider":
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = theme.dark_bg
        add_gradient_bar(slide, Inches(0), Inches(0), Inches(13.333), Inches(0.08),
                         theme.primary, theme.accent)
        add_text_box(slide, title, MARGIN_LEFT, Inches(2.8), Inches(10.0), Inches(1.8),
                     token=Typography.HERO_TITLE, color=theme.text_on_dark,
                     alignment=PP_ALIGN.LEFT, word_wrap=True)
        add_filled_rect(slide, MARGIN_LEFT, Inches(4.7), Inches(3.0), Inches(0.04), fill_color=theme.accent)
        add_footer(slide, slide_number, total_slides, theme, section_name=deck_title)
        add_speaker_notes(slide, notes)
        return

    # Pedagogical Dispatch
    from .dispatch import dispatch_pedagogical_component
    if dispatch_pedagogical_component(slide, slide_spec, theme, slide_number, total_slides, deck_title):
        return

    # Eyebrow tag (section label) above title — when present
    section_label = slide_spec.get("section_label") or ""
    title_top = Inches(0.6)
    if section_label:
        render_eyebrow_tag(slide, section_label, MARGIN_LEFT, Inches(0.35), theme)
        title_top = Inches(0.72)

    # Asymmetric Header: Title left, key message right
    add_text_box(slide, title, MARGIN_LEFT, title_top, Inches(7.5), Inches(1.1),
                 token=Typography.SLIDE_TITLE, color=theme.text, bold=True, word_wrap=True)

    if key_msg:
        add_card(slide, Inches(8.8), Inches(0.6), Inches(3.7), Inches(1.1),
                 fill_color=theme.surface_alt, border_color=theme.border)
        add_text_box(slide, key_msg, Inches(8.95), Inches(0.7), Inches(3.4), Inches(0.9),
                     token=Typography.CAPTION, color=theme.primary, italic=True, word_wrap=True)

    content_top = Inches(1.9)
    content_h = Inches(4.8)

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
            # Editorial 3-zone: image left, bullets+example right
            img_w = Inches(5.2)
            right_w = CONTENT_WIDTH - img_w - Inches(0.4)
            right_left = MARGIN_LEFT + img_w + Inches(0.4)

            add_image(slide, img_bytes, MARGIN_LEFT, content_top, img_w, content_h - Inches(0.2),
                      corner_radius=Inches(0.1))

            bullet_h = content_h * 0.55
            add_bullet_list(slide, bullets, right_left, content_top, right_w, bullet_h,
                            token=Typography.BULLET, text_color=theme.text, accent_color=theme.primary)

            ex_top = content_top + bullet_h + Inches(0.2)
            ex_h = content_h - bullet_h - Inches(0.35)
            card_pad = Inches(0.3)
            add_card(slide, right_left, ex_top, right_w, ex_h,
                     fill_color=theme.surface_alt, border_color=theme.border)
            add_text_box(slide, "EXAMPLE", right_left + card_pad, ex_top + Inches(0.18),
                         right_w - (card_pad * 2), Inches(0.28), token=Typography.BADGE, color=theme.accent)
            add_text_box(slide, example, right_left + card_pad, ex_top + Inches(0.48),
                         right_w - (card_pad * 2), ex_h - Inches(0.65),
                         token=Typography.BODY, color=theme.text, italic=True, word_wrap=True)
        else:
            img_w = Inches(5.2)
            text_w = CONTENT_WIDTH - img_w - Inches(0.4)
            add_image(slide, img_bytes, MARGIN_LEFT, content_top, img_w, content_h - Inches(0.2),
                      corner_radius=Inches(0.1))
            add_bullet_list(slide, bullets, MARGIN_LEFT + img_w + Inches(0.4), content_top, text_w, content_h,
                            token=Typography.BULLET, text_color=theme.text, accent_color=theme.primary)
    else:
        add_bullet_list(slide, bullets, MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h,
                        token=Typography.BODY, text_color=theme.text, accent_color=theme.primary)

    add_footer(slide, slide_number, total_slides, theme)
    add_speaker_notes(slide, notes)
