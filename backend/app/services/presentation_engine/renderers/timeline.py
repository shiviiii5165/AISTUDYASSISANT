"""Timeline renderer — Milestone progression track."""
from pptx.slide import Slide
from pptx.util import Inches
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from .. import SlideContent, ThemeColors, TimelineMilestone
from ..tokens import (
    SLIDE_WIDTH, SLIDE_HEIGHT, MARGIN_LEFT, CONTENT_WIDTH,
    ZONE_TITLE_TOP, ZONE_TITLE_HEIGHT, ZONE_CONTENT_TOP,
    Typography, grid_x, grid_width,
)
from .base import (
    add_filled_rect, add_text_box, add_accent_bar,
    add_footer, add_speaker_notes,
)


def render_timeline(slide: Slide, content: SlideContent, theme: ThemeColors, **kw) -> None:
    """Render a horizontal timeline with milestone markers."""
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

    milestones = content.milestones
    if not milestones:
        milestones = [TimelineMilestone(date=f"Phase {i+1}", label=b, detail="")
                      for i, b in enumerate(content.body_bullets[:6])]

    if not milestones:
        return

    num = min(len(milestones), 6)

    # Horizontal timeline track
    track_y = ZONE_CONTENT_TOP + Inches(1.8)
    track_left = MARGIN_LEFT + Inches(0.3)
    track_width = CONTENT_WIDTH - Inches(0.6)

    # Track line
    add_filled_rect(
        slide, track_left, track_y, track_width, Inches(0.04), theme.border
    )

    segment = track_width / max(num - 1, 1)

    for i, ms in enumerate(milestones[:num]):
        cx = track_left + i * segment
        dot_size = Inches(0.22)

        # Milestone dot
        add_filled_rect(
            slide, cx - dot_size / 2, track_y - dot_size / 2 + Inches(0.02),
            dot_size, dot_size, theme.primary,
            corner_radius=Inches(0.11),
        )

        # Date label — above the track
        add_text_box(
            slide, ms.date,
            cx - Inches(0.8), track_y - Inches(0.7),
            Inches(1.6), Inches(0.35),
            token=Typography.BADGE, color=theme.primary,
            alignment=PP_ALIGN.CENTER,
        )

        # Milestone label — below the track
        add_text_box(
            slide, ms.label,
            cx - Inches(0.9), track_y + Inches(0.4),
            Inches(1.8), Inches(0.5),
            token=Typography.BULLET_SMALL, color=theme.text,
            alignment=PP_ALIGN.CENTER,
        )

        # Detail — further below
        if ms.detail:
            add_text_box(
                slide, ms.detail,
                cx - Inches(0.9), track_y + Inches(0.9),
                Inches(1.8), Inches(0.6),
                token=Typography.CAPTION, color=theme.text_muted,
                alignment=PP_ALIGN.CENTER,
            )

    add_footer(slide, kw.get("slide_number", 0), kw.get("total_slides", 0), theme)
    add_speaker_notes(slide, content.speaker_note)
