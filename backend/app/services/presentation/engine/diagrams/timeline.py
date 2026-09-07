"""
Deterministic Diagram Renderer — Milestone Timeline
====================================================
Renders horizontal chronological progressions with milestone nodes.
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from app.services.presentation_engine.tokens import ThemeColors, Typography
from app.services.presentation_engine.renderers.base import add_filled_rect, add_text_box


def render_timeline_diagram(
    slide: Slide,
    milestones: list,
    left: Emu,
    top: Emu,
    width: Emu,
    height: Emu,
    theme: ThemeColors,
) -> None:
    """Render a clean horizontal milestone timeline."""
    if not milestones:
        return

    n = min(len(milestones), 5)
    gutter = Inches(0.2)
    card_width = (width - (gutter * (n - 1))) / n

    # Central timeline axis line
    axis_y = top + Inches(0.4)
    add_filled_rect(
        slide,
        left, axis_y, width, Inches(0.04),
        fill_color=theme.primary_light,
    )

    for i in range(n):
        m = milestones[i]
        date_str = str(m.get("date", m.get("year", f"Phase {i+1}")))
        label = m.get("label", m.get("title", ""))
        detail = m.get("detail", "")
        cur_left = left + i * (card_width + gutter)

        # Milestone badge (with sequence number)
        dot_size = Inches(0.28)
        dot_x = cur_left + (card_width / 2) - (dot_size / 2)
        dot_y = axis_y - (dot_size / 2) + Inches(0.02)
        add_filled_rect(
            slide,
            dot_x, dot_y, dot_size, dot_size,
            fill_color=theme.primary,
            corner_radius=Inches(0.14),
        )
        add_text_box(
            slide,
            str(i + 1),
            dot_x, dot_y, dot_size, dot_size,
            token=Typography.BADGE,
            color=theme.text_on_dark,
            alignment=PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.MIDDLE,
        )

        # Milestone card below axis
        card_top = top + Inches(0.8)
        card_h = height - Inches(0.9)
        add_filled_rect(
            slide,
            cur_left, card_top, card_width, card_h,
            fill_color=theme.surface,
            border_color=theme.border,
            corner_radius=Inches(0.1),
        )

        # Date header
        add_text_box(
            slide,
            date_str,
            cur_left + Inches(0.1), card_top + Inches(0.1), card_width - Inches(0.2), Inches(0.3),
            token=Typography.BADGE,
            color=theme.primary,
            alignment=PP_ALIGN.CENTER,
        )

        # Milestone title
        if label:
            add_text_box(
                slide,
                label,
                cur_left + Inches(0.1), card_top + Inches(0.45), card_width - Inches(0.2), Inches(0.5),
                token=Typography.SLIDE_SUBTITLE,
                color=theme.text,
                alignment=PP_ALIGN.CENTER,
                word_wrap=True,
            )

        # Detail text
        if detail:
            add_text_box(
                slide,
                detail,
                cur_left + Inches(0.1), card_top + Inches(1.0), card_width - Inches(0.2), card_h - Inches(1.1),
                token=Typography.CAPTION,
                color=theme.text_muted,
                word_wrap=True,
            )
