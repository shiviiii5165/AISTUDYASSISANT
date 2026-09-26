"""
LearnByGenie Renderer — Hub and Spoke Component
=============================================
Renders a central concept node connected via clean connectors to surrounding
satellite concept cards, ideal for taxonomies, ecosystem overviews, and core principles.
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from .. import SlideContent, ThemeColors
from ..tokens import (
    MARGIN_LEFT, CONTENT_WIDTH, ZONE_TITLE_TOP, ZONE_TITLE_HEIGHT,
    ZONE_CONTENT_TOP, Typography
)
from .base import (
    add_filled_rect, add_text_box, add_card, add_accent_bar,
    add_footer, add_speaker_notes
)

def render_hub_and_spoke(
    slide: Slide,
    content: SlideContent,
    theme: ThemeColors,
    **kw
) -> None:
    """Render a central hub node connected to 4 satellite cards."""
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

    satellites = []
    if content.body_bullets:
        for b in content.body_bullets[:4]:
            if ":" in b:
                parts = b.split(":", 1)
                satellites.append((parts[0].strip(), parts[1].strip()))
            else:
                satellites.append(("Core Facet", b.strip()))
    else:
        satellites = [
            ("Model Layer", "Encapsulates schema rules and business domain entities."),
            ("View Layer", "Renders deterministic UI and responds to state updates."),
            ("Controller", "Routes inbound client requests and triggers services."),
            ("Persistence", "Maintains durable transaction logs in ACID storage.")
        ]

    while len(satellites) < 4:
        satellites.append(("Feature", "Supporting domain component."))

    # Layout:
    # Central Hub Node in middle
    hub_cx = Inches(13.333) // 2
    hub_cy = Inches(4.3)
    hub_w = Inches(3.2)
    hub_h = Inches(1.5)
    hub_x = hub_cx - hub_w // 2
    hub_y = hub_cy - hub_h // 2

    # Satellite cards in 4 quadrants
    card_w = Inches(3.8)
    card_h = Inches(1.8)

    pos = [
        (MARGIN_LEFT, Inches(2.1)),                                    # Top-Left
        (MARGIN_LEFT + CONTENT_WIDTH - card_w, Inches(2.1)),          # Top-Right
        (MARGIN_LEFT, Inches(4.7)),                                    # Bottom-Left
        (MARGIN_LEFT + CONTENT_WIDTH - card_w, Inches(4.7)),          # Bottom-Right
    ]

    # Draw connector lines first
    for (sx, sy) in pos:
        sc_x = sx + card_w // 2
        sc_y = sy + card_h // 2
        line = slide.shapes.add_connector(1, hub_cx, hub_cy, sc_x, sc_y) # 1 = straight
        line.line.color.rgb = theme.border
        line.line.width = Pt(2.0)

    # Central Hub Card
    add_card(slide, hub_x, hub_y, hub_w, hub_h,
             fill_color=theme.primary, border_color=theme.accent)
    add_text_box(
        slide, content.key_insight or content.title,
        hub_x + Inches(0.2), hub_y + Inches(0.3),
        hub_w - Inches(0.4), hub_h - Inches(0.6),
        token=Typography.CARD_TITLE, color=theme.text_on_dark,
        bold=True, alignment=PP_ALIGN.CENTER, word_wrap=True
    )

    # Satellites
    for (title_s, desc_s), (sx, sy) in zip(satellites, pos):
        add_card(slide, sx, sy, card_w, card_h,
                 fill_color=theme.surface, border_color=theme.border)
        add_text_box(
            slide, title_s,
            sx + Inches(0.2), sy + Inches(0.15),
            card_w - Inches(0.4), Inches(0.4),
            token=Typography.BADGE, color=theme.primary
        )
        add_text_box(
            slide, desc_s,
            sx + Inches(0.2), sy + Inches(0.55),
            card_w - Inches(0.4), card_h - Inches(0.7),
            token=Typography.BODY, color=theme.text, word_wrap=True
        )

    add_footer(slide, kw.get("slide_number", 1), kw.get("total_slides", 1), theme, section_name=kw.get("deck_title", ""))
    add_speaker_notes(slide, content.speaker_note)
