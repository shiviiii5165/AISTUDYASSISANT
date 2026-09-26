"""
TeachGenie Renderer — Comparison Table Component
================================================
Renders a genuine python-pptx Table shape with N rows and 2–4 columns.
Features shaded header row, subtle alternating row fills, and formatted cell text.
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from .. import SlideContent, ThemeColors
from ..tokens import (
    MARGIN_LEFT, CONTENT_WIDTH, ZONE_TITLE_TOP, ZONE_TITLE_HEIGHT,
    ZONE_CONTENT_TOP, Typography
)
from .base import (
    add_filled_rect, add_text_box, add_accent_bar, add_footer, add_speaker_notes
)

def render_comparison_table(
    slide: Slide,
    content: SlideContent,
    theme: ThemeColors,
    **kw
) -> None:
    """Render a structured comparison table with genuine python-pptx Table shape."""
    from ..tokens import SLIDE_WIDTH, SLIDE_HEIGHT
    add_filled_rect(slide, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, theme.background)

    # Accent bar & Title
    add_accent_bar(
        slide, MARGIN_LEFT - Inches(0.15), ZONE_TITLE_TOP + Inches(0.1),
        width=Inches(0.06), height=Inches(0.55),
        color=theme.primary,
    )
    add_text_box(
        slide, content.title,
        MARGIN_LEFT, ZONE_TITLE_TOP,
        CONTENT_WIDTH, ZONE_TITLE_HEIGHT,
        token=Typography.SLIDE_TITLE,
        color=theme.text,
    )

    content_top = ZONE_CONTENT_TOP + Inches(0.15)

    # Determine columns and rows
    headers = []
    rows_data = []

    if content.columns and len(content.columns) >= 2:
        col_points_max = max((len(col.points) for col in content.columns[:4]), default=0)
        if col_points_max > 0:
            headers = [col.heading or f"Option {i+1}" for i, col in enumerate(content.columns[:4])]
            for r_idx in range(col_points_max):
                row = []
                for col in content.columns[:4]:
                    pt = col.points[r_idx] if r_idx < len(col.points) else ""
                    row.append(pt)
                rows_data.append(row)
    if not rows_data:
        raise ValueError("Comparison table requires at least one data row; automatic fabrication from unrelated bullets is disallowed")

    num_cols = len(headers)
    num_rows = len(rows_data) + 1  # header + data rows

    col_w = CONTENT_WIDTH // num_cols
    total_table_w = col_w * num_cols
    row_h = Inches(0.55)
    total_table_h = row_h * num_rows

    table_shape = slide.shapes.add_table(num_rows, num_cols, MARGIN_LEFT, content_top, total_table_w, total_table_h)
    table = table_shape.table

    # Format Headers
    for c_idx, h_text in enumerate(headers):
        cell = table.cell(0, c_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = theme.primary
        tf = cell.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = h_text.upper()
        p.font.name = Typography.BADGE.font_name
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = theme.text_on_dark
        p.alignment = PP_ALIGN.CENTER

    # Format Data Rows
    for r_idx, row in enumerate(rows_data):
        is_even = (r_idx % 2 == 0)
        row_bg = theme.surface if is_even else theme.surface_alt
        for c_idx, val in enumerate(row):
            cell = table.cell(r_idx + 1, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = row_bg
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = str(val)
            p.font.name = Typography.BODY.font_name
            p.font.size = Pt(13)
            p.font.color.rgb = theme.text
            p.alignment = PP_ALIGN.LEFT if c_idx == 0 else PP_ALIGN.CENTER

    add_footer(slide, kw.get("slide_number", 1), kw.get("total_slides", 1), theme, section_name=kw.get("deck_title", ""))
    add_speaker_notes(slide, content.speaker_note)
