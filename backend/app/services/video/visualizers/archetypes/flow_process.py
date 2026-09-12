"""
Flow & Process Visualizer Archetype
===================================
Renders multi-step workflows, algorithms, and scientific processes
(e.g., Photosynthesis, Compilation Stages, State Machines).
Features sequential step cards, animated pulse along active stage, and arrow connectors.
"""
from typing import List, Tuple
from PIL import ImageDraw, Image
from ..base import BaseVisualizer, PALETTE
from ...schemas import SceneSpec


class FlowProcessVisualizer(BaseVisualizer):
    """Renders PROCESS_FLOW, SCIENTIFIC_PROCESS, STEP_SEQUENCE, and ALGORITHM_TRACE."""

    @classmethod
    def render_scene(cls, scene: SceneSpec, output_path: str, style: str = "academic", progress: float = 1.0) -> str:
        img, draw = cls.create_canvas(
            title=scene.visual_spec.title or scene.caption,
            subtitle=scene.caption,
            tag="PROCESS FLOW"
        )

        steps = scene.visual_spec.steps or scene.visual_spec.bullets or ["Step 1: Input", "Step 2: Process", "Step 3: Output"]
        n_steps = min(5, len(steps))

        # Calculate horizontal positions
        card_width = 200
        card_height = 240
        spacing = 40
        total_w = (n_steps * card_width) + ((n_steps - 1) * spacing)
        start_x = (cls.WIDTH - total_w) // 2
        card_y = 230

        active_idx = min(n_steps - 1, int(progress * n_steps))

        for i in range(n_steps):
            x1 = start_x + i * (card_width + spacing)
            x2 = x1 + card_width
            y1 = card_y
            y2 = y1 + card_height

            is_active = (i == active_idx)
            is_past = (i < active_idx)

            card_border = PALETTE["primary"] if is_active else (PALETTE["accent_green"] if is_past else PALETTE["card_border"])
            border_w = 3 if is_active else 2
            bg_fill = (38, 52, 75) if is_active else PALETTE["card_bg"]

            # Draw card
            draw.rounded_rectangle([x1, y1, x2, y2], radius=12, fill=bg_fill, outline=card_border, width=border_w)

            # Step number badge
            badge_color = PALETTE["primary"] if is_active else (PALETTE["accent_green"] if is_past else PALETTE["text_muted"])
            draw.rounded_rectangle([x1 + 15, y1 + 15, x1 + 55, y1 + 45], radius=6, fill=badge_color)
            font_badge = cls.get_font(16, bold=True)
            draw.text((x1 + 25, y1 + 20), str(i + 1), fill=(15, 23, 42), font=font_badge)

            # Step text
            font_text = cls.get_font(16, bold=False)
            step_text = steps[i]
            # Wrap text inside card
            words = step_text.split()
            lines = []
            curr = ""
            for w in words:
                test = f"{curr} {w}".strip()
                if len(test) < 18:
                    curr = test
                else:
                    lines.append(curr)
                    curr = w
            if curr:
                lines.append(curr)

            ty = y1 + 65
            for line in lines[:6]:
                draw.text((x1 + 15, ty), line, fill=PALETTE["text_primary"], font=font_text)
                ty += 24

            # Draw connector arrow to next card
            if i < n_steps - 1:
                arrow_start = (x2 + 5, card_y + card_height // 2)
                arrow_end = (x2 + spacing - 5, card_y + card_height // 2)
                arrow_color = PALETTE["accent_green"] if is_past else PALETTE["primary"]
                cls.draw_arrow(draw, arrow_start, arrow_end, color=arrow_color, width=3)

        img.save(output_path, "PNG")
        return output_path

    @classmethod
    def _render_animation_frame(cls, scene: SceneSpec, progress: float, output_path: str):
        cls.render_scene(scene, output_path, progress=progress)
