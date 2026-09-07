"""
TeachGenie Renderer — Illustrated Icon Grid Component
=====================================================
Renders a grid of 3–5 concept cards featuring bundled static PNG icons
from `icons.py`, bold labels, and concise subtitles.
Strictly scoped to structural CS concepts (stack, queue, tree, graph, database).
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
    add_filled_rect, add_text_box, add_card, add_accent_bar,
    add_footer, add_speaker_notes
)
from .icons import render_bundled_icon

def render_illustrated_icon_grid(
    slide: Slide,
    content: SlideContent,
    theme: ThemeColors,
    **kw
) -> None:
    """Render a card grid featuring bundled high-resolution static PNG icons."""
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

    items = []
    # Infer or extract cards
    if content.body_bullets:
        for b in content.body_bullets[:4]:
            icon_guess = "plate-stack"
            lb = b.lower()
            if "queue" in lb or "fifo" in lb:
                icon_guess = "queue-line"
            elif "tree" in lb or "hierarch" in lb:
                icon_guess = "tree-branch"
            elif "graph" in lb or "network" in lb:
                icon_guess = "network-graph"
            elif "data" in lb or "sql" in lb or "storage" in lb:
                icon_guess = "database-cylinder"
            elif "stack" in lb or "lifo" in lb:
                icon_guess = "plate-stack"
            elif "user" in lb or "person" in lb:
                icon_guess = "person"

            if ":" in b:
                parts = b.split(":", 1)
                items.append((parts[0].strip(), parts[1].strip(), icon_guess))
            else:
                items.append((b.strip()[:20], b.strip(), icon_guess))
    else:
        items = [
            ("Stack (LIFO)", "Push and pop elements strictly at the top.", "plate-stack"),
            ("Queue (FIFO)", "Enqueue at rear, dequeue at front in strict arrival order.", "queue-line"),
            ("Binary Tree", "Hierarchical root branching into left and right subtrees.", "tree-branch"),
            ("Graph Topology", "Interconnected vertices joined by directed or undirected edges.", "network-graph")
        ]

    n = len(items)
    gap = Inches(0.3)
    card_w = (CONTENT_WIDTH - gap * (n - 1)) // n
    content_top = ZONE_CONTENT_TOP + Inches(0.15)
    card_h = Inches(4.2)

    for idx, (label, detail, icon_name) in enumerate(items):
        cx = MARGIN_LEFT + idx * (card_w + gap)

        # Card container
        add_card(slide, cx, content_top, card_w, card_h,
                 fill_color=theme.surface, border_color=theme.border)

        # Render bundled icon
        icon_size = Inches(1.4)
        icon_x = cx + (card_w - icon_size) // 2
        icon_y = content_top + Inches(0.3)
        render_bundled_icon(slide, icon_name, icon_x, icon_y, icon_size, icon_size)

        # Label beneath icon
        add_text_box(
            slide, label,
            cx + Inches(0.15), icon_y + icon_size + Inches(0.2),
            card_w - Inches(0.3), Inches(0.55),
            token=Typography.CARD_TITLE, color=theme.text, bold=True,
            alignment=PP_ALIGN.CENTER, word_wrap=True
        )

        # Detail text
        add_text_box(
            slide, detail,
            cx + Inches(0.15), icon_y + icon_size + Inches(0.8),
            card_w - Inches(0.3), card_h - (icon_size + Inches(1.2)),
            token=Typography.BODY, color=theme.text_muted,
            alignment=PP_ALIGN.CENTER, word_wrap=True
        )

    add_footer(slide, kw.get("slide_number", 1), kw.get("total_slides", 1), theme, section_name=kw.get("deck_title", ""))
    add_speaker_notes(slide, content.speaker_note)
