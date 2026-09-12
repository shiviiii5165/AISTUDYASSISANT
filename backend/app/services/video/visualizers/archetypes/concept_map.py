"""
Concept Map & Network Visualizer Archetype
==========================================
Renders network graphs, relational concept maps, and entity-relationship links.
"""
import math
from typing import List, Tuple
from PIL import ImageDraw
from ..base import BaseVisualizer, PALETTE
from ...schemas import SceneSpec


class ConceptMapVisualizer(BaseVisualizer):
    """Renders CONCEPT_MAP and NETWORK."""

    @classmethod
    def render_scene(cls, scene: SceneSpec, output_path: str, style: str = "academic", progress: float = 1.0) -> str:
        img, draw = cls.create_canvas(
            title=scene.visual_spec.title or scene.caption,
            subtitle=scene.caption,
            tag="CONCEPT MAP"
        )

        nodes = scene.visual_spec.nodes or [scene.visual_spec.title or "Central Concept", "Principle A", "Principle B", "Principle C", "Principle D"]
        center_node = nodes[0]
        satellite_nodes = nodes[1:6]

        center_x = cls.WIDTH // 2
        center_y = cls.HEIGHT // 2 + 30
        center_r = 75

        font_center = cls.get_font(18, bold=True)
        font_sat = cls.get_font(15, bold=False)

        # Satellite positions in circular orbit
        n_sat = len(satellite_nodes)
        orbit_rx = 340
        orbit_ry = 180

        for i, sat in enumerate(satellite_nodes):
            angle = (2 * math.pi / max(1, n_sat)) * i - (math.pi / 2)
            sx = int(center_x + orbit_rx * math.cos(angle))
            sy = int(center_y + orbit_ry * math.sin(angle))

            # Connecting vector arrow
            cls.draw_arrow(draw, (center_x, center_y), (sx, sy), color=PALETTE["card_border"], width=2)

            # Satellite Box
            sw, sh = 180, 60
            draw.rounded_rectangle([sx - sw//2, sy - sh//2, sx + sw//2, sy + sh//2], radius=8, fill=PALETTE["card_bg"], outline=PALETTE["primary"], width=2)
            draw.text((sx - sw//2 + 15, sy - 10), str(sat)[:18], fill=PALETTE["text_primary"], font=font_sat)

        # Central Hub Node
        draw.ellipse([center_x - center_r, center_y - center_r, center_x + center_r, center_y + center_r], fill=PALETTE["card_bg"], outline=PALETTE["primary"], width=4)
        draw.text((center_x - 55, center_y - 12), str(center_node)[:16], fill=PALETTE["primary"], font=font_center)

        img.save(output_path, "PNG")
        return output_path
