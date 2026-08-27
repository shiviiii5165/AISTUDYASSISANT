"""
Deterministic Diagram Renderer — Layered Architecture
======================================================
Renders stacked architectural tiers with component pill badges.
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from app.services.presentation_engine.tokens import ThemeColors, Typography
from app.services.presentation_engine.renderers.base import add_filled_rect, add_text_box


def render_architecture_diagram(
    slide: Slide,
    layers: list,
    left: Emu,
    top: Emu,
    width: Emu,
    height: Emu,
    theme: ThemeColors,
) -> None:
    """Render a stacked tier architecture diagram."""
    if not layers:
        return

    n = min(len(layers), 5)
    gutter = Inches(0.12)
    layer_height = (height - (gutter * (n - 1))) / n

    for i in range(n):
        layer_data = layers[i]
        layer_name = layer_data.get("name", layer_data.get("title", f"Layer {i+1}"))
        components = layer_data.get("components", layer_data.get("items", []))
        cur_top = top + i * (layer_height + gutter)

        # Layer container background
        is_even = (i % 2 == 0)
        bg_fill = theme.surface_alt if is_even else theme.surface
        add_filled_rect(
            slide,
            left, cur_top, width, layer_height,
            fill_color=bg_fill,
            border_color=theme.border,
            corner_radius=Inches(0.08),
        )

        # Left label strip
        label_width = Inches(2.2)
        add_filled_rect(
            slide,
            left, cur_top, label_width, layer_height,
            fill_color=theme.primary_light,
            border_color=theme.border,
            corner_radius=Inches(0.08),
        )
        add_text_box(
            slide,
            layer_name,
            left + Inches(0.1), cur_top + Inches(0.1), label_width - Inches(0.2), layer_height - Inches(0.2),
            token=Typography.BADGE,
            color=theme.primary,
            alignment=PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.MIDDLE,
            word_wrap=True,
        )

        # Component badges
        comp_area_left = left + label_width + Inches(0.2)
        comp_area_width = width - label_width - Inches(0.3)
        
        if components:
            k = min(len(components), 4)
            comp_w = (comp_area_width - (Inches(0.1) * (k - 1))) / k
            comp_h = layer_height - Inches(0.2)
            comp_top = cur_top + Inches(0.1)

            for j in range(k):
                c_name = str(components[j])
                c_left = comp_area_left + j * (comp_w + Inches(0.1))
                add_filled_rect(
                    slide,
                    c_left, comp_top, comp_w, comp_h,
                    fill_color=theme.surface,
                    border_color=theme.border,
                    corner_radius=Inches(0.06),
                )
                add_text_box(
                    slide,
                    c_name,
                    c_left + Inches(0.05), comp_top + Inches(0.05), comp_w - Inches(0.1), comp_h - Inches(0.1),
                    token=Typography.CAPTION,
                    color=theme.text,
                    alignment=PP_ALIGN.CENTER,
                    anchor=MSO_ANCHOR.MIDDLE,
                    word_wrap=True,
                )
