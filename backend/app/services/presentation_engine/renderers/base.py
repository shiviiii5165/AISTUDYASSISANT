"""
TeachGenie Renderer — Base Drawing Primitives
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
    combined_text = "\n".join(display_bullets)
    actual_token, actual_text = fit_text_to_box(combined_text, token, width, height)
    
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
        # Set corner radius via XML
        try:
            from lxml import etree
            sp = shape._element
            ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
            prstGeom = sp.find('.//a:prstGeom', ns)
            if prstGeom is not None:
                avLst = prstGeom.find('a:avLst', ns)
                if avLst is None:
                    avLst = etree.SubElement(prstGeom, '{http://schemas.openxmlformats.org/drawingml/2006/main}avLst')
                gd = etree.SubElement(avLst, '{http://schemas.openxmlformats.org/drawingml/2006/main}gd')
                gd.set('name', 'adj')
                gd.set('fmla', f'val {int(corner_radius)}')
        except Exception:
            pass
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
) -> None:
    """Add a card (rounded rectangle with border)."""
    add_filled_rect(
        slide, left, top, width, height,
        fill_color=fill_color,
        border_color=border_color,
        corner_radius=CARD_CORNER_RADIUS,
    )


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
) -> None:
    """Embed an image from bytes into the slide."""
    image_stream = BytesIO(image_bytes)
    slide.shapes.add_picture(image_stream, left, top, width, height)


# ═══════════════════════════════════════════════════════════════════════════
# FOOTER / BRANDING
# ═══════════════════════════════════════════════════════════════════════════

def add_footer(
    slide: Slide,
    slide_number: int,
    total_slides: int,
    theme: ThemeColors,
    section_name: str = "",
) -> None:
    """Add a subtle footer with slide number and optional section name."""
    # Slide number (right)
    add_text_box(
        slide,
        f"{slide_number} / {total_slides}",
        SLIDE_WIDTH - Inches(1.2), ZONE_FOOTER_TOP,
        Inches(1.0), ZONE_FOOTER_HEIGHT,
        token=Typography.CAPTION,
        color=theme.text_muted,
        alignment=PP_ALIGN.RIGHT,
    )

    # Section name (left) — if provided
    if section_name:
        add_text_box(
            slide,
            section_name,
            MARGIN_LEFT, ZONE_FOOTER_TOP,
            Inches(4.0), ZONE_FOOTER_HEIGHT,
            token=Typography.CAPTION,
            color=theme.text_muted,
            alignment=PP_ALIGN.LEFT,
        )

    # Brand mark (center-ish)
    add_text_box(
        slide,
        "TeachGenie AI",
        Inches(5.5), ZONE_FOOTER_TOP,
        Inches(2.5), ZONE_FOOTER_HEIGHT,
        token=Typography.FOOTNOTE,
        color=theme.border,
        alignment=PP_ALIGN.CENTER,
    )


def add_speaker_notes(slide: Slide, notes_text: str) -> None:
    """Add presenter notes to a slide."""
    if not notes_text:
        return
    notes_slide = slide.notes_slide
    notes_slide.notes_text_frame.text = notes_text
