"""Case Study renderer — Problem → Intervention → Outcome structure."""
from pptx.slide import Slide
from pptx.util import Inches
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from .. import SlideContent, ThemeColors
from ..tokens import (
    SLIDE_WIDTH, SLIDE_HEIGHT, MARGIN_LEFT, CONTENT_WIDTH,
    ZONE_TITLE_TOP, ZONE_TITLE_HEIGHT, ZONE_CONTENT_TOP,
    Typography, grid_x, grid_width,
)
from .base import (
    add_filled_rect, add_text_box, add_accent_bar, add_card,
    add_bullet_list, add_footer, add_speaker_notes,
)


def render_case_study(slide: Slide, content: SlideContent, theme: ThemeColors, **kw) -> None:
    """Render a case study slide with structured sections."""
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

    # Split into 3 horizontal cards: Context | Solution | Result
    # Use body_bullets distributed into sections, or fall back to example text
    bullets = content.body_bullets or []
    third = max(len(bullets) // 3, 1)

    sections_data = [
        ("Context", bullets[:third] if bullets else [content.body_text or "–"], theme.surface_alt),
        ("Solution", bullets[third:2*third] if len(bullets) > third else [content.example or "–"], theme.primary_light),
        ("Outcome", bullets[2*third:] if len(bullets) > 2*third else [content.key_insight or "–"], theme.surface_alt),
    ]

    gap = Inches(0.2)
    card_w = (CONTENT_WIDTH - 2 * gap) / 3
    card_h = Inches(3.8)

    for i, (label, points, bg) in enumerate(sections_data):
        x = MARGIN_LEFT + i * (card_w + gap)
        y = ZONE_CONTENT_TOP + Inches(0.2)

        add_card(slide, x, y, card_w, card_h, fill_color=bg, border_color=theme.border)

        # Section badge
        add_text_box(
            slide, label,
            x + Inches(0.2), y + Inches(0.2),
            card_w - Inches(0.4), Inches(0.35),
            token=Typography.BADGE, color=theme.primary,
        )

        # Section content
        # For Outcome (index 2), if metrics exist, show them prominently instead of bullets
        if i == 2 and content.metrics:
            m_top = y + Inches(0.7)
            for m in content.metrics[:2]:
                add_text_box(
                    slide, m.value,
                    x + Inches(0.2), m_top,
                    card_w - Inches(0.4), Inches(0.8),
                    token=Typography.KPI_NUMBER, color=theme.primary,
                )
                add_text_box(
                    slide, m.label,
                    x + Inches(0.2), m_top + Inches(0.8),
                    card_w - Inches(0.4), Inches(0.4),
                    token=Typography.KPI_LABEL, color=theme.text_muted,
                )
                m_top += Inches(1.3)
        elif isinstance(points, list) and points:
            add_bullet_list(
                slide, points,
                x + Inches(0.2), y + Inches(0.7),
                card_w - Inches(0.4), card_h - Inches(1.0),
                token=Typography.BULLET_SMALL, text_color=theme.text,
                accent_color=theme.primary, max_bullets=4,
            )
        elif isinstance(points, str):
            add_text_box(
                slide, points,
                x + Inches(0.2), y + Inches(0.7),
                card_w - Inches(0.4), card_h - Inches(1.0),
                token=Typography.BODY, color=theme.text,
            )

    add_footer(slide, kw.get("slide_number", 0), kw.get("total_slides", 0), theme)
    add_speaker_notes(slide, content.speaker_note)
