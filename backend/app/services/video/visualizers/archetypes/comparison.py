"""
Comparison Visualizer Archetype
===============================
Renders side-by-side comparative matrices, trade-off evaluations,
and Correct Approach vs Common Pitfall contrasts.
"""
from typing import List
from PIL import ImageDraw
from ..base import BaseVisualizer, PALETTE
from ...schemas import SceneSpec, ComparisonColumn


class ComparisonVisualizer(BaseVisualizer):
    """Renders COMPARISON archetype."""

    @classmethod
    def render_scene(cls, scene: SceneSpec, output_path: str, style: str = "academic", progress: float = 1.0) -> str:
        img, draw = cls.create_canvas(
            title=scene.visual_spec.title or scene.caption,
            subtitle=scene.caption,
            tag="COMPARISON"
        )

        cols: List[ComparisonColumn] = scene.visual_spec.comparisons
        if not cols:
            # Fallback two columns from bullets
            bullets = scene.visual_spec.bullets or ["Principle A", "Principle B"]
            mid = len(bullets) // 2 or 1
            cols = [
                ComparisonColumn(header="Approach A / Advantages", items=bullets[:mid], color_accent="#10B981"),
                ComparisonColumn(header="Approach B / Trade-offs", items=bullets[mid:], color_accent="#EF4444")
            ]

        n_cols = min(3, len(cols))
        margin_x = 80
        total_w = cls.WIDTH - (2 * margin_x)
        col_gap = 40
        col_w = (total_w - ((n_cols - 1) * col_gap)) // n_cols
        col_y1 = 180
        col_y2 = cls.HEIGHT - 80

        font_header = cls.get_font(22, bold=True)
        font_item = cls.get_font(16, bold=False)

        for i, col in enumerate(cols[:n_cols]):
            cx1 = margin_x + i * (col_w + col_gap)
            cx2 = cx1 + col_w

            accent = PALETTE["primary"] if not col.color_accent else (
                (16, 185, 129) if "green" in col.color_accent.lower() or "#10b981" in col.color_accent.lower()
                else (244, 63, 94)
            )

            # Container Box
            draw.rounded_rectangle([cx1, col_y1, cx2, col_y2], radius=14, fill=PALETTE["card_bg"], outline=accent, width=2)

            # Header Banner
            draw.rounded_rectangle([cx1, col_y1, cx2, col_y1 + 55], radius=14, fill=(38, 50, 72))
            draw.text((cx1 + 25, col_y1 + 16), col.header[:28], fill=accent, font=font_header)

            # Draw Items with checkmarks/crosses
            item_y = col_y1 + 85
            for idx, item in enumerate(col.items[:6]):
                # Small badge bullet
                draw.ellipse([cx1 + 25, item_y + 4, cx1 + 35, item_y + 14], fill=accent)
                # Text
                draw.text((cx1 + 50, item_y), item[:42], fill=PALETTE["text_primary"], font=font_item)
                item_y += 50

        img.save(output_path, "PNG")
        return output_path
