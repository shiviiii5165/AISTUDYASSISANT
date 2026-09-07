"""Process flow renderer — Numbered step-by-step horizontal or vertical flow."""
from pptx.slide import Slide
from pptx.util import Inches
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from .. import SlideContent, ThemeColors, ProcessStep
from ..tokens import (
    SLIDE_WIDTH, SLIDE_HEIGHT, MARGIN_LEFT, CONTENT_WIDTH,
    ZONE_TITLE_TOP, ZONE_TITLE_HEIGHT, ZONE_CONTENT_TOP,
    Typography, grid_x, grid_width, STEP_GLYPH,
)
from .base import (
    add_filled_rect, add_text_box, add_accent_bar, add_card,
    add_footer, add_speaker_notes,
)


def render_process_flow(slide: Slide, content: SlideContent, theme: ThemeColors, **kw) -> None:
    """Render a process flow: numbered step cards in a horizontal track."""
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

    steps = content.steps
    if not steps:
        # Fallback: create steps from body_bullets
        steps = [ProcessStep(number=i+1, title=b, detail="") for i, b in enumerate(content.body_bullets[:6])]

    if not steps:
        return

    num_steps = min(len(steps), 6)

    # Dynamic card height calculation from content volume
    max_detail_chars = max((len(s.detail or "") for s in steps[:num_steps]), default=0)
    max_title_chars = max((len(s.title or "") for s in steps[:num_steps]), default=0)

    est_h = Inches(1.3)
    if max_title_chars > 20:
        est_h += Inches(0.3)
    if max_detail_chars > 60:
        est_h += Inches(0.9)
    elif max_detail_chars > 20:
        est_h += Inches(0.5)

    card_height = max(Inches(2.3), min(est_h + Inches(0.4), Inches(3.8)))
    content_area_h = Inches(4.5)
    row_top = ZONE_CONTENT_TOP + max(Inches(0.1), (content_area_h - card_height) / 2)

    total_gap = Inches(0.2) * (num_steps - 1)
    card_width = (CONTENT_WIDTH - total_gap) / num_steps

    for i, step in enumerate(steps[:num_steps]):
        x = MARGIN_LEFT + i * (card_width + Inches(0.2))
        y = row_top

        # Step card with dynamic fit
        add_card(slide, x, y, card_width, card_height,
                 fill_color=theme.surface, border_color=theme.border)

        # Step number circle (colored badge)
        num_size = Inches(0.42)
        add_filled_rect(
            slide, x + card_width / 2 - num_size / 2, y + Inches(0.15),
            num_size, num_size, theme.primary,
            corner_radius=Inches(0.21),
        )
        add_text_box(
            slide, str(step.number),
            x + card_width / 2 - num_size / 2, y + Inches(0.15),
            num_size, num_size,
            token=Typography.BADGE, color=theme.text_on_dark,
            alignment=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
        )

        # Step title
        title_h = Inches(0.5) if max_title_chars <= 25 else Inches(0.7)
        title_y = y + Inches(0.62)
        add_text_box(
            slide, step.title,
            x + Inches(0.15), title_y,
            card_width - Inches(0.3), title_h,
            token=Typography.BULLET, color=theme.text,
            alignment=PP_ALIGN.CENTER,
        )

        # Step detail
        if step.detail:
            detail_y = title_y + title_h + Inches(0.04)
            avail_h = max(Inches(0.5), y + card_height - detail_y - Inches(0.12))
            add_text_box(
                slide, step.detail,
                x + Inches(0.15), detail_y,
                card_width - Inches(0.3), avail_h,
                token=Typography.CAPTION, color=theme.text_muted,
                alignment=PP_ALIGN.CENTER,
            )

        # Arrow between steps
        if i < num_steps - 1:
            arrow_x = x + card_width
            add_text_box(
                slide, "→",
                arrow_x, y + card_height / 2 - Inches(0.15),
                Inches(0.2), Inches(0.3),
                token=Typography.BODY, color=theme.text_muted,
                alignment=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
            )

    add_footer(slide, kw.get("slide_number", 0), kw.get("total_slides", 0), theme)
    add_speaker_notes(slide, content.speaker_note)
