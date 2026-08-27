"""
SVG Educational Diagram Generator (Zero LLM Tokens)
===================================================
Generates crisp, high-resolution SVG markup for process flowcharts,
architectural stacks, timelines, comparisons, and formulas.
"""
from typing import List, Dict, Any, Optional
from ..design_tokens import get_design_tokens


def render_flowchart_svg(
    title: str,
    nodes: List[str],
    style: str = "academic",
    width: int = 1280,
    height: int = 720,
) -> str:
    """Generates a responsive SVG process flowchart with directional arrows."""
    tokens = get_design_tokens(style)
    node_count = max(2, min(5, len(nodes)))
    step_width = (width - 160) // node_count
    node_w = int(step_width * 0.75)
    node_h = 110
    y_pos = (height // 2) - 40

    svg_elements = []
    
    # Title & Header
    svg_elements.append(f'<text x="80" y="70" font-family="{tokens["font_heading"]}" font-size="34" font-weight="bold" fill="{tokens["primary"]}">{title}</text>')
    
    # Nodes and Arrows
    for i, node_text in enumerate(nodes[:node_count]):
        x_pos = 80 + (i * step_width)
        
        # Node Box
        svg_elements.append(
            f'<rect x="{x_pos}" y="{y_pos}" width="{node_w}" height="{node_h}" rx="{tokens["border_radius"]}" '
            f'fill="{tokens["card_bg"]}" stroke="{tokens["primary"]}" stroke-width="3" filter="drop-shadow(0 4px 6px rgba(0,0,0,0.05))" />'
        )
        
        # Step Number Badge
        badge_w, badge_h = 32, 26
        svg_elements.append(
            f'<rect x="{x_pos + 12}" y="{y_pos + 12}" width="{badge_w}" height="{badge_h}" rx="6" fill="{tokens["accent"]}" />'
            f'<text x="{x_pos + 22}" y="{y_pos + 30}" font-family="{tokens["font_heading"]}" font-size="14" font-weight="bold" fill="{tokens["primary"]}">{i+1}</text>'
        )

        # Node Label
        clean_text = node_text[:28].replace("&", "&amp;").replace("<", "&lt;")
        svg_elements.append(
            f'<text x="{x_pos + 16}" y="{y_pos + 68}" font-family="{tokens["font_body"]}" font-size="18" font-weight="600" fill="{tokens["text_dark"]}">{clean_text}</text>'
        )

        # Directional Arrow
        if i < node_count - 1:
            arrow_start_x = x_pos + node_w + 12
            arrow_end_x = x_pos + step_width - 12
            arrow_y = y_pos + (node_h // 2)
            svg_elements.append(
                f'<line x1="{arrow_start_x}" y1="{arrow_y}" x2="{arrow_end_x}" y2="{arrow_y}" stroke="{tokens["primary"]}" stroke-width="4" />'
                f'<polygon points="{arrow_end_x},{arrow_y} {arrow_end_x - 12},{arrow_y - 7} {arrow_end_x - 12},{arrow_y + 7}" fill="{tokens["primary"]}" />'
            )

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <rect width="100%" height="100%" fill="{tokens['bg_color']}" />
  <rect width="100%" height="8" fill="{tokens['primary']}" />
  {''.join(svg_elements)}
</svg>"""
    return svg_content


def render_architecture_stack_svg(
    title: str,
    layers: List[str],
    style: str = "academic",
    width: int = 1280,
    height: int = 720,
) -> str:
    """Generates a layered architecture stack diagram."""
    tokens = get_design_tokens(style)
    layer_count = max(2, min(5, len(layers)))
    layer_w = width - 360
    layer_h = 75
    y_start = 140

    svg_elements = [
        f'<text x="80" y="70" font-family="{tokens["font_heading"]}" font-size="34" font-weight="bold" fill="{tokens["primary"]}">{title}</text>'
    ]

    for i, layer_text in enumerate(layers[:layer_count]):
        y_pos = y_start + (i * 95)
        clean_text = layer_text.replace("&", "&amp;").replace("<", "&lt;")
        svg_elements.append(
            f'<rect x="180" y="{y_pos}" width="{layer_w}" height="{layer_h}" rx="{tokens["border_radius"]}" '
            f'fill="{tokens["card_bg"]}" stroke="{tokens["border"]}" stroke-width="2" />'
            f'<rect x="180" y="{y_pos}" width="12" height="{layer_h}" rx="4" fill="{tokens["primary"]}" />'
            f'<text x="210" y="{y_pos + 44}" font-family="{tokens["font_body"]}" font-size="22" font-weight="bold" fill="{tokens["text_dark"]}">{clean_text}</text>'
        )

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <rect width="100%" height="100%" fill="{tokens['bg_color']}" />
  <rect width="100%" height="8" fill="{tokens['primary']}" />
  {''.join(svg_elements)}
</svg>"""
    return svg_content
