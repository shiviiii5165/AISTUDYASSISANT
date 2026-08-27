"""
Design Template 1 — Academic Clean
===================================
University lecture and classroom teaching style.
- Light off-white background
- Strong serif heading with clean sans body
- Subtle accent underlines and clear section demarcation
- Generous whitespace and subtle page citations
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from app.services.presentation_engine.tokens import ThemeColors, Typography, CONTENT_WIDTH, MARGIN_LEFT
from app.services.presentation_engine.renderers.base import (
    add_filled_rect, add_text_box, add_bullet_list, add_card, add_image, add_footer, add_speaker_notes
)
from ..diagrams import render_flow_diagram, render_architecture_diagram, render_timeline_diagram, render_comparison_diagram


def render_academic_slide(
    slide: Slide,
    slide_spec: dict,
    theme: ThemeColors,
    slide_number: int,
    total_slides: int,
    deck_title: str = "",
) -> None:
    stype = slide_spec.get("type", "concept")
    title = slide_spec.get("title", "")
    subtitle = slide_spec.get("subtitle", "")
    key_msg = slide_spec.get("key_message", "")
    bullets = slide_spec.get("body_bullets", [])
    example = slide_spec.get("example", "")
    notes = slide_spec.get("speaker_notes", "")
    visual = slide_spec.get("visual") or slide_spec.get("visual_spec") or {}
    source_refs = slide_spec.get("source_refs", [])

    # Set background
    bg_color = theme.dark_bg if stype in ["hero", "qa"] else theme.background
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = bg_color

    if stype == "hero":
        # Academic Hero Slide
        add_filled_rect(slide, Inches(0), Inches(0), Inches(13.333), Inches(0.12), fill_color=theme.primary)
        add_text_box(
            slide, "ACADEMIC LECTURE", Inches(1.5), Inches(2.2), Inches(10.3), Inches(0.4),
            token=Typography.BADGE, color=theme.accent, alignment=PP_ALIGN.CENTER
        )
        add_text_box(
            slide, title or deck_title, Inches(1.2), Inches(2.7), Inches(10.9), Inches(2.2),
            token=Typography.HERO_TITLE, color=theme.text_on_dark, alignment=PP_ALIGN.CENTER, word_wrap=True
        )
        if subtitle or key_msg:
            add_text_box(
                slide, subtitle or key_msg, Inches(2.0), Inches(5.0), Inches(9.3), Inches(0.8),
                token=Typography.HERO_SUBTITLE, color=theme.text_muted, alignment=PP_ALIGN.CENTER, word_wrap=True
            )
        add_speaker_notes(slide, notes)
        return

    # Standard Header Zone
    add_filled_rect(slide, Inches(0), Inches(0), Inches(13.333), Inches(0.06), fill_color=theme.primary)
    
    # Title
    add_text_box(
        slide, title, MARGIN_LEFT, Inches(0.5), CONTENT_WIDTH, Inches(0.9),
        token=Typography.SLIDE_TITLE, color=theme.text, bold=True, word_wrap=True
    )
    
    # Thin academic accent line under title
    add_filled_rect(slide, MARGIN_LEFT, Inches(1.42), Inches(2.2), Inches(0.03), fill_color=theme.primary)

    # Content Zone Partitioning
    content_top = Inches(1.65)
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
        # 2-column split with image on right
        text_w = Inches(6.8)
        img_left = MARGIN_LEFT + text_w + Inches(0.4)
        img_w = CONTENT_WIDTH - text_w - Inches(0.4)

        add_bullet_list(slide, bullets, MARGIN_LEFT, content_top, text_w, content_h, token=Typography.BULLET, text_color=theme.text, accent_color=theme.primary)
        add_image(slide, img_bytes, img_left, content_top, img_w, content_h - Inches(0.3))
    else:
        # Standard Concept / Two Column layout
        if example:
            text_w = Inches(7.2)
            ex_left = MARGIN_LEFT + text_w + Inches(0.4)
            ex_w = CONTENT_WIDTH - text_w - Inches(0.4)

            add_bullet_list(slide, bullets, MARGIN_LEFT, content_top, text_w, content_h, token=Typography.BULLET, text_color=theme.text, accent_color=theme.primary)

            # Example Callout Card on Right
            add_card(slide, ex_left, content_top, ex_w, content_h - Inches(0.3), fill_color=theme.surface_alt, border_color=theme.border)
            add_text_box(slide, "CASE EXAMPLE", ex_left + Inches(0.25), content_top + Inches(0.2), ex_w - Inches(0.5), Inches(0.35), token=Typography.BADGE, color=theme.primary)
            add_text_box(slide, example, ex_left + Inches(0.25), content_top + Inches(0.65), ex_w - Inches(0.5), content_h - Inches(1.1), token=Typography.BODY, color=theme.text, italic=True, word_wrap=True)
        else:
            add_bullet_list(slide, bullets, MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h - Inches(0.4), token=Typography.BULLET, text_color=theme.text, accent_color=theme.primary)

    # Subtle Page Citation
    if source_refs:
        page_nums = [str(r.get("page")) for r in source_refs if r.get("page")]
        if page_nums:
            cite_str = f"Source: Page {', '.join(page_nums)}"
            add_text_box(slide, cite_str, MARGIN_LEFT, Inches(6.8), Inches(4.0), Inches(0.3), token=Typography.FOOTNOTE, color=theme.text_muted)

    add_footer(slide, slide_number, total_slides, theme, section_name=deck_title)
    add_speaker_notes(slide, notes)
