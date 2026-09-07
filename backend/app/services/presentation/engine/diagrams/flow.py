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

    # Compute dynamic card height from content volume across all steps
    max_detail_chars = max((len(s.get("detail", "")) for s in steps[:n]), default=0)
    max_title_chars = max((len(s.get("title", "")) for s in steps[:n]), default=0)
    
    # Estimate vertical content requirement
    est_content_h = Inches(1.2)
    if max_title_chars > 20:
        est_content_h += Inches(0.3)
    if max_detail_chars > 60:
        est_content_h += Inches(0.9)
    elif max_detail_chars > 20:
        est_content_h += Inches(0.5)

    card_height = max(Inches(2.2), min(est_content_h + Inches(0.4), height - Inches(0.4)))
    card_top = top + max(Inches(0.1), (height - card_height) / 2)

    for i in range(n):
        step_data = steps[i]
        title = step_data.get("title", f"Step {i+1}")
        detail = step_data.get("detail", "")
        cur_left = left + i * (step_width + gutter)

        # Card container with dynamic fit
        add_filled_rect(
            slide,
            cur_left, card_top, step_width, card_height,
            fill_color=theme.surface,
            border_color=theme.border,
            corner_radius=Inches(0.12),
        )

        # Step Number Badge
        badge_size = Inches(0.38)
        badge_x = cur_left + Inches(0.15)
        badge_y = card_top + Inches(0.15)
        add_filled_rect(
            slide,
            badge_x, badge_y, badge_size, badge_size,
            fill_color=theme.primary_light,
            border_color=theme.primary,
            corner_radius=Inches(0.19),
        )
        add_text_box(
            slide,
            str(i + 1),
            badge_x, badge_y, badge_size, badge_size,
            token=Typography.BADGE,
            color=theme.primary,
            alignment=PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.MIDDLE,
        )

        # Step Title
        title_top = card_top + Inches(0.6)
        title_h = Inches(0.5) if max_title_chars <= 25 else Inches(0.7)
        add_text_box(
            slide,
            title,
            cur_left + Inches(0.15), title_top, step_width - Inches(0.3), title_h,
            token=Typography.SLIDE_SUBTITLE,
            color=theme.text,
            word_wrap=True,
        )

        # Step Detail
        if detail:
            detail_top = title_top + title_h + Inches(0.05)
            avail_detail_h = max(Inches(0.5), card_top + card_height - detail_top - Inches(0.12))
            add_text_box(
                slide,
                detail,
                cur_left + Inches(0.15), detail_top, step_width - Inches(0.3), avail_detail_h,
                token=Typography.CAPTION,
                color=theme.text_muted,
                word_wrap=True,
            )

        # Connector arrow to next step
        if i < n - 1:
            arrow_left = cur_left + step_width + Inches(0.02)
            arrow_top = card_top + (card_height / 2) - Inches(0.15)
            add_text_box(
                slide,
                "→",
                arrow_left, arrow_top, gutter, Inches(0.3),
                token=Typography.SLIDE_SUBTITLE,
                color=theme.primary,
                alignment=PP_ALIGN.CENTER,
                anchor=MSO_ANCHOR.MIDDLE,
            )
