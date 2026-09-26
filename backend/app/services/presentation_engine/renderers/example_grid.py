"""
LearnByGenie Renderer — Example Grid Component
==============================================
Renders a 2x2 or 4-across grid of application/example items.
Each item: topic icon (from topic_icons) or small stock photo fallback
+ bold header + 1-2 lines description.

Consistent framing: all items get same corner-radius/card styling
regardless of whether icon or photo source is used.

Designed for "Real-World Applications" / "Use Cases" / "Examples" slides
where 3-4 concrete application domains are shown with consistent visual weight.
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from typing import List, Tuple
from .. import SlideContent, ThemeColors
from ..tokens import (
    MARGIN_LEFT, CONTENT_WIDTH, ZONE_TITLE_TOP, ZONE_TITLE_HEIGHT,
    ZONE_CONTENT_TOP, Typography, SLIDE_WIDTH, SLIDE_HEIGHT,
)
from .base import (
    add_filled_rect, add_text_box, add_card, add_accent_bar,
    add_footer, add_speaker_notes,
)
from .topic_icons import render_topic_icon


def _extract_grid_items(content: SlideContent) -> List[Tuple[str, str]]:
    """Extract (title, description) pairs for grid items from bullets."""
    items = []
    for b in content.body_bullets:
        b = b.strip()
        if ":" in b:
            parts = b.split(":", 1)
            items.append((parts[0].strip(), parts[1].strip()))
        elif " — " in b:
            parts = b.split(" — ", 1)
            items.append((parts[0].strip(), parts[1].strip()))
        elif " - " in b:
            parts = b.split(" - ", 1)
            items.append((parts[0].strip(), parts[1].strip()))
        else:
            # Use first 2-3 words as title, rest as description
            words = b.split()
            if len(words) > 3:
                items.append((" ".join(words[:2]), " ".join(words[2:])))
            else:
                items.append((b, ""))
    return items[:6]  # Cap at 6


def render_example_grid(
    slide: Slide,
    content: SlideContent,
    theme: ThemeColors,
    **kw
) -> None:
    """Render a 2x2 or row grid of application examples with icons."""
    add_filled_rect(slide, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, theme.background)

    # Title with accent bar
    add_accent_bar(
        slide, MARGIN_LEFT - Inches(0.15), ZONE_TITLE_TOP + Inches(0.1),
        width=Inches(0.06), height=Inches(0.55),
        color=theme.primary,
    )
    add_text_box(
        slide, content.title,
        MARGIN_LEFT, ZONE_TITLE_TOP, CONTENT_WIDTH, ZONE_TITLE_HEIGHT,
        token=Typography.SLIDE_TITLE,
        color=theme.text,
    )

    items = _extract_grid_items(content)
    if not items:
        items = [("Example 1", "Description"), ("Example 2", "Description")]

    n = len(items)
    content_top = ZONE_CONTENT_TOP + Inches(0.15)

    if n <= 4:
        _render_grid_2x2(slide, items, content_top, theme)
    else:
        _render_grid_row(slide, items, content_top, theme)

    add_footer(slide, kw.get("slide_number", 1), kw.get("total_slides", 1), theme,
               section_name=kw.get("deck_title", ""))
    add_speaker_notes(slide, content.speaker_note)


def _render_grid_2x2(
    slide: Slide,
    items: List[Tuple[str, str]],
    content_top: Emu,
    theme: ThemeColors,
) -> None:
    """2x2 grid layout for 3-4 items."""
    gap_h = Inches(0.3)
    gap_v = Inches(0.25)
    cols = 2
    rows = (len(items) + 1) // 2

    card_w = (CONTENT_WIDTH - gap_h * (cols - 1)) // cols
    card_h = Inches(1.9)

    for idx, (title, desc) in enumerate(items[:4]):
        col = idx % cols
        row = idx // cols
        card_x = MARGIN_LEFT + col * (card_w + gap_h)
        card_y = content_top + row * (card_h + gap_v)

        # Card container
        add_card(slide, card_x, card_y, card_w, card_h,
                 fill_color=theme.surface, border_color=theme.border_light)

        # Try topic icon first (left side of card)
        icon_size = Inches(0.55)
        icon_x = card_x + Inches(0.25)
        icon_y = card_y + Inches(0.3)

        icon_rendered = render_topic_icon(
            slide, f"{title} {desc}",
            icon_x, icon_y, icon_size, icon_size,
        )

        # Text zone (right of icon, or full width if no icon)
        if icon_rendered:
            text_x = icon_x + icon_size + Inches(0.2)
            text_w = card_w - icon_size - Inches(0.7)
        else:
            text_x = card_x + Inches(0.25)
            text_w = card_w - Inches(0.5)

            # Fallback: colored accent dot
            dot_size = Inches(0.12)
            add_filled_rect(
                slide, icon_x, icon_y + Inches(0.05),
                dot_size, dot_size,
                fill_color=theme.accent,
                corner_radius=Inches(0.06),
            )
            text_x = icon_x + dot_size + Inches(0.15)
            text_w = card_w - dot_size - Inches(0.65)

        # Item title (bold)
        add_text_box(
            slide, title,
            text_x, card_y + Inches(0.25), text_w, Inches(0.4),
            token=Typography.CARD_TITLE, color=theme.text,
            alignment=PP_ALIGN.LEFT, bold=True,
        )

        # Item description
        if desc:
            add_text_box(
                slide, desc,
                text_x, card_y + Inches(0.7), text_w, card_h - Inches(1.0),
                token=Typography.BULLET_SMALL, color=theme.text_muted,
                alignment=PP_ALIGN.LEFT, word_wrap=True,
            )


def _render_grid_row(
    slide: Slide,
    items: List[Tuple[str, str]],
    content_top: Emu,
    theme: ThemeColors,
) -> None:
    """Single-row layout for 5-6 items."""
    n = min(len(items), 6)
    gap = Inches(0.2)
    card_w = (CONTENT_WIDTH - gap * (n - 1)) // n
    card_h = Inches(3.6)

    for idx, (title, desc) in enumerate(items[:n]):
        card_x = MARGIN_LEFT + idx * (card_w + gap)

        # Card
        add_card(slide, card_x, content_top, card_w, card_h,
                 fill_color=theme.surface, border_color=theme.border_light)

        # Icon at top center
        icon_size = Inches(0.5)
        icon_x = card_x + (card_w - icon_size) // 2
        icon_y = content_top + Inches(0.25)

        icon_rendered = render_topic_icon(
            slide, f"{title} {desc}",
            icon_x, icon_y, icon_size, icon_size,
        )

        if not icon_rendered:
            # Fallback: small accent square
            add_filled_rect(
                slide, icon_x + Inches(0.15), icon_y + Inches(0.1),
                Inches(0.2), Inches(0.2),
                fill_color=theme.accent,
                corner_radius=Inches(0.04),
            )

        # Title below icon
        add_text_box(
            slide, title,
            card_x + Inches(0.15), content_top + Inches(0.9),
            card_w - Inches(0.3), Inches(0.5),
            token=Typography.CARD_TITLE, color=theme.text,
            alignment=PP_ALIGN.CENTER, bold=True, word_wrap=True,
        )

        # Description
        if desc:
            add_text_box(
                slide, desc,
                card_x + Inches(0.15), content_top + Inches(1.45),
                card_w - Inches(0.3), card_h - Inches(1.7),
                token=Typography.BULLET_SMALL, color=theme.text_muted,
                alignment=PP_ALIGN.CENTER, word_wrap=True,
            )
