"""
Deterministic Diagram Renderer — Side-by-Side Comparison
=========================================================
Renders structured comparison columns (e.g. Approach A vs Approach B, Pros vs Cons).
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from app.services.presentation_engine.tokens import ThemeColors, Typography
from app.services.presentation_engine.renderers.base import add_filled_rect, add_text_box, add_bullet_list


def render_comparison_diagram(
    slide: Slide,
    columns: list,
    left: Emu,
    top: Emu,
    width: Emu,
    height: Emu,
    theme: ThemeColors,
) -> None:
    """Render a clean 2-column or 3-column side-by-side comparison matrix."""
    if not columns:
        return

    n = min(len(columns), 3)
    gutter = Inches(0.25)
    col_width = (width - (gutter * (n - 1))) / n

    for i in range(n):
        col_data = columns[i]
        heading = col_data.get("heading", f"Option {chr(65+i)}")
        points = col_data.get("points", [])
        cur_left = left + i * (col_width + gutter)

        # Highlight first column differently if 2 columns (e.g. A vs B)
        header_fill = theme.primary if i == 0 else theme.surface_alt
        header_text_color = theme.text_on_dark if i == 0 else theme.primary

        # Card container
        add_filled_rect(
            slide,
            cur_left, top, col_width, height,
            fill_color=theme.surface,
            border_color=theme.primary if i == 0 else theme.border,
            corner_radius=Inches(0.12),
        )

        # Column Header banner
        header_h = Inches(0.65)
        add_filled_rect(
            slide,
            cur_left, top, col_width, header_h,
            fill_color=header_fill,
            corner_radius=Inches(0.12),
        )
        add_text_box(
            slide,
            heading,
            cur_left + Inches(0.15), top + Inches(0.1), col_width - Inches(0.3), header_h - Inches(0.2),
            token=Typography.SLIDE_SUBTITLE,
            color=header_text_color,
            alignment=PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.MIDDLE,
            word_wrap=True,
        )

        # Content points
        body_top = top + header_h + Inches(0.2)
        body_h = height - header_h - Inches(0.3)

        clean_points = [str(p).strip() for p in points[:5] if str(p).strip()]
        if clean_points:
            add_bullet_list(
                slide,
                clean_points,
                cur_left + Inches(0.2), body_top, col_width - Inches(0.4), body_h,
                token=Typography.BULLET,
                text_color=theme.text,
                accent_color=theme.primary,
            )
