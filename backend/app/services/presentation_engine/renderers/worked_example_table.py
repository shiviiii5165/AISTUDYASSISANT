"""
TeachGenie Renderer — Worked Example Table Component
====================================================
Renders a compact 2-column table mapping computational steps / code lines
to their mathematical interpretation, variable state, or pedagogical meaning.
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from .. import SlideContent, ThemeColors
from ..tokens import (
    MARGIN_LEFT, CONTENT_WIDTH, ZONE_TITLE_TOP, ZONE_TITLE_HEIGHT,
    ZONE_CONTENT_TOP, Typography
)
from .base import (
    add_filled_rect, add_text_box, add_accent_bar, add_footer, add_speaker_notes
)

def render_worked_example_table(
    slide: Slide,
    content: SlideContent,
    theme: ThemeColors,
    **kw
) -> None:
    """Render a 2-column step-by-step worked example table."""
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

    # Parse rows: Step -> Explanation
    rows = []
    if content.body_bullets:
        for b in content.body_bullets[:6]:
            if "->" in b or "→" in b:
                delim = "->" if "->" in b else "→"
                parts = b.split(delim, 1)
                rows.append([parts[0].strip(), parts[1].strip()])
            elif ":" in b:
                parts = b.split(":", 1)
                rows.append([parts[0].strip(), parts[1].strip()])
            else:
                rows.append(["Step", b.strip()])
    else:
        rows = [
            ["Initialize State", "Set counter = 0, allocate buffer array"],
            ["Iterative Step", "Inspect next token and push to evaluation stack"],
            ["Terminal Condition", "Return top element when input stream terminates"]
        ]

    num_rows = len(rows) + 1
    num_cols = 2
    col_w0 = Inches(4.0)
    col_w1 = CONTENT_WIDTH - col_w0
    total_table_w = CONTENT_WIDTH
    row_h = Inches(0.58)
    total_table_h = row_h * num_rows

    table_shape = slide.shapes.add_table(num_rows, num_cols, MARGIN_LEFT, content_top, total_table_w, total_table_h)
    table = table_shape.table
    table.columns[0].width = col_w0
    table.columns[1].width = col_w1

    # Header Row
    headers = ["STEP / EXPRESSION", "STATE & PEDAGOGICAL MEANING"]
    for c_idx, h in enumerate(headers):
        cell = table.cell(0, c_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = theme.primary
        tf = cell.text_frame
        p = tf.paragraphs[0]
        p.text = h
        p.font.name = Typography.BADGE.font_name
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = theme.text_on_dark
        p.alignment = PP_ALIGN.LEFT if c_idx == 0 else PP_ALIGN.LEFT

    # Data Rows
    for r_idx, (col0, col1) in enumerate(rows):
        is_even = (r_idx % 2 == 0)
        row_bg = theme.surface if is_even else theme.surface_alt
        
        c0 = table.cell(r_idx + 1, 0)
        c0.fill.solid()
        c0.fill.fore_color.rgb = row_bg
        p0 = c0.text_frame.paragraphs[0]
        p0.text = col0
        p0.font.name = Typography.BODY.font_name
        p0.font.size = Pt(13)
        p0.font.bold = True
        p0.font.color.rgb = theme.text

        c1 = table.cell(r_idx + 1, 1)
        c1.fill.solid()
        c1.fill.fore_color.rgb = row_bg
        p1 = c1.text_frame.paragraphs[0]
        p1.text = col1
        p1.font.name = Typography.BODY.font_name
        p1.font.size = Pt(13)
        p1.font.color.rgb = theme.text

    add_footer(slide, kw.get("slide_number", 1), kw.get("total_slides", 1), theme, section_name=kw.get("deck_title", ""))
    add_speaker_notes(slide, content.speaker_note)
