"""
Deterministic Diagram Renderer — Process Flow
==============================================
Renders horizontal/grid sequence steps with numbered badges and directional connectors.
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from app.services.presentation_engine.tokens import ThemeColors, Typography
from app.services.presentation_engine.renderers.base import add_filled_rect, add_text_box


def render_flow_diagram(
    slide: Slide,
    steps: list,
    left: Emu,
    top: Emu,
    width: Emu,
    height: Emu,
    theme: ThemeColors,
) -> None:
    """Render a step-by-step process flow with connecting arrows."""
    if not steps:
        return

    n = min(len(steps), 5)
    gutter = Inches(0.2)
    step_width = (width - (gutter * (n - 1))) / n

    for i in range(n):
        step_data = steps[i]
        title = step_data.get("title", f"Step {i+1}")
        detail = step_data.get("detail", "")
        cur_left = left + i * (step_width + gutter)

        # Card container
        add_filled_rect(
            slide,
            cur_left, top, step_width, height,
            fill_color=theme.surface,
            border_color=theme.border,
            corner_radius=Inches(0.12),
        )

        # Step Number Badge
        badge_size = Inches(0.4)
        add_filled_rect(
            slide,
            cur_left + Inches(0.15), top + Inches(0.15), badge_size, badge_size,
            fill_color=theme.primary_light,
            border_color=theme.primary,
            corner_radius=Inches(0.2),
        )
        add_text_box(
            slide,
            str(i + 1),
            cur_left + Inches(0.15), top + Inches(0.15), badge_size, badge_size,
            token=Typography.BADGE,
            color=theme.primary,
            alignment=PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.MIDDLE,
        )

        # Step Title
        add_text_box(
            slide,
            title,
            cur_left + Inches(0.15), top + Inches(0.65), step_width - Inches(0.3), Inches(0.6),
            token=Typography.SLIDE_SUBTITLE,
            color=theme.text,
            word_wrap=True,
        )

        # Step Detail
        if detail:
            add_text_box(
                slide,
                detail,
                cur_left + Inches(0.15), top + Inches(1.3), step_width - Inches(0.3), height - Inches(1.45),
                token=Typography.CAPTION,
                color=theme.text_muted,
                word_wrap=True,
            )

        # Connector arrow to next step
        if i < n - 1:
            arrow_left = cur_left + step_width + Inches(0.04)
            arrow_top = top + (height / 2) - Inches(0.15)
            add_text_box(
                slide,
                "→",
                arrow_left, arrow_top, gutter, Inches(0.3),
                token=Typography.SLIDE_SUBTITLE,
                color=theme.primary,
                alignment=PP_ALIGN.CENTER,
                anchor=MSO_ANCHOR.MIDDLE,
            )
