"""
Mathematical Derivation & Formula Visualizer Archetype
======================================================
Renders mathematical derivations, stepwise symbolic transformations,
and highlighted operational identities with LaTeX-inspired typography.
"""
from typing import List
from PIL import ImageDraw
from ..base import BaseVisualizer, PALETTE
from ...schemas import SceneSpec, EquationStep


class EquationVisualizer(BaseVisualizer):
    """Renders MATHEMATICAL_DERIVATION and FORMULA_VISUALIZATION."""

    @classmethod
    def render_scene(cls, scene: SceneSpec, output_path: str, style: str = "academic", progress: float = 1.0) -> str:
        img, draw = cls.create_canvas(
            title=scene.visual_spec.title or scene.caption,
            subtitle=scene.caption,
            tag="DERIVATION"
        )

        steps: List[EquationStep] = scene.visual_spec.equations
        if not steps:
            # Fallback default equations
            steps = [
                EquationStep(equation="Step 1: State Fundamental Identity", explanation="Initial definition"),
                EquationStep(equation="Step 2: Apply Differentiation / Substitution", explanation="Operational change"),
                EquationStep(equation="Step 3: Evaluate Final Simplified Form", explanation="Closed form result")
            ]

        n_steps = min(4, len(steps))
        step_y = 180
        box_w = cls.WIDTH - 160
        box_h = 105
        spacing = 30

        font_eq = cls.get_font(24, bold=True)
        font_exp = cls.get_font(15, bold=False)

        for i, step in enumerate(steps[:n_steps]):
            y1 = step_y + i * (box_h + spacing)
            y2 = y1 + box_h
            x1 = 80
            x2 = x1 + box_w

            is_final = (i == n_steps - 1)
            border_color = PALETTE["accent_green"] if is_final else PALETTE["primary"]
            border_w = 3 if is_final else 2

            # Equation Card Box
            draw.rounded_rectangle([x1, y1, x2, y2], radius=12, fill=PALETTE["card_bg"], outline=border_color, width=border_w)

            # Step Number
            draw.rounded_rectangle([x1 + 15, y1 + 15, x1 + 50, y1 + 45], radius=6, fill=border_color)
            font_num = cls.get_font(16, bold=True)
            draw.text((x1 + 25, y1 + 20), str(i + 1), fill=(15, 23, 42), font=font_num)

            # Equation String (Centered/Bold)
            draw.text((x1 + 75, y1 + 20), step.equation, fill=PALETTE["text_primary"], font=font_eq)

            # Explanation Subtitle
            if step.explanation:
                draw.text((x1 + 75, y1 + 65), f"-> {step.explanation}", fill=PALETTE["text_muted"], font=font_exp)

        img.save(output_path, "PNG")
        return output_path
