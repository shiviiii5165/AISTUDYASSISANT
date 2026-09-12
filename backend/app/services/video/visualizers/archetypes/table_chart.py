"""
Table & Structured Data Visualizer Archetype
============================================
Renders relational database tables, attribute matrices, and marketing funnel stages
(e.g., DBMS Normalization decomposition, Marketing Funnel progression).
"""
from typing import List
from PIL import ImageDraw
from ..base import BaseVisualizer, PALETTE
from ...schemas import SceneSpec


class TableChartVisualizer(BaseVisualizer):
    """Renders TABLE and CHART archetypes."""

    @classmethod
    def render_scene(cls, scene: SceneSpec, output_path: str, style: str = "academic", progress: float = 1.0) -> str:
        img, draw = cls.create_canvas(
            title=scene.visual_spec.title or scene.caption,
            subtitle=scene.caption,
            tag="DATA TABLE"
        )

        headers = scene.visual_spec.table_headers or ["Attribute / Key", "Form 1 (1NF)", "Form 2 (2NF)", "Form 3 (3NF)"]
        rows = scene.visual_spec.table_rows or [
            ["Candidate Keys", "Atomic", "Full Key Only", "Non-transitive"],
            ["Dependencies", "Any", "Partial Removed", "Transitive Removed"],
            ["Integrity Risk", "High Redundancy", "Moderate Risk", "Lossless / Normal"]
        ]

        # Table dimensions
        start_x = 80
        total_w = cls.WIDTH - 160
        start_y = 190
        row_h = 60
        n_cols = len(headers)
        col_w = total_w // max(1, n_cols)

        font_th = cls.get_font(18, bold=True)
        font_td = cls.get_font(16, bold=False)

        # Header Row
        draw.rounded_rectangle([start_x, start_y, start_x + total_w, start_y + row_h], radius=10, fill=(38, 52, 75), outline=PALETTE["primary"], width=2)
        for c_idx, h in enumerate(headers):
            hx = start_x + c_idx * col_w + 20
            draw.text((hx, start_y + 18), str(h)[:20], fill=PALETTE["primary"], font=font_th)

        # Data Rows
        for r_idx, row in enumerate(rows[:6]):
            ry = start_y + (r_idx + 1) * (row_h + 10)
            row_bg = PALETTE["card_bg"] if r_idx % 2 == 0 else (24, 34, 50)
            draw.rounded_rectangle([start_x, ry, start_x + total_w, ry + row_h], radius=8, fill=row_bg, outline=PALETTE["card_border"], width=1)

            for c_idx, cell_val in enumerate(row[:n_cols]):
                cx = start_x + c_idx * col_w + 20
                draw.text((cx, ry + 18), str(cell_val)[:22], fill=PALETTE["text_primary"], font=font_td)

        img.save(output_path, "PNG")
        return output_path
