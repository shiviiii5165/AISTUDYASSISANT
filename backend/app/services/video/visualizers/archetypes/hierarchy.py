"""
Hierarchy & Architecture Visualizer Archetype
=============================================
Renders tree structures, system architectures, classification taxonomies,
and organizational hierarchies with parent-child connection lines.
"""
from typing import List, Tuple
from PIL import ImageDraw
from ..base import BaseVisualizer, PALETTE
from ...schemas import SceneSpec


class HierarchyVisualizer(BaseVisualizer):
    """Renders HIERARCHY and SYSTEM_ARCHITECTURE."""

    @classmethod
    def render_scene(cls, scene: SceneSpec, output_path: str, style: str = "academic", progress: float = 1.0) -> str:
        img, draw = cls.create_canvas(
            title=scene.visual_spec.title or scene.caption,
            subtitle=scene.caption,
            tag="HIERARCHY"
        )

        nodes = scene.visual_spec.nodes or [scene.visual_spec.title or "Root System", "Component A", "Component B", "Component C"]
        font_node = cls.get_font(18, bold=True)
        font_sub = cls.get_font(14, bold=False)

        # Root Node (Top Center)
        root_w = 260
        root_h = 70
        root_x1 = (cls.WIDTH - root_w) // 2
        root_y1 = 180
        root_x2 = root_x1 + root_w
        root_y2 = root_y1 + root_h

        draw.rounded_rectangle([root_x1, root_y1, root_x2, root_y2], radius=10, fill=PALETTE["card_bg"], outline=PALETTE["primary"], width=2)
        draw.text((root_x1 + 20, root_y1 + 22), str(nodes[0])[:22], fill=PALETTE["primary"], font=font_node)

        # Child Nodes (Level 2)
        children = nodes[1:5] if len(nodes) > 1 else ["Child 1", "Child 2", "Child 3"]
        n_children = len(children)
        child_w = 210
        child_h = 90
        gap = 40
        total_w = (n_children * child_w) + ((n_children - 1) * gap)
        start_x = (cls.WIDTH - total_w) // 2
        child_y1 = 360
        child_y2 = child_y1 + child_h

        root_bottom_center = ((root_x1 + root_x2) // 2, root_y2)

        for idx, child_name in enumerate(children):
            cx1 = start_x + idx * (child_w + gap)
            cx2 = cx1 + child_w
            child_top_center = ((cx1 + cx2) // 2, child_y1)

            # Connector line
            draw.line([root_bottom_center, child_top_center], fill=PALETTE["primary"], width=2)

            # Child box
            draw.rounded_rectangle([cx1, child_y1, cx2, child_y2], radius=10, fill=PALETTE["card_bg"], outline=PALETTE["card_border"], width=2)
            draw.text((cx1 + 15, child_y1 + 20), str(child_name)[:20], fill=PALETTE["text_primary"], font=font_node)
            draw.text((cx1 + 15, child_y1 + 52), "Subsystem Module", fill=PALETTE["text_muted"], font=font_sub)

        img.save(output_path, "PNG")
        return output_path
