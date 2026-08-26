"""Architecture renderer — Multi-tier layered system diagram using native shapes."""
from pptx.slide import Slide
from pptx.util import Inches
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from .. import SlideContent, ThemeColors
from ..tokens import (
    SLIDE_WIDTH, SLIDE_HEIGHT, MARGIN_LEFT, CONTENT_WIDTH,
    ZONE_TITLE_TOP, ZONE_TITLE_HEIGHT, ZONE_CONTENT_TOP,
    Typography, grid_x, grid_width,
)
from .base import (
    add_filled_rect, add_text_box, add_accent_bar, add_card,
    add_footer, add_speaker_notes,
)


def render_architecture(slide: Slide, content: SlideContent, theme: ThemeColors, **kw) -> None:
    """Render a layered architecture diagram using native PowerPoint shapes."""
    add_filled_rect(slide, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, theme.background)

    # Title
    add_accent_bar(
        slide, MARGIN_LEFT - Inches(0.15), ZONE_TITLE_TOP + Inches(0.1),
        width=Inches(0.06), height=Inches(0.55), color=theme.primary,
    )
    add_text_box(
        slide, content.title, MARGIN_LEFT, ZONE_TITLE_TOP,
        CONTENT_WIDTH, ZONE_TITLE_HEIGHT,
        token=Typography.SLIDE_TITLE, color=theme.text,
    )

    layers = content.layers
    if not layers:
        # Fallback: create layers from body_bullets
        layers_data = []
        for i, bullet in enumerate(content.body_bullets[:5]):
            from .. import ArchitectureLayer
            layers_data.append(ArchitectureLayer(name=bullet, components=[]))
        layers = layers_data

    if not layers:
        return

    # Compute layout for architecture layers
    num_layers = min(len(layers), 5)
    layer_total_height = Inches(4.0)
    layer_gap = Inches(0.15)
    layer_height = (layer_total_height - (num_layers - 1) * layer_gap) / num_layers
    layer_width = grid_width(10)
    layer_left = grid_x(1)

    # Color progression: primary → secondary → accent → muted
    layer_colors = [
        theme.primary_light,
        theme.surface_alt,
        theme.surface,
        theme.surface_alt,
        theme.primary_light,
    ]
    text_colors = [
        theme.primary,
        theme.text,
        theme.text,
        theme.text,
        theme.primary,
    ]

    for i, layer in enumerate(layers[:num_layers]):
        y = ZONE_CONTENT_TOP + i * (layer_height + layer_gap)
        bg = layer_colors[i % len(layer_colors)]
        tc = text_colors[i % len(text_colors)]

        # Layer card
        add_card(slide, layer_left, y, layer_width, layer_height, fill_color=bg, border_color=theme.border)

        # Layer name
        add_text_box(
            slide, layer.name,
            layer_left + Inches(0.3), y + Inches(0.08),
            Inches(3.5), Inches(0.35),
            token=Typography.BULLET, color=tc,
        )

        # Component chips
        if layer.components:
            chip_left = layer_left + Inches(4.0)
            for j, comp in enumerate(layer.components[:4]):
                cw = Inches(2.2)
                cx = chip_left + j * (cw + Inches(0.15))
                if cx + cw > layer_left + layer_width:
                    break
                add_filled_rect(
                    slide, cx, y + Inches(0.08),
                    cw, Inches(0.3),
                    fill_color=theme.surface,
                    border_color=theme.border_light,
                    corner_radius=Inches(0.15),
                )
                add_text_box(
                    slide, comp,
                    cx, y + Inches(0.08),
                    cw, Inches(0.3),
                    token=Typography.CAPTION, color=theme.text_muted,
                    alignment=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
                )

        # Down arrow between layers (except last)
        if i < num_layers - 1:
            arrow_x = layer_left + layer_width / 2 - Inches(0.1)
            arrow_y = y + layer_height
            add_text_box(
                slide, "↓",
                arrow_x, arrow_y, Inches(0.3), layer_gap,
                token=Typography.BODY, color=theme.text_muted,
                alignment=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
            )

    add_footer(slide, kw.get("slide_number", 0), kw.get("total_slides", 0), theme)
    add_speaker_notes(slide, content.speaker_note)
