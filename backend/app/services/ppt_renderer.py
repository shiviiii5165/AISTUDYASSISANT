import io
import base64
import httpx
import hashlib
from typing import List, Dict, Optional, Any
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from app.core.config import settings

# 10 Curated Color Palettes (Background, Primary Text, Accent, Secondary Accent)
PALETTES = [
    {"bg": (15, 23, 42), "text": (248, 250, 252), "accent": (56, 189, 248), "secondary": (148, 163, 184)}, # Slate / Sky
    {"bg": (23, 23, 23), "text": (250, 250, 250), "accent": (251, 146, 60), "secondary": (163, 163, 163)}, # Neutral / Orange
    {"bg": (30, 27, 75), "text": (238, 242, 255), "accent": (167, 139, 250), "secondary": (165, 180, 252)}, # Indigo / Violet
    {"bg": (17, 24, 39), "text": (243, 244, 246), "accent": (52, 211, 153), "secondary": (156, 163, 175)}, # Gray / Emerald
    {"bg": (66, 32, 6), "text": (255, 237, 213), "accent": (251, 146, 60), "secondary": (253, 186, 116)},  # Brown / Orange
    {"bg": (12, 74, 110), "text": (240, 249, 255), "accent": (56, 189, 248), "secondary": (125, 211, 252)}, # Sky / Light Blue
    {"bg": (20, 83, 45), "text": (240, 253, 244), "accent": (74, 222, 128), "secondary": (134, 239, 172)}, # Green / Emerald
    {"bg": (88, 28, 135), "text": (250, 245, 255), "accent": (192, 132, 252), "secondary": (216, 180, 254)}, # Purple / Fuchsia
    {"bg": (127, 29, 29), "text": (254, 242, 242), "accent": (248, 113, 113), "secondary": (252, 165, 165)}, # Red / Rose
    {"bg": (24, 24, 27), "text": (250, 250, 250), "accent": (96, 165, 250), "secondary": (161, 161, 170)}, # Zinc / Blue
]

def get_palette_for_topic(topic: str) -> Dict[str, tuple]:
    """Select a consistent palette for a topic based on its hash."""
    hash_val = int(hashlib.md5(topic.encode('utf-8')).hexdigest(), 16)
    return PALETTES[hash_val % len(PALETTES)]

async def generate_slide_image(prompt: str) -> Optional[bytes]:
    """Calls Gemini 2.5 Flash Image to generate a slide visual."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={settings.GEMINI_IMAGE_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"]
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Extract base64 image from standard Gemini generation response
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for part in parts:
                    inline_data = part.get("inlineData", {})
                    if "data" in inline_data:
                        return base64.b64decode(inline_data["data"])
                        
        return None
    except Exception as e:
        print(f"Image generation failed: {e}")
        return None

def add_title_slide(prs, title: str, palette: Dict):
    slide_layout = prs.slide_layouts[0] # Usually Title Slide
    slide = prs.slides.add_slide(slide_layout)
    
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(*palette["bg"])
    
    title_shape = slide.shapes.title
    title_shape.text = title
    
    for paragraph in title_shape.text_frame.paragraphs:
        paragraph.font.color.rgb = RGBColor(*palette["text"])
        paragraph.font.name = "Georgia"
        paragraph.font.bold = True
        paragraph.font.size = Pt(44)
    
    return slide

def add_content_slide(prs, section: Dict, palette: Dict, image_bytes: Optional[bytes] = None):
    slide_layout = prs.slide_layouts[1] # Title and Content
    slide = prs.slides.add_slide(slide_layout)
    
    # Content slides have light background
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(250, 250, 250)
    
    title_shape = slide.shapes.title
    title_shape.text = section.get("title", "Topic")
    for paragraph in title_shape.text_frame.paragraphs:
        paragraph.font.color.rgb = RGBColor(*palette["bg"])
        paragraph.font.name = "Georgia"
        paragraph.font.bold = True
    
    body_shape = slide.placeholders[1]
    tf = body_shape.text_frame
    tf.text = ""
    
    bullets = section.get("body_bullets", [])
    for idx, bullet in enumerate(bullets):
        p = tf.add_paragraph() if idx > 0 else tf.paragraphs[0]
        p.text = bullet
        p.font.color.rgb = RGBColor(50, 50, 50)
        p.font.size = Pt(18)
        p.font.name = "Calibri"
    
    # If image provided, add it to the right side
    if image_bytes:
        try:
            image_stream = io.BytesIO(image_bytes)
            # Position on the right side of the slide
            left = Inches(6.5)
            top = Inches(2.0)
            height = Inches(4.5)
            slide.shapes.add_picture(image_stream, left, top, height=height)
            
            # Shrink text box width to make room for image
            body_shape.width = Inches(5.5)
        except Exception as e:
            print(f"Failed to insert image: {e}")
            
    # Add example/note box if no image and example exists
    elif section.get("example"):
        left = Inches(1)
        top = Inches(5)
        width = Inches(11)
        height = Inches(1.5)
        txBox = slide.shapes.add_textbox(left, top, width, height)
        tf_ex = txBox.text_frame
        tf_ex.word_wrap = True
        p = tf_ex.paragraphs[0]
        p.text = "💡 Example: " + section.get("example")
        p.font.color.rgb = RGBColor(*palette["bg"])
        p.font.size = Pt(16)
        p.font.italic = True
        
        fill = txBox.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(230, 240, 250)

def add_closing_slide(prs, palette: Dict):
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(*palette["bg"])
    
    title_shape = slide.shapes.title
    title_shape.text = "Thank You"
    for paragraph in title_shape.text_frame.paragraphs:
        paragraph.font.color.rgb = RGBColor(*palette["accent"])
        paragraph.font.name = "Georgia"
        paragraph.font.bold = True
        
    return slide

async def generate_pptx_bytes(deck_data: Dict) -> bytes:
    """Takes the JSON structure from the LLM and creates a PPTX byte stream."""
    prs = Presentation()
    
    # Set 16:9 widescreen
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    topic = deck_data.get("deck_title", "Topic Deck")
    palette = get_palette_for_topic(topic)
    
    add_title_slide(prs, topic, palette)
    
    sections = deck_data.get("sections", [])
    for section in sections:
        image_bytes = None
        
        # If visual hint requires an image, generate it
        visual_hint = section.get("visual_hint", "")
        if visual_hint == "generated_image" and section.get("image_prompt"):
            image_bytes = await generate_slide_image(section["image_prompt"])
            
        add_content_slide(prs, section, palette, image_bytes)
        
    add_closing_slide(prs, palette)
    
    output = io.BytesIO()
    prs.save(output)
    output.seek(0)
    
    return output.read()
