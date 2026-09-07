"""
Design Template 1 — Academic Clean (Premium Edition)
=====================================================
University lecture and classroom teaching style.
- Premium gradient hero with decorative accents
- Strong serif heading with clean sans body
- key_message rendered as an italicised thesis line beneath every slide title
- kpi_metrics rendered as large number cards instead of bullets
- 3-zone layout when both image + example are present
- Section divider support
- Generous whitespace and subtle page citations
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from app.services.presentation_engine.tokens import (
    ThemeColors, Typography, CONTENT_WIDTH, MARGIN_LEFT, TypeToken
)
from app.services.presentation_engine.renderers.base import (
    add_filled_rect, add_text_box, add_bullet_list, add_card, add_image,
    add_footer, add_speaker_notes, add_category_pill, add_kpi_metrics,
    add_gradient_bar, add_accent_bar
)
from ..diagrams import (
    render_flow_diagram, render_architecture_diagram,
    render_timeline_diagram, render_comparison_diagram
)

# Key-message text token: italic, slightly smaller than body
_KM_TOKEN = TypeToken("Calibri", Pt(13), bold=False, italic=True, line_spacing=1.2)


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
    metrics = slide_spec.get("metrics", [])

    # Set background
    bg_color = theme.dark_bg if stype in ["hero", "qa"] else theme.background
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = bg_color

    # ═══════════════════════════════════════════════════════════════════════
    # HERO / COVER SLIDE — Premium gradient design
    # ═══════════════════════════════════════════════════════════════════════
    if stype == "hero":
        # Gradient accent strip at top
        add_gradient_bar(slide, Inches(0), Inches(0), Inches(13.333), Inches(0.18),
                         theme.primary, theme.accent)

        # Decorative side accent (vertical bar)
        add_filled_rect(slide, Inches(0.6), Inches(1.8), Inches(0.08), Inches(3.5),
                        fill_color=theme.primary_light)

        # Category badge
        add_category_pill(slide, "ACADEMIC LECTURE", Inches(1.2), Inches(2.0),
                          bg_color=theme.primary, text_color=theme.text_on_dark,
                          width=Inches(2.2), height=Inches(0.35))

        # Title — large, bold, centered
        add_text_box(
            slide, title or deck_title, Inches(1.2), Inches(2.6), Inches(10.9), Inches(2.2),
            token=Typography.HERO_TITLE, color=theme.text_on_dark, alignment=PP_ALIGN.LEFT, word_wrap=True
        )

        # Subtitle / key message
        if subtitle or key_msg:
            add_text_box(
                slide, subtitle or key_msg, Inches(1.2), Inches(4.9), Inches(9.0), Inches(0.9),
                token=Typography.HERO_SUBTITLE, color=theme.text_muted, alignment=PP_ALIGN.LEFT, word_wrap=True
            )

        # Decorative bottom accent line
        add_gradient_bar(slide, Inches(1.2), Inches(6.0), Inches(4.0), Inches(0.04),
                         theme.accent, theme.primary_light)

        add_footer(slide, 1, total_slides, theme)
        add_speaker_notes(slide, notes)
        return

    # ═══════════════════════════════════════════════════════════════════════
    # Q&A / CLOSING SLIDE
    # ═══════════════════════════════════════════════════════════════════════
    if stype == "qa":
        add_gradient_bar(slide, Inches(0), Inches(0), Inches(13.333), Inches(0.18),
                         theme.primary, theme.accent)

        add_text_box(
            slide, "Questions & Discussion", Inches(1.5), Inches(2.0), Inches(10.3), Inches(0.5),
            token=Typography.BADGE, color=theme.accent, alignment=PP_ALIGN.CENTER
        )
        add_text_box(
            slide, title, Inches(1.5), Inches(2.7), Inches(10.3), Inches(1.6),
            token=Typography.HERO_TITLE, color=theme.text_on_dark, alignment=PP_ALIGN.CENTER, word_wrap=True
        )
        if key_msg:
            add_text_box(
                slide, key_msg, Inches(2.0), Inches(4.5), Inches(9.3), Inches(1.2),
                token=Typography.HERO_SUBTITLE, color=theme.text_muted, alignment=PP_ALIGN.CENTER, word_wrap=True
            )
        add_footer(slide, slide_number, total_slides, theme, section_name=deck_title)
        add_speaker_notes(slide, notes)
        return

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION DIVIDER — branded transition slide
    # ═══════════════════════════════════════════════════════════════════════
    if stype == "section_divider":
        # Dark-ish background for contrast
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = theme.dark_bg

        add_gradient_bar(slide, Inches(0), Inches(0), Inches(13.333), Inches(0.12),
                         theme.primary, theme.accent)

        # Large section number or title
        add_text_box(
            slide, title, Inches(1.5), Inches(2.5), Inches(10.3), Inches(2.0),
            token=Typography.HERO_TITLE, color=theme.text_on_dark,
            alignment=PP_ALIGN.CENTER, word_wrap=True
        )
        if subtitle or key_msg:
            add_text_box(
                slide, subtitle or key_msg, Inches(2.5), Inches(4.6), Inches(8.3), Inches(0.8),
                token=Typography.HERO_SUBTITLE, color=theme.text_muted,
                alignment=PP_ALIGN.CENTER, word_wrap=True
            )

        # Decorative accent
        add_filled_rect(slide, Inches(5.5), Inches(4.3), Inches(2.3), Inches(0.04),
                        fill_color=theme.accent)

        add_footer(slide, slide_number, total_slides, theme, section_name=deck_title)
        add_speaker_notes(slide, notes)
        return

    # ═══════════════════════════════════════════════════════════════════════
    # STANDARD CONTENT SLIDE — Header Zone
    # ═══════════════════════════════════════════════════════════════════════
    # Thin gradient accent at top
    add_gradient_bar(slide, Inches(0), Inches(0), Inches(13.333), Inches(0.06),
                     theme.primary, theme.accent)

    # Vertical accent bar next to title
    add_accent_bar(slide, MARGIN_LEFT - Inches(0.15), Inches(0.45),
                   width=Inches(0.06), height=Inches(0.65), color=theme.primary)

    add_text_box(
        slide, title, MARGIN_LEFT, Inches(0.5), CONTENT_WIDTH, Inches(0.9),
        token=Typography.SLIDE_TITLE, color=theme.text, bold=True, word_wrap=True
    )

    # Thin accent underline
    add_filled_rect(slide, MARGIN_LEFT, Inches(1.42), Inches(2.2), Inches(0.03), fill_color=theme.primary)

    # ─── Key Message as thesis subtitle ────────────────────────────────────
    has_key_msg = bool(key_msg and key_msg.strip())
    if has_key_msg:
        add_text_box(
            slide, key_msg, MARGIN_LEFT, Inches(1.52), CONTENT_WIDTH, Inches(0.42),
            token=_KM_TOKEN, color=theme.text_muted, alignment=PP_ALIGN.LEFT, word_wrap=True
        )
        content_top = Inches(2.05)
        content_h = Inches(4.55)
    else:
        content_top = Inches(1.65)
        content_h = Inches(5.00)

    # ═══════════════════════════════════════════════════════════════════════
    # CONTENT ZONE — Pedagogical dispatch first
    # ═══════════════════════════════════════════════════════════════════════
    from .dispatch import dispatch_pedagogical_component
    if dispatch_pedagogical_component(slide, slide_spec, theme, slide_number, total_slides, deck_title):
        return

    diagram_spec = visual.get("diagram_spec")
    img_bytes = visual.get("image_bytes")

    # kpi_metrics: render metric cards instead of bullets
    if stype == "kpi_metrics" and metrics:
        add_kpi_metrics(slide, metrics, MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h, theme)

    elif diagram_spec and diagram_spec.get("diagram_type") == "architecture":
        render_architecture_diagram(
            slide, slide_spec.get("layers", []), MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h, theme)

    elif diagram_spec and diagram_spec.get("diagram_type") == "flow":
        render_flow_diagram(
            slide, slide_spec.get("steps", []), MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h, theme)

    elif diagram_spec and diagram_spec.get("diagram_type") == "timeline":
        render_timeline_diagram(
            slide, slide_spec.get("milestones", []), MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h, theme)

    elif diagram_spec and diagram_spec.get("diagram_type") == "comparison":
        render_comparison_diagram(
            slide, slide_spec.get("columns", []), MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h, theme)

    elif img_bytes:
        # ── 3-Zone Layout when BOTH image + example exist ──
        if example and len(example.strip()) > 5:
            # Zone 1: Bullets top-left (60% width, 55% height)
            text_w = Inches(6.8)
            bullet_h = content_h * 0.55
            add_bullet_list(
                slide, bullets, MARGIN_LEFT, content_top, text_w, bullet_h,
                token=Typography.BULLET, text_color=theme.text, accent_color=theme.primary)

            # Zone 2: Image right (40% width, full height)
            img_left = MARGIN_LEFT + text_w + Inches(0.4)
            img_w = CONTENT_WIDTH - text_w - Inches(0.4)
            add_image(slide, img_bytes, img_left, content_top, img_w, content_h - Inches(0.3),
                      corner_radius=Inches(0.1))

            # Zone 3: Example card bottom-left (60% width, 40% height)
            ex_top = content_top + bullet_h + Inches(0.2)
            ex_h = content_h - bullet_h - Inches(0.2)
            add_card(slide, MARGIN_LEFT, ex_top, text_w, ex_h,
                     fill_color=theme.surface_alt, border_color=theme.border)
            add_text_box(slide, "EXAMPLE", MARGIN_LEFT + Inches(0.2), ex_top + Inches(0.12),
                         text_w - Inches(0.4), Inches(0.28),
                         token=Typography.BADGE, color=theme.primary)
            add_text_box(slide, example,
                         MARGIN_LEFT + Inches(0.2), ex_top + Inches(0.42),
                         text_w - Inches(0.4), ex_h - Inches(0.55),
                         token=Typography.BODY, color=theme.text, italic=True, word_wrap=True)
        else:
            # 2-column: bullets left, image right (with rounded corners)
            text_w = Inches(6.8)
            img_left = MARGIN_LEFT + text_w + Inches(0.4)
            img_w = CONTENT_WIDTH - text_w - Inches(0.4)
            add_bullet_list(
                slide, bullets, MARGIN_LEFT, content_top, text_w, content_h,
                token=Typography.BULLET, text_color=theme.text, accent_color=theme.primary)
            add_image(slide, img_bytes, img_left, content_top, img_w, content_h - Inches(0.3),
                      corner_radius=Inches(0.1))

    else:
        if example:
            text_w = Inches(7.2)
            ex_left = MARGIN_LEFT + text_w + Inches(0.4)
            ex_w = CONTENT_WIDTH - text_w - Inches(0.4)

            add_bullet_list(
                slide, bullets, MARGIN_LEFT, content_top, text_w, content_h,
                token=Typography.BULLET, text_color=theme.text, accent_color=theme.primary)

            add_card(slide, ex_left, content_top, ex_w, content_h - Inches(0.3),
                     fill_color=theme.surface_alt, border_color=theme.border)
            add_text_box(slide, "EXAMPLE", ex_left + Inches(0.2), content_top + Inches(0.15),
                         ex_w - Inches(0.4), Inches(0.32),
                         token=Typography.BADGE, color=theme.primary)
            add_text_box(slide, example,
                         ex_left + Inches(0.2), content_top + Inches(0.55),
                         ex_w - Inches(0.4), content_h - Inches(1.0),
                         token=Typography.BODY, color=theme.text, italic=True, word_wrap=True)
        else:
            add_bullet_list(
                slide, bullets, MARGIN_LEFT, content_top, CONTENT_WIDTH, content_h - Inches(0.3),
                token=Typography.BULLET, text_color=theme.text, accent_color=theme.primary)

    # ─── Source Citations ───────────────────────────────────────────────────
    if source_refs:
        page_nums = [str(r.get("page")) for r in source_refs if r.get("page")]
        if page_nums:
            cite_str = f"Source: Page {', '.join(page_nums)}"
            add_text_box(slide, cite_str, MARGIN_LEFT, Inches(6.8), Inches(4.0), Inches(0.3),
                         token=Typography.FOOTNOTE, color=theme.text_muted)

    add_footer(slide, slide_number, total_slides, theme, section_name=deck_title)
    add_speaker_notes(slide, notes)
