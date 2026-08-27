"""Comparison renderer — Side-by-side A vs B comparison."""
from pptx.slide import Slide
from pptx.util import Inches
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from .. import SlideContent, ThemeColors, ComparisonColumn
from ..tokens import (
    SLIDE_WIDTH, SLIDE_HEIGHT, MARGIN_LEFT, CONTENT_WIDTH,
    ZONE_TITLE_TOP, ZONE_TITLE_HEIGHT, ZONE_CONTENT_TOP,
    Typography, grid_x, grid_width, BULLET_GLYPH,
)
from .base import (
    add_filled_rect, add_text_box, add_accent_bar, add_card,
    add_bullet_list, add_footer, add_speaker_notes,
)


def render_comparison(slide: Slide, content: SlideContent, theme: ThemeColors, **kw) -> None:
    """Render a symmetrical comparison layout (A vs B)."""
    add_filled_rect(slide, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, theme.background)

    add_accent_bar(
        slide, MARGIN_LEFT - Inches(0.15), ZONE_TITLE_TOP + Inches(0.1),
        width=Inches(0.06), height=Inches(0.55), color=theme.primary,
    )
    add_text_box(
        slide, content.title, MARGIN_LEFT, ZONE_TITLE_TOP,
        CONTENT_WIDTH, ZONE_TITLE_HEIGHT,
        token=Typography.SLIDE_TITLE, color=theme.text,
    )

    columns = content.columns
    if not columns:
        # Fallback: split bullets into two columns
        mid = len(content.body_bullets) // 2
        columns = [
            ComparisonColumn(heading="Option A", points=content.body_bullets[:mid] or ["–"]),
            ComparisonColumn(heading="Option B", points=content.body_bullets[mid:] or ["–"]),
        ]

    num_cols = min(len(columns), 3)
    gap = Inches(0.4)
    col_width = (CONTENT_WIDTH - (num_cols - 1) * gap) / num_cols
    content_height = Inches(4.5)

    col_accents = [theme.primary, theme.secondary, theme.accent]

    for i, col in enumerate(columns[:num_cols]):
        x = MARGIN_LEFT + i * (col_width + gap)
        y = ZONE_CONTENT_TOP + Inches(0.2)

        # Column header bar
        add_filled_rect(
            slide, x, y, col_width, Inches(0.04),
            col_accents[i % len(col_accents)],
        )

        # Column heading
        add_text_box(
            slide, col.heading,
            x, y + Inches(0.15),
            col_width, Inches(0.4),
            token=Typography.SLIDE_SUBTITLE, color=col_accents[i % len(col_accents)],
            alignment=PP_ALIGN.LEFT,
        )

        # Column points
        if col.points:
            add_bullet_list(
                slide, col.points,
                x, y + Inches(0.7),
                col_width, content_height - Inches(1.0),
                token=Typography.BODY,
                text_color=theme.text,
                accent_color=col_accents[i % len(col_accents)],
                max_bullets=6,
            )
            
        # Draw vertical divider for all but the last column
        if i < num_cols - 1:
            div_x = x + col_width + (gap / 2)
            add_filled_rect(
                slide, div_x, y + Inches(0.1), Inches(0.02), content_height - Inches(0.5),
                theme.border_light
            )

    # Clean text VS badge between first two columns
    if num_cols >= 2:
        vs_x = MARGIN_LEFT + col_width + (gap / 2) - Inches(0.2)
        vs_y = ZONE_CONTENT_TOP + Inches(0.25)
        add_filled_rect(
            slide, vs_x, vs_y, Inches(0.4), Inches(0.25),
            theme.background
        )
        add_text_box(
            slide, "VS",
            vs_x, vs_y, Inches(0.4), Inches(0.25),
            token=Typography.BADGE, color=theme.text_muted,
            alignment=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
        )

    add_footer(slide, kw.get("slide_number", 0), kw.get("total_slides", 0), theme)
    add_speaker_notes(slide, content.speaker_note)
