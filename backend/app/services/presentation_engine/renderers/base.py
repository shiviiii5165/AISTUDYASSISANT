"""
LearnByGenie Renderer — Base Drawing Primitives
===============================================
All renderers build slides using ONLY these primitives.
No renderer may scatter raw pptx calls with arbitrary values.
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from io import BytesIO
from typing import Optional, List

from ..tokens import (
    ThemeColors, Typography, TypeToken,
    MARGIN_LEFT, MARGIN_RIGHT, MARGIN_TOP, MARGIN_BOTTOM,
    CONTENT_WIDTH, SLIDE_WIDTH, SLIDE_HEIGHT,
    ZONE_TITLE_TOP, ZONE_TITLE_HEIGHT,
    ZONE_SUBTITLE_TOP, ZONE_SUBTITLE_HEIGHT,
    ZONE_CONTENT_TOP, ZONE_CONTENT_HEIGHT,
    ZONE_FOOTER_TOP, ZONE_FOOTER_HEIGHT,
    CARD_CORNER_RADIUS, CARD_PADDING, CARD_BORDER_WIDTH,
    BULLET_GLYPH, TAKEAWAY_GLYPH,
    grid_x, grid_width,
)


# ═══════════════════════════════════════════════════════════════════════════
# TEXT PRIMITIVES
# ═══════════════════════════════════════════════════════════════════════════

from ..text_fitter import fit_text_to_box

def add_text_box(
    slide: Slide,
    text: str,
    left: Emu, top: Emu, width: Emu, height: Emu,
    token: TypeToken,
    color: RGBColor = None,
    alignment: int = PP_ALIGN.LEFT,
    anchor: int = MSO_ANCHOR.TOP,
    word_wrap: bool = True,
    bold: Optional[bool] = None,
    italic: Optional[bool] = None,
) -> None:
    """Add a styled text box to a slide using a TypeToken, auto-fitting to bounds."""
    # Fit text to box height
    actual_token, actual_text = fit_text_to_box(text, token, width, height, word_wrap=word_wrap)

    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = word_wrap

    p = tf.paragraphs[0]
    p.text = actual_text
    p.font.name = actual_token.font_name
    p.font.size = actual_token.size
    p.font.bold = bold if bold is not None else actual_token.bold
    p.font.italic = italic if italic is not None else actual_token.italic
    if color:
        p.font.color.rgb = color
    p.alignment = alignment
    p.space_after = Pt(0)
    p.space_before = Pt(0)

    # Line spacing
    if actual_token.line_spacing != 1.0:
        p.line_spacing = actual_token.line_spacing

    tf.auto_size = None
    # Anchor (vertical alignment)
    try:
        txBox.text_frame._txBody.bodyPr.set("anchor", {
            MSO_ANCHOR.TOP: "t",
            MSO_ANCHOR.MIDDLE: "ctr",
            MSO_ANCHOR.BOTTOM: "b",
        }.get(anchor, "t"))
    except Exception:
        pass


def add_bullet_list(
    slide: Slide,
    bullets: List[str],
    left: Emu, top: Emu, width: Emu, height: Emu,
    token: TypeToken,
    text_color: RGBColor = None,
    accent_color: RGBColor = None,
    glyph: str = BULLET_GLYPH,
    max_bullets: int = 7,
) -> None:
    """Add a formatted bullet list to a slide, auto-fitting to bounds."""
    display_bullets = bullets[:max_bullets]
    if not display_bullets:
        return
        
    # Combine bullets into a single string to estimate height
    # Pass per-paragraph spacing so the fitter accounts for space_before/space_after
    combined_text = "\n".join(display_bullets)
    actual_token, actual_text = fit_text_to_box(
        combined_text, token, width, height,
        para_space_after_pt=6.0,
        para_space_before_pt=2.0,
    )
    
    # Re-split actual_text (which might be truncated)
    final_bullets = actual_text.split("\n")

    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True

    for i, bullet_text in enumerate(final_bullets):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()

        # Glyph run
        run_glyph = p.add_run()
        run_glyph.text = f"{glyph}  "
        run_glyph.font.name = actual_token.font_name
        run_glyph.font.size = actual_token.size
        run_glyph.font.bold = True
        if accent_color:
            run_glyph.font.color.rgb = accent_color

        # Text run
        run_text = p.add_run()
        run_text.text = bullet_text
        run_text.font.name = actual_token.font_name
        run_text.font.size = actual_token.size
        run_text.font.bold = actual_token.bold
        if text_color:
            run_text.font.color.rgb = text_color

        p.space_after = Pt(6)
        p.space_before = Pt(2)
        if actual_token.line_spacing != 1.0:
            p.line_spacing = actual_token.line_spacing


# ═══════════════════════════════════════════════════════════════════════════
# SHAPE PRIMITIVES
# ═══════════════════════════════════════════════════════════════════════════

def add_filled_rect(
    slide: Slide,
    left: Emu, top: Emu, width: Emu, height: Emu,
    fill_color: RGBColor,
    border_color: RGBColor = None,
    corner_radius: Emu = None,
) -> None:
    """Add a filled rectangle (card background, accent bar, etc.)."""
    if corner_radius:
        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height
        )
        min_dim = min(width, height)
        if min_dim > 0:
            adj = min(0.5, max(0.0, float(corner_radius) / float(min_dim)))
            shape.adjustments[0] = adj
    else:
        shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, left, top, width, height
        )

    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color

    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = CARD_BORDER_WIDTH
    else:
        shape.line.fill.background()

    shape.shadow.inherit = False


def add_accent_bar(
    slide: Slide,
    left: Emu, top: Emu,
    width: Emu = Inches(0.08),
    height: Emu = Inches(0.6),
    color: RGBColor = None,
) -> None:
    """Add a thin vertical accent bar (often to the left of a title)."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, left, top, width, height
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    shape.shadow.inherit = False


def add_card(
    slide: Slide,
    left: Emu, top: Emu, width: Emu, height: Emu,
    fill_color: RGBColor,
    border_color: RGBColor = None,
    shadow: bool = None,
) -> None:
    """Add a card (rounded rectangle with border and optional shadow)."""
    from ..tokens import CARD_SHADOW, CARD_CORNER_RADIUS
    shape = None
    # Use ROUNDED_RECTANGLE for cards
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color

    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = CARD_BORDER_WIDTH
    else:
        shape.line.fill.background()

    # Subtle modern card rounding (Gamma/Stripe style)
    # Standard roundRect adjustment is 0.0 to 0.5.
    # Clamp between 0.02 and 0.06 so cards never deform into pills or circles
    min_dim = min(width, height)
    if min_dim > 0:
        adj = min(0.06, max(0.02, float(CARD_CORNER_RADIUS) / float(min_dim)))
        shape.adjustments[0] = adj
    else:
        shape.adjustments[0] = 0.04

    # Subtle shadow for premium depth
    use_shadow = shadow if shadow is not None else CARD_SHADOW
    if use_shadow:
        try:
            from lxml import etree
            ns = 'http://schemas.openxmlformats.org/drawingml/2006/main'
            spPr = shape._element.find(f'.//{{{ns}}}spPr')
            if spPr is not None:
                effectLst = etree.SubElement(spPr, f'{{{ns}}}effectLst')
                outerShdw = etree.SubElement(effectLst, f'{{{ns}}}outerShdw')
                outerShdw.set('blurRad', '50800')   # 4pt blur
                outerShdw.set('dist', '25400')       # 2pt offset
                outerShdw.set('dir', '5400000')      # bottom direction
                outerShdw.set('algn', 'tl')
                srgbClr = etree.SubElement(outerShdw, f'{{{ns}}}srgbClr')
                srgbClr.set('val', '000000')
                alpha = etree.SubElement(srgbClr, f'{{{ns}}}alpha')
                alpha.set('val', '15000')            # 15% opacity
        except Exception:
            pass
    else:
        shape.shadow.inherit = False


def add_category_pill(
    slide: Slide,
    text: str,
    left: Emu, top: Emu,
    bg_color: RGBColor,
    text_color: RGBColor,
    width: Emu = Inches(1.8),
    height: Emu = Inches(0.32),
) -> None:
    """Add a small category pill / badge."""
    add_filled_rect(slide, left, top, width, height, bg_color, corner_radius=Inches(0.16))
    add_text_box(
        slide, text.upper(),
        left, top, width, height,
        token=Typography.BADGE,
        color=text_color,
        alignment=PP_ALIGN.CENTER,
        anchor=MSO_ANCHOR.MIDDLE,
    )


# ═══════════════════════════════════════════════════════════════════════════
# IMAGE PRIMITIVES
# ═══════════════════════════════════════════════════════════════════════════

def add_image(
    slide: Slide,
    image_bytes: bytes,
    left: Emu, top: Emu, width: Emu, height: Emu,
    preserve_aspect: bool = True,
    corner_radius: Emu = None,
) -> None:
    """Embed an image from bytes into the slide, preserving aspect ratio.
    
    If preserve_aspect is True (default), the image is scaled to fit within
    the bounding box while maintaining its original proportions, then centered.
    """
    from PIL import Image as PILImage
    image_stream = BytesIO(image_bytes)
    
    if preserve_aspect:
        try:
            # Read image dimensions
            img = PILImage.open(BytesIO(image_bytes))
            img_w, img_h = img.size
            img.close()
            
            # Calculate aspect-ratio-preserving dimensions
            box_w = _to_inches(width)
            box_h = _to_inches(height)
            img_aspect = img_w / max(img_h, 1)
            box_aspect = box_w / max(box_h, 0.01)
            
            if img_aspect > box_aspect:
                # Image is wider than box — fit to width
                fit_w = box_w
                fit_h = box_w / img_aspect
            else:
                # Image is taller than box — fit to height
                fit_h = box_h
                fit_w = box_h * img_aspect
            
            # Center within bounding box
            offset_x = (box_w - fit_w) / 2
            offset_y = (box_h - fit_h) / 2
            
            final_left = left + Inches(offset_x)
            final_top = top + Inches(offset_y)
            final_w = Inches(fit_w)
            final_h = Inches(fit_h)
        except Exception:
            # Fallback to original behavior
            final_left, final_top, final_w, final_h = left, top, width, height
    else:
        final_left, final_top, final_w, final_h = left, top, width, height
    
    image_stream = BytesIO(image_bytes)
    pic = slide.shapes.add_picture(image_stream, final_left, final_top, final_w, final_h)
    
    # Apply rounded corners if requested
    if corner_radius:
        try:
            from lxml import etree
            spPr = pic._element.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}spPr')
            if spPr is None:
                spPr = etree.SubElement(pic._element, '{http://schemas.openxmlformats.org/drawingml/2006/main}spPr')
            prstGeom = etree.SubElement(spPr, '{http://schemas.openxmlformats.org/drawingml/2006/main}prstGeom')
            prstGeom.set('prst', 'roundRect')
            avLst = etree.SubElement(prstGeom, '{http://schemas.openxmlformats.org/drawingml/2006/main}avLst')
            min_dim = min(final_w, final_h)
            adj_pct = min(0.08, max(0.02, float(corner_radius) / float(min_dim))) if min_dim > 0 else 0.04
            adj_val = int(adj_pct * 100000)
            gd = etree.SubElement(avLst, '{http://schemas.openxmlformats.org/drawingml/2006/main}gd')
            gd.set('name', 'adj')
            gd.set('fmla', f'val {adj_val}')
        except Exception:
            pass


def _to_inches(val) -> float:
    """Convert EMU or Inches value to float inches."""
    if hasattr(val, 'inches'):
        return val.inches
    return val / 914400.0


# ═══════════════════════════════════════════════════════════════════════════
# FOOTER / BRANDING
# ═══════════════════════════════════════════════════════════════════════════

def add_gradient_bar(
    slide: Slide,
    left: Emu, top: Emu, width: Emu, height: Emu,
    color_start: RGBColor,
    color_end: RGBColor,
) -> None:
    """Add a horizontal gradient bar (for premium hero accents)."""
    try:
        from lxml import etree
        shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
        shape.line.fill.background()
        shape.shadow.inherit = False
        
        spPr = shape._element.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}spPr')
        # Remove solid fill
        solidFill = spPr.find('{http://schemas.openxmlformats.org/drawingml/2006/main}solidFill')
        if solidFill is not None:
            spPr.remove(solidFill)
        
        ns = 'http://schemas.openxmlformats.org/drawingml/2006/main'
        gradFill = etree.SubElement(spPr, f'{{{ns}}}gradFill')
        gsLst = etree.SubElement(gradFill, f'{{{ns}}}gsLst')
        
        # Start color
        gs1 = etree.SubElement(gsLst, f'{{{ns}}}gs')
        gs1.set('pos', '0')
        srgb1 = etree.SubElement(gs1, f'{{{ns}}}srgbClr')
        srgb1.set('val', f'{color_start.red:02X}{color_start.green:02X}{color_start.blue:02X}')
        
        # End color
        gs2 = etree.SubElement(gsLst, f'{{{ns}}}gs')
        gs2.set('pos', '100000')
        srgb2 = etree.SubElement(gs2, f'{{{ns}}}srgbClr')
        srgb2.set('val', f'{color_end.red:02X}{color_end.green:02X}{color_end.blue:02X}')
        
        lin = etree.SubElement(gradFill, f'{{{ns}}}lin')
        lin.set('ang', '0')  # horizontal
        lin.set('scaled', '1')
    except Exception:
        # Fallback to solid fill with start color
        add_filled_rect(slide, left, top, width, height, color_start)


def add_footer(
    slide: Slide,
    slide_number: int,
    total_slides: int,
    theme: ThemeColors,
    section_name: str = "",
) -> None:
    """Add a polished footer with progress bar, slide number, and branding."""
    # ── Progress bar (thin accent strip showing position in deck) ──
    progress_ratio = min(slide_number / max(total_slides, 1), 1.0)
    progress_width = Inches(SLIDE_WIDTH.inches * progress_ratio)
    add_filled_rect(
        slide, Inches(0), Inches(SLIDE_HEIGHT.inches - 0.06),
        progress_width, Inches(0.06),
        fill_color=theme.primary,
    )
    # Background track
    add_filled_rect(
        slide, progress_width, Inches(SLIDE_HEIGHT.inches - 0.06),
        Inches(SLIDE_WIDTH.inches) - progress_width, Inches(0.06),
        fill_color=theme.border_light,
    )

    # Slide number (right) — formatted as "03 / 12"
    num_str = f"{slide_number:02d} / {total_slides:02d}"
    add_text_box(
        slide, num_str,
        SLIDE_WIDTH - Inches(1.4), ZONE_FOOTER_TOP,
        Inches(1.2), ZONE_FOOTER_HEIGHT,
        token=Typography.CAPTION,
        color=theme.text_muted,
        alignment=PP_ALIGN.RIGHT,
    )

    # Section name (left) — if provided
    if section_name:
        add_text_box(
            slide, section_name,
            MARGIN_LEFT, ZONE_FOOTER_TOP,
            Inches(4.0), ZONE_FOOTER_HEIGHT,
            token=Typography.CAPTION,
            color=theme.text_muted,
            alignment=PP_ALIGN.LEFT,
        )

    # Brand mark (center)
    add_text_box(
        slide, "LearnByGenie AI",
        Inches(5.5), ZONE_FOOTER_TOP,
        Inches(2.5), ZONE_FOOTER_HEIGHT,
        token=Typography.FOOTNOTE,
        color=theme.border,
        alignment=PP_ALIGN.CENTER,
    )


def add_kpi_metrics(
    slide: Slide,
    metrics: list,
    left: "Emu", top: "Emu", width: "Emu", height: "Emu",
    theme: ThemeColors,
) -> None:
    """
    Render KPI metric cards: large value + label + context sentence.
    Each metric dict: {"value": str, "label": str, "context": str}
    """
    n = max(1, len(metrics))
    gap = Inches(0.2)
    card_w = (width - gap * (n - 1)) / n
    card_h = height

    value_zone_h = Inches(1.2)
    label_zone_h = Inches(0.42)

    for i, metric in enumerate(metrics):
        cx = left + i * (card_w + gap)
        add_filled_rect(slide, cx, top, card_w, card_h,
                        fill_color=theme.surface_alt, border_color=theme.border)

        value = str(metric.get("value", "—"))
        label = str(metric.get("label", ""))
        context = str(metric.get("context", ""))

        add_text_box(
            slide, value,
            cx + Inches(0.1), top + Inches(0.15),
            card_w - Inches(0.2), value_zone_h,
            token=Typography.KPI_NUMBER, color=theme.primary,
            alignment=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
        )
        add_text_box(
            slide, label.upper(),
            cx + Inches(0.1), top + value_zone_h,
            card_w - Inches(0.2), label_zone_h,
            token=Typography.BADGE, color=theme.text_muted,
            alignment=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.TOP,
        )
        ctx_top = top + value_zone_h + label_zone_h + Inches(0.1)
        ctx_h = card_h - value_zone_h - label_zone_h - Inches(0.2)
        if context and ctx_h > Inches(0.2):
            add_text_box(
                slide, context,
                cx + Inches(0.15), ctx_top,
                card_w - Inches(0.3), ctx_h,
                token=Typography.CAPTION, color=theme.text_muted,
                alignment=PP_ALIGN.CENTER, word_wrap=True,
            )


def add_speaker_notes(slide: Slide, notes_text: str) -> None:
    """Add presenter notes to a slide."""
    if not notes_text:
        return
    notes_slide = slide.notes_slide
    notes_slide.notes_text_frame.text = notes_text


def add_icon_led_point(
    slide: Slide,
    label: str,
    description: str,
    left: Emu, top: Emu, width: Emu,
    theme: "ThemeColors",
    icon_char: str = "▸",
    point_height: Emu = Inches(0.75),
) -> Emu:
    """
    Render an icon-led sub-point: small arrow/chevron + bold label + description.
    Returns the bottom edge (top + actual height) for stacking.

    Pattern: ▸ **Bold Label** — One supporting line of text.
    """
    icon_w = Inches(0.25)
    text_left = left + icon_w

    # Icon/arrow character
    add_text_box(
        slide, icon_char,
        left, top, icon_w, Inches(0.3),
        token=Typography.BODY,
        color=theme.accent,
        alignment=PP_ALIGN.LEFT,
        bold=True,
    )

    # Label (bold)
    add_text_box(
        slide, label,
        text_left, top, width - icon_w, Inches(0.3),
        token=Typography.BODY,
        color=theme.text,
        alignment=PP_ALIGN.LEFT,
        bold=True,
    )

    # Description (below label)
    if description:
        add_text_box(
            slide, description,
            text_left, top + Inches(0.3), width - icon_w, Inches(0.4),
            token=Typography.BULLET_SMALL,
            color=theme.text_muted,
            alignment=PP_ALIGN.LEFT,
        )

    return top + point_height

