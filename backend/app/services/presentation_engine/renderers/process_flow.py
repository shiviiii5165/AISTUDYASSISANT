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

    # Horizontal layout: step cards in a row
    total_gap = Inches(0.2) * (num_steps - 1)
    card_width = (CONTENT_WIDTH - total_gap) / num_steps
    card_height = Inches(3.5)

    for i, step in enumerate(steps[:num_steps]):
        x = MARGIN_LEFT + i * (card_width + Inches(0.2))
        y = ZONE_CONTENT_TOP + Inches(0.3)

        # Step card
        add_card(slide, x, y, card_width, card_height,
                 fill_color=theme.surface, border_color=theme.border)

        # Step number circle (colored badge)
        num_size = Inches(0.5)
        add_filled_rect(
            slide, x + card_width / 2 - num_size / 2, y + Inches(0.2),
            num_size, num_size, theme.primary,
            corner_radius=Inches(0.25),
        )
        add_text_box(
            slide, str(step.number),
            x + card_width / 2 - num_size / 2, y + Inches(0.2),
            num_size, num_size,
            token=Typography.BADGE, color=theme.text_on_dark,
            alignment=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
        )

        # Step title
        add_text_box(
            slide, step.title,
            x + Inches(0.15), y + Inches(0.85),
            card_width - Inches(0.3), Inches(0.6),
            token=Typography.BULLET, color=theme.text,
            alignment=PP_ALIGN.CENTER,
        )

        # Step detail
        if step.detail:
            add_text_box(
                slide, step.detail,
                x + Inches(0.15), y + Inches(1.5),
                card_width - Inches(0.3), Inches(1.5),
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
