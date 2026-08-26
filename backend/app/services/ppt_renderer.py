import io
import base64
import httpx
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Any
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
from app.core.config import settings

# ─────────────────────────────────────────────────────────────────────────────
# COLOR PALETTES — 10 curated dark-mode themes
# Each palette: bg (slide title/closing bg), light (content slide bg tint),
# text (on dark), text_dark (on light), accent, secondary
# ─────────────────────────────────────────────────────────────────────────────
PALETTES = [
    {
        "name": "Midnight Sky",
        "bg": (15, 23, 42), "light": (241, 245, 249),
        "text": (248, 250, 252), "text_dark": (30, 41, 59),
        "accent": (56, 189, 248), "secondary": (148, 163, 184),
    },
    {
        "name": "Warm Charcoal",
        "bg": (23, 23, 23), "light": (245, 245, 245),
        "text": (250, 250, 250), "text_dark": (38, 38, 38),
        "accent": (251, 146, 60), "secondary": (163, 163, 163),
    },
    {
        "name": "Deep Indigo",
        "bg": (30, 27, 75), "light": (238, 242, 255),
        "text": (238, 242, 255), "text_dark": (49, 46, 129),
        "accent": (167, 139, 250), "secondary": (165, 180, 252),
    },
    {
        "name": "Steel Emerald",
        "bg": (17, 24, 39), "light": (240, 253, 244),
        "text": (243, 244, 246), "text_dark": (20, 83, 45),
        "accent": (52, 211, 153), "secondary": (156, 163, 175),
    },
    {
        "name": "Espresso",
        "bg": (66, 32, 6), "light": (255, 247, 237),
        "text": (255, 237, 213), "text_dark": (67, 20, 7),
        "accent": (251, 146, 60), "secondary": (253, 186, 116),
    },
    {
        "name": "Ocean Blue",
        "bg": (12, 74, 110), "light": (240, 249, 255),
        "text": (240, 249, 255), "text_dark": (12, 74, 110),
        "accent": (56, 189, 248), "secondary": (125, 211, 252),
    },
    {
        "name": "Forest",
        "bg": (20, 83, 45), "light": (240, 253, 244),
        "text": (240, 253, 244), "text_dark": (22, 101, 52),
        "accent": (74, 222, 128), "secondary": (134, 239, 172),
    },
    {
        "name": "Royal Purple",
        "bg": (88, 28, 135), "light": (250, 245, 255),
        "text": (250, 245, 255), "text_dark": (107, 33, 168),
        "accent": (192, 132, 252), "secondary": (216, 180, 254),
    },
    {
        "name": "Crimson",
        "bg": (127, 29, 29), "light": (254, 242, 242),
        "text": (254, 242, 242), "text_dark": (153, 27, 27),
        "accent": (248, 113, 113), "secondary": (252, 165, 165),
    },
    {
        "name": "Carbon Blue",
        "bg": (24, 24, 27), "light": (244, 244, 245),
        "text": (250, 250, 250), "text_dark": (39, 39, 42),
        "accent": (96, 165, 250), "secondary": (161, 161, 170),
    },
]

# Fonts
FONT_HEADING = "Georgia"
FONT_BODY = "Calibri"
FONT_MONO = "Consolas"


def get_palette_for_topic(topic: str) -> Dict[str, Any]:
    """Select a consistent palette for a topic based on its hash."""
    hash_val = int(hashlib.md5(topic.encode('utf-8')).hexdigest(), 16)
    return PALETTES[hash_val % len(PALETTES)]


def _set_solid_fill(shape_or_bg, color_tuple):
    """Helper to set solid fill on a shape or background."""
    fill = shape_or_bg.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(*color_tuple)


def _add_accent_bar(slide, palette, position="left"):
    """Add a thin colored accent bar to the edge of a slide."""
    if position == "left":
        left, top, width, height = Emu(0), Emu(0), Inches(0.15), Inches(7.5)
    else:  # top
        left, top, width, height = Emu(0), Emu(0), Inches(13.333), Inches(0.08)

    bar = slide.shapes.add_shape(
        1,  # MSO_SHAPE.RECTANGLE
        left, top, width, height
    )
    _set_solid_fill(bar, palette["accent"])
    bar.line.fill.background()  # No border


def _style_paragraph(paragraph, font_name, font_size_pt, color_tuple, 
                     bold=False, italic=False, alignment=None, space_after_pt=None):
    """Apply consistent styling to a paragraph."""
    paragraph.font.name = font_name
    paragraph.font.size = Pt(font_size_pt)
    paragraph.font.color.rgb = RGBColor(*color_tuple)
    paragraph.font.bold = bold
    paragraph.font.italic = italic
    if alignment:
        paragraph.alignment = alignment
    if space_after_pt is not None:
        paragraph.space_after = Pt(space_after_pt)


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE GENERATION
# ─────────────────────────────────────────────────────────────────────────────

async def generate_slide_image(prompt: str) -> Optional[bytes]:
    """Calls Gemini to generate a slide visual."""
    api_key = settings.GEMINI_IMAGE_API_KEY.strip()
    if not api_key:
        return None
    
    # Try the primary image-capable model (current Gemini 3.x series)
    models_to_try = [
        "gemini-3.6-flash",
        "gemini-3.5-flash",
    ]
    
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        
        enhanced_prompt = (
            f"Generate a clean, minimal, flat-design educational illustration: {prompt}. "
            "Style: soft muted color palette, no text overlays, no watermarks, "
            "suitable for a professional presentation slide. White or transparent background."
        )
        
        payload = {
            "contents": [{"parts": [{"text": enhanced_prompt}]}],
            "generationConfig": {
                "responseModalities": ["IMAGE", "TEXT"],
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 404:
                    continue  # Try next model
                response.raise_for_status()
                data = response.json()
                
                # Extract base64 image from Gemini response
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for part in parts:
                        inline_data = part.get("inlineData", {})
                        if "data" in inline_data:
                            return base64.b64decode(inline_data["data"])
        except Exception as e:
            print(f"Image generation failed with {model_name}: {e}")
            continue
            
    return None


# ─────────────────────────────────────────────────────────────────────────────
# SLIDE BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def add_title_slide(prs, title: str, audience: str, palette: Dict):
    """Creates a visually striking title slide with dark themed background."""
    slide_layout = prs.slide_layouts[6]  # Blank layout for full control
    slide = prs.slides.add_slide(slide_layout)
    
    # Dark themed background
    _set_solid_fill(slide.background, palette["bg"])
    
    # Add accent bar at top
    _add_accent_bar(slide, palette, "top")
    
    # Small decorative accent line
    accent_line = slide.shapes.add_shape(
        1,  # Rectangle
        Inches(5.5), Inches(2.8), Inches(2.3), Inches(0.06)
    )
    _set_solid_fill(accent_line, palette["accent"])
    accent_line.line.fill.background()
    
    # Title text box — large, centered
    title_box = slide.shapes.add_textbox(
        Inches(1.5), Inches(3.0), Inches(10.3), Inches(2.0)
    )
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    _style_paragraph(p, FONT_HEADING, 48, palette["text"], bold=True, alignment=PP_ALIGN.CENTER)
    
    # Subtitle text box
    now = datetime.now()
    subtitle_text = f"AI-Generated  •  {audience.title()} Level  •  {now.strftime('%B %Y')}"
    sub_box = slide.shapes.add_textbox(
        Inches(2.5), Inches(5.2), Inches(8.3), Inches(0.6)
    )
    tf_sub = sub_box.text_frame
    tf_sub.word_wrap = True
    p_sub = tf_sub.paragraphs[0]
    p_sub.text = subtitle_text
    _style_paragraph(p_sub, FONT_BODY, 18, palette["secondary"], alignment=PP_ALIGN.CENTER)
    
    # Branding footer
    footer_box = slide.shapes.add_textbox(
        Inches(4.5), Inches(6.8), Inches(4.3), Inches(0.4)
    )
    tf_footer = footer_box.text_frame
    p_footer = tf_footer.paragraphs[0]
    p_footer.text = "Powered by TeachGenie AI"
    _style_paragraph(p_footer, FONT_BODY, 12, palette["secondary"], italic=True, alignment=PP_ALIGN.CENTER)
    
    return slide


def add_content_slide(prs, section: Dict, slide_number: int, total_slides: int, 
                      palette: Dict, image_bytes: Optional[bytes] = None):
    """Creates a polished content slide with themed styling."""
    slide_layout = prs.slide_layouts[6]  # Blank for full control
    slide = prs.slides.add_slide(slide_layout)
    
    # Light themed background
    _set_solid_fill(slide.background, palette["light"])
    
    # Left accent bar
    _add_accent_bar(slide, palette, "left")
    
    # ─── Title Area ───
    title_box = slide.shapes.add_textbox(
        Inches(0.6), Inches(0.3), Inches(12.0), Inches(0.9)
    )
    tf_title = title_box.text_frame
    tf_title.word_wrap = True
    p_title = tf_title.paragraphs[0]
    p_title.text = section.get("title", "Topic")
    _style_paragraph(p_title, FONT_HEADING, 32, palette["text_dark"], bold=True, space_after_pt=4)
    
    # Thin separator line under title
    sep = slide.shapes.add_shape(
        1,  # Rectangle
        Inches(0.6), Inches(1.25), Inches(2.0), Inches(0.04)
    )
    _set_solid_fill(sep, palette["accent"])
    sep.line.fill.background()
    
    # ─── Body Content Area ───
    has_image = image_bytes is not None
    body_width = Inches(6.5) if has_image else Inches(11.5)
    
    body_box = slide.shapes.add_textbox(
        Inches(0.6), Inches(1.6), body_width, Inches(4.5)
    )
    tf_body = body_box.text_frame
    tf_body.word_wrap = True
    
    bullets = section.get("body_bullets", [])
    for idx, bullet in enumerate(bullets):
        p = tf_body.add_paragraph() if idx > 0 else tf_body.paragraphs[0]
        
        # Add accent-colored bullet marker
        run_marker = p.add_run()
        run_marker.text = "▸  "
        run_marker.font.color.rgb = RGBColor(*palette["accent"])
        run_marker.font.size = Pt(18)
        run_marker.font.name = FONT_BODY
        
        # Add bullet text
        run_text = p.add_run()
        run_text.text = bullet
        run_text.font.color.rgb = RGBColor(*palette["text_dark"])
        run_text.font.size = Pt(18)
        run_text.font.name = FONT_BODY
        
        p.space_after = Pt(12)
        p.line_spacing = Pt(26)
    
    # ─── Image (Right Side) ───
    if image_bytes:
        try:
            image_stream = io.BytesIO(image_bytes)
            # Position on the right 1/3 of the widescreen slide
            img_left = Inches(7.8)
            img_top = Inches(1.6)
            img_height = Inches(4.5)
            
            pic = slide.shapes.add_picture(image_stream, img_left, img_top, height=img_height)
            
            # Add subtle rounded-look border effect (via line)
            pic.line.color.rgb = RGBColor(*palette["secondary"])
            pic.line.width = Pt(1)
        except Exception as e:
            print(f"Failed to insert image: {e}")
    
    # ─── Example Box (if no image and example exists) ───
    elif section.get("example"):
        ex_left = Inches(0.6)
        ex_top = Inches(5.2) if len(bullets) <= 3 else Inches(5.8)
        ex_width = Inches(11.5)
        ex_height = Inches(1.3)
        
        ex_box = slide.shapes.add_textbox(ex_left, ex_top, ex_width, ex_height)
        _set_solid_fill(ex_box, _lighten_color(palette["accent"], factor=0.85))
        
        tf_ex = ex_box.text_frame
        tf_ex.word_wrap = True
        tf_ex.margin_left = Inches(0.2)
        tf_ex.margin_right = Inches(0.2)
        tf_ex.margin_top = Inches(0.1)
        
        # Example label
        p_label = tf_ex.paragraphs[0]
        run_icon = p_label.add_run()
        run_icon.text = "💡 "
        run_icon.font.size = Pt(16)
        
        run_label = p_label.add_run()
        run_label.text = "Example"
        run_label.font.bold = True
        run_label.font.size = Pt(16)
        run_label.font.color.rgb = RGBColor(*palette["text_dark"])
        run_label.font.name = FONT_BODY
        
        # Example content
        p_content = tf_ex.add_paragraph()
        p_content.text = section.get("example", "")
        _style_paragraph(p_content, FONT_BODY, 15, palette["text_dark"], italic=True)
    
    # ─── Slide Number (bottom right) ───
    num_box = slide.shapes.add_textbox(
        Inches(12.0), Inches(7.0), Inches(1.0), Inches(0.3)
    )
    tf_num = num_box.text_frame
    p_num = tf_num.paragraphs[0]
    p_num.text = f"{slide_number} / {total_slides}"
    _style_paragraph(p_num, FONT_BODY, 11, palette["secondary"], alignment=PP_ALIGN.RIGHT)
    
    # ─── Speaker Notes ───
    speaker_note = section.get("speaker_note", "")
    if speaker_note:
        notes_slide = slide.notes_slide
        notes_tf = notes_slide.notes_text_frame
        notes_tf.text = speaker_note
    
    return slide


def add_closing_slide(prs, deck_data: Dict, palette: Dict):
    """Creates a polished closing slide with key takeaways and branding."""
    slide_layout = prs.slide_layouts[6]  # Blank
    slide = prs.slides.add_slide(slide_layout)
    
    # Dark themed background matching title
    _set_solid_fill(slide.background, palette["bg"])
    
    # Top accent bar
    _add_accent_bar(slide, palette, "top")
    
    # "Thank You" heading
    ty_box = slide.shapes.add_textbox(
        Inches(1.5), Inches(1.5), Inches(10.3), Inches(1.2)
    )
    tf_ty = ty_box.text_frame
    p_ty = tf_ty.paragraphs[0]
    p_ty.text = "Thank You"
    _style_paragraph(p_ty, FONT_HEADING, 48, palette["accent"], bold=True, alignment=PP_ALIGN.CENTER)
    
    # Decorative line
    dec_line = slide.shapes.add_shape(
        1, Inches(5.5), Inches(2.8), Inches(2.3), Inches(0.05)
    )
    _set_solid_fill(dec_line, palette["accent"])
    dec_line.line.fill.background()
    
    # Key takeaways section
    takeaways = deck_data.get("key_takeaways", [])
    if not takeaways:
        # Fallback: use section titles as summary
        sections = deck_data.get("sections", [])
        takeaways = [s.get("title", "") for s in sections[:5] if s.get("title")]
    
    if takeaways:
        ta_box = slide.shapes.add_textbox(
            Inches(2.5), Inches(3.2), Inches(8.3), Inches(3.0)
        )
        tf_ta = ta_box.text_frame
        tf_ta.word_wrap = True
        
        # Label
        p_label = tf_ta.paragraphs[0]
        p_label.text = "Key Takeaways"
        _style_paragraph(p_label, FONT_BODY, 16, palette["secondary"], bold=True, 
                        alignment=PP_ALIGN.CENTER, space_after_pt=12)
        
        for takeaway in takeaways[:5]:
            p = tf_ta.add_paragraph()
            run_marker = p.add_run()
            run_marker.text = "✦  "
            run_marker.font.color.rgb = RGBColor(*palette["accent"])
            run_marker.font.size = Pt(16)
            
            run_text = p.add_run()
            run_text.text = takeaway
            run_text.font.color.rgb = RGBColor(*palette["text"])
            run_text.font.size = Pt(16)
            run_text.font.name = FONT_BODY
            
            p.space_after = Pt(8)
            p.alignment = PP_ALIGN.CENTER
    
    # Branding footer
    footer_box = slide.shapes.add_textbox(
        Inches(3.5), Inches(6.6), Inches(6.3), Inches(0.4)
    )
    tf_footer = footer_box.text_frame
    p_footer = tf_footer.paragraphs[0]
    p_footer.text = "Generated with TeachGenie AI  •  teachgenie.online"
    _style_paragraph(p_footer, FONT_BODY, 12, palette["secondary"], italic=True, alignment=PP_ALIGN.CENTER)
    
    return slide


def _lighten_color(color_tuple, factor=0.8):
    """Create a lighter version of a color for backgrounds."""
    return tuple(min(255, int(c + (255 - c) * factor)) for c in color_tuple)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN GENERATION FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

MAX_IMAGES = 5  # Limit images to stay within Vercel time constraints

async def generate_pptx_bytes(deck_data: Dict, audience: str = "university") -> bytes:
    """Takes the JSON structure from the LLM and creates a PPTX byte stream."""
    import asyncio
    
    prs = Presentation()
    
    # Set 16:9 widescreen
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    topic = deck_data.get("deck_title", "Topic Deck")
    palette = get_palette_for_topic(topic)
    sections = deck_data.get("sections", [])
    total_slides = len(sections) + 2  # Title + Closing
    
    # 1. Title Slide
    add_title_slide(prs, topic, audience, palette)
    
    # 2. Generate ALL images in parallel (huge speed win)
    image_tasks = []
    image_indices = []
    
    for idx, section in enumerate(sections):
        visual_hint = section.get("visual_hint", "")
        if visual_hint == "generated_image" and section.get("image_prompt"):
            if len(image_tasks) < MAX_IMAGES:
                image_tasks.append(generate_slide_image(section["image_prompt"]))
                image_indices.append(idx)
    
    # Run all image generations concurrently
    image_results = []
    if image_tasks:
        try:
            image_results = await asyncio.gather(*image_tasks, return_exceptions=True)
        except Exception as e:
            print(f"Parallel image generation error: {e}")
            image_results = [None] * len(image_tasks)
    
    # Map results back to section indices
    image_map = {}
    for i, idx in enumerate(image_indices):
        result = image_results[i] if i < len(image_results) else None
        if isinstance(result, Exception):
            print(f"Image for section {idx} failed: {result}")
            result = None
        image_map[idx] = result
    
    # 3. Build content slides with pre-generated images
    for idx, section in enumerate(sections):
        image_bytes = image_map.get(idx, None)
        slide_number = idx + 2  # 1-indexed, after title
        add_content_slide(prs, section, slide_number, total_slides, palette, image_bytes)
    
    # 4. Closing Slide
    add_closing_slide(prs, deck_data, palette)
    
    output = io.BytesIO()
    prs.save(output)
    output.seek(0)
    
    return output.read()
