"""KPI / Big Number renderer — Hero metrics with contextual labels."""
from pptx.slide import Slide
from pptx.util import Inches
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from .. import SlideContent, ThemeColors, KPIMetric
from ..tokens import (
    SLIDE_WIDTH, SLIDE_HEIGHT, MARGIN_LEFT, CONTENT_WIDTH,
    ZONE_TITLE_TOP, ZONE_TITLE_HEIGHT, ZONE_CONTENT_TOP,
    Typography, grid_x, grid_width,
)
from .base import (
    add_filled_rect, add_text_box, add_accent_bar, add_card,
    add_footer, add_speaker_notes,
)


def render_kpi_metrics(slide: Slide, content: SlideContent, theme: ThemeColors, **kw) -> None:
    """Render big KPI numbers with contextual labels and cards."""
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

    metrics = content.metrics
    if not metrics:
        # Fallback: extract from bullets
        metrics = [KPIMetric(value=f"#{i+1}", label=b, context="")
                   for i, b in enumerate(content.body_bullets[:4])]

    if not metrics:
        return

    num = min(len(metrics), 4)

    if num == 1:
        # Single hero KPI — centered
        m = metrics[0]
        add_text_box(
            slide, m.value,
            MARGIN_LEFT, ZONE_CONTENT_TOP + Inches(0.5),
            CONTENT_WIDTH, Inches(1.5),
            token=Typography.KPI_NUMBER, color=theme.primary,
            alignment=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
        )
        add_text_box(
            slide, m.label,
            MARGIN_LEFT, ZONE_CONTENT_TOP + Inches(2.0),
            CONTENT_WIDTH, Inches(0.5),
            token=Typography.KPI_LABEL, color=theme.text_muted,
            alignment=PP_ALIGN.CENTER,
        )
        if m.context:
            add_text_box(
                slide, m.context,
                MARGIN_LEFT + Inches(2), ZONE_CONTENT_TOP + Inches(2.8),
                CONTENT_WIDTH - Inches(4), Inches(0.8),
                token=Typography.BODY, color=theme.text,
                alignment=PP_ALIGN.CENTER,
            )
    else:
        # Multiple KPIs in cards
        gap = Inches(0.3)
        card_w = (CONTENT_WIDTH - (num - 1) * gap) / num
        card_h = Inches(3.2)

        for i, m in enumerate(metrics[:num]):
            x = MARGIN_LEFT + i * (card_w + gap)
            y = ZONE_CONTENT_TOP + Inches(0.5)

            # Card bg
            add_card(slide, x, y, card_w, card_h,
                     fill_color=theme.surface, border_color=theme.border)

            # Top accent line
            add_filled_rect(slide, x, y, card_w, Inches(0.05), theme.primary)

            # Big number
            add_text_box(
                slide, m.value,
                x + Inches(0.2), y + Inches(0.4),
                card_w - Inches(0.4), Inches(1.0),
                token=Typography.KPI_NUMBER, color=theme.primary,
                alignment=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
            )

            # Label
            add_text_box(
                slide, m.label,
                x + Inches(0.2), y + Inches(1.5),
                card_w - Inches(0.4), Inches(0.4),
                token=Typography.KPI_LABEL, color=theme.text_muted,
                alignment=PP_ALIGN.CENTER,
            )

            # Context
            if m.context:
                add_text_box(
                    slide, m.context,
                    x + Inches(0.15), y + Inches(2.1),
                    card_w - Inches(0.3), Inches(0.8),
                    token=Typography.CAPTION, color=theme.text,
                    alignment=PP_ALIGN.CENTER,
                )

    add_footer(slide, kw.get("slide_number", 0), kw.get("total_slides", 0), theme)
    add_speaker_notes(slide, content.speaker_note)
