"""
Python Graphics Engine — Deterministic Frame Renderer
=====================================================
Renders clean, high-resolution educational slides, diagrams, process flows,
and comparison cards directly to PNG frames using Pillow (Zero LLM Tokens).
"""
import os
import io
from typing import Dict, Any, List, Optional
from PIL import Image, ImageDraw, ImageFont
from ..design_tokens import get_design_tokens, DESIGN_TOKENS

THEME_COLORS = DESIGN_TOKENS


def hex_to_rgb(hex_str: str) -> tuple:
    """Converts #RRGGBB hex string to RGB tuple."""
    hex_clean = hex_str.lstrip('#')
    return tuple(int(hex_clean[i:i+2], 16) for i in (0, 2, 4))


def create_base_canvas(width: int = 1280, height: int = 720, style: str = "academic") -> Image.Image:
    """Creates a clean background canvas with subtle header accent line."""
    tokens = get_design_tokens(style)
    bg_rgb = hex_to_rgb(tokens["bg_color"])
    primary_rgb = hex_to_rgb(tokens["primary"])

    img = Image.new("RGB", (width, height), color=bg_rgb)
    draw = ImageDraw.Draw(img)

    # Accent top border
    draw.rectangle([0, 0, width, 8], fill=primary_rgb)
    return img


def render_concept_card_frame(
    title: str,
    bullets: List[str],
    caption: str = "",
    citation_badge: Optional[str] = None,
    width: int = 1280,
    height: int = 720,
    style: str = "academic",
) -> Image.Image:
    """Renders a structured educational slide with title, bullet points, and source badge."""
    tokens = get_design_tokens(style)
    img = create_base_canvas(width, height, style)
    draw = ImageDraw.Draw(img)

    primary_rgb = hex_to_rgb(tokens["primary"])
    text_dark_rgb = hex_to_rgb(tokens["text_dark"])
    text_muted_rgb = hex_to_rgb(tokens["text_muted"])
    card_bg_rgb = hex_to_rgb(tokens["card_bg"])
    border_rgb = hex_to_rgb(tokens["border"])
    accent_rgb = hex_to_rgb(tokens["accent"])

    # 1. Title Header
    try:
        font_title = ImageFont.truetype("arial.ttf", 36)
        font_bullet = ImageFont.truetype("arial.ttf", 22)
        font_badge = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font_title = ImageFont.load_default()
        font_bullet = ImageFont.load_default()
        font_badge = ImageFont.load_default()

    # Draw Title
    draw.text((80, 60), title or "Core Concept", fill=primary_rgb, font=font_title)
    
    if caption:
        draw.text((80, 110), caption, fill=text_muted_rgb, font=font_badge)

    # 2. Main Content Card
    card_box = [80, 150, width - 80, height - 80]
    draw.rounded_rectangle(card_box, radius=tokens["border_radius"], fill=card_bg_rgb, outline=border_rgb, width=2)

    # 3. Bullets
    y_offset = 190
    for idx, bullet in enumerate(bullets[:5]):
        badge_box = [110, y_offset, 140, y_offset + 30]
        draw.rounded_rectangle(badge_box, radius=6, fill=accent_rgb)
        draw.text((120, y_offset + 5), str(idx + 1), fill=primary_rgb, font=font_badge)

        draw.text((160, y_offset + 4), bullet, fill=text_dark_rgb, font=font_bullet)
        y_offset += 65

    # 4. Citation Badge if provided
    if citation_badge:
        cite_text = f"Source: {citation_badge}"
        draw.rectangle([width - 240, height - 60, width - 90, height - 30], fill=accent_rgb)
        draw.text((width - 230, height - 52), cite_text, fill=primary_rgb, font=font_badge)

    return img


def render_diagram_flow_frame(
    title: str,
    nodes: List[str],
    width: int = 1280,
    height: int = 720,
    style: str = "academic",
) -> Image.Image:
    """Renders a horizontal process flow diagram with connecting arrows."""
    tokens = get_design_tokens(style)
    img = create_base_canvas(width, height, style)
    draw = ImageDraw.Draw(img)

    primary_rgb = hex_to_rgb(tokens["primary"])
    text_dark_rgb = hex_to_rgb(tokens["text_dark"])
    card_bg_rgb = hex_to_rgb(tokens["card_bg"])

    try:
        font_title = ImageFont.truetype("arial.ttf", 36)
        font_node = ImageFont.truetype("arial.ttf", 20)
    except Exception:
        font_title = ImageFont.load_default()
        font_node = ImageFont.load_default()

    draw.text((80, 60), title or "Process Flow Diagram", fill=primary_rgb, font=font_title)

    node_count = max(2, min(5, len(nodes)))
    step_width = (width - 200) // node_count
    node_w = int(step_width * 0.75)
    node_h = 100
    y_pos = (height // 2) - 20

    for i, node_text in enumerate(nodes[:node_count]):
        x_pos = 100 + (i * step_width)
        box = [x_pos, y_pos, x_pos + node_w, y_pos + node_h]
        
        # Node box
        draw.rounded_rectangle(box, radius=tokens["border_radius"], fill=card_bg_rgb, outline=primary_rgb, width=3)
        draw.text((x_pos + 15, y_pos + 38), node_text[:20], fill=text_dark_rgb, font=font_node)

        # Arrow to next node
        if i < node_count - 1:
            arrow_start_x = x_pos + node_w + 10
            arrow_end_x = x_pos + step_width - 10
            arrow_y = y_pos + (node_h // 2)
            draw.line([arrow_start_x, arrow_y, arrow_end_x, arrow_y], fill=primary_rgb, width=4)
            draw.polygon([
                (arrow_end_x, arrow_y),
                (arrow_end_x - 10, arrow_y - 6),
                (arrow_end_x - 10, arrow_y + 6)
            ], fill=primary_rgb)

    return img


def render_scene_to_image_file(
    scene_data: Dict[str, Any],
    output_path: str,
    width: int = 1280,
    height: int = 720,
    style: str = "academic",
) -> str:
    """Renders scene specification to a local PNG file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    visual_spec = scene_data.get("visual_spec", {})
    diagram_type = visual_spec.get("diagram_type", "cards")
    title = visual_spec.get("title") or scene_data.get("caption") or scene_data.get("concept_id", "Concept")
    bullets = visual_spec.get("bullets", [])
    nodes = visual_spec.get("nodes", [])

    # Extract source badge if available
    source_refs = scene_data.get("source_refs", [])
    badge = None
    if source_refs:
        first_ref = source_refs[0]
        if isinstance(first_ref, dict):
            if first_ref.get("page_number"):
                badge = f"Page {first_ref['page_number']}"
            elif first_ref.get("slide_number"):
                badge = f"Slide {first_ref['slide_number']}"

    if diagram_type == "flow" and nodes:
        img = render_diagram_flow_frame(title=title, nodes=nodes, width=width, height=height, style=style)
    else:
        if not bullets and scene_data.get("narration"):
            bullets = [s.strip() for s in scene_data["narration"].split(".") if len(s.strip()) > 10][:4]
        img = render_concept_card_frame(title=title, bullets=bullets, caption=scene_data.get("caption", ""), citation_badge=badge, width=width, height=height, style=style)

    img.save(output_path, "PNG")
    return output_path
