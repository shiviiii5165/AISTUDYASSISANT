"""
TeachGenie Renderer — Numbered Process Component
================================================
Renders a sequential workflow with two visual variants:

1. **Circular Badge** (default): Crisp numbered chips (0.42" diameter)
   inside card panels. Preferred by most templates.

2. **Thin Rule Numeral**: Plain "01" / "02" / "03" numerals over a thin
   colored underline rule, each with bold header + one line. Cleaner
   aesthetic preferred by editorial/minimal templates.

Template theme controls which variant is used via the `prefer_thin_rule`
keyword argument.
"""
from pptx.slide import Slide
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
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


def _extract_steps(content: SlideContent) -> list:
    """Extract (title, detail) pairs from content steps or bullets."""
    steps_data = []
    if content.steps:
        for s in content.steps[:5]:
            steps_data.append((s.title or f"Step {s.number}", s.detail or ""))
    elif content.body_bullets:
        for i, b in enumerate(content.body_bullets[:5]):
            if ":" in b:
                parts = b.split(":", 1)
                steps_data.append((parts[0].strip(), parts[1].strip()))
            else:
                steps_data.append((f"Step {i+1}", b.strip()))
    else:
        steps_data = [
            ("Initiation", "Capture requirements and formulate problem constraints."),
            ("Transformation", "Process inputs through deterministic computational steps."),
            ("Validation", "Verify outputs against specification contracts.")
        ]
    return steps_data


def _render_circular_badge_variant(
    slide: Slide,
    steps_data: list,
    content_top,
    theme: ThemeColors,
) -> None:
    """Original variant: circular number chips inside card panels."""
    n_steps = len(steps_data)
    gap = Inches(0.3)
    step_w = (CONTENT_WIDTH - gap * (n_steps - 1)) // n_steps
    card_h = Inches(3.8)

    for idx, (title_text, detail_text) in enumerate(steps_data):
        step_x = MARGIN_LEFT + idx * (step_w + gap)

        # Card container
        add_card(slide, step_x, content_top, step_w, card_h,
                 fill_color=theme.surface, border_color=theme.border)

        # Circular number chip
        chip_size = Inches(0.42)
        chip_x = step_x + Inches(0.25)
        chip_y = content_top + Inches(0.25)

        chip = slide.shapes.add_shape(MSO_SHAPE.OVAL, chip_x, chip_y, chip_size, chip_size)
        chip.fill.solid()
        chip.fill.fore_color.rgb = theme.primary
        chip.line.fill.background()
        tf = chip.text_frame
        p = tf.paragraphs[0]
        p.text = str(idx + 1)
        p.font.name = Typography.BADGE.font_name
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = theme.text_on_dark
        p.alignment = PP_ALIGN.CENTER

        # Connector arrow to next step
        if idx < n_steps - 1:
            arr_x = step_x + step_w + Inches(0.08)
            arr_y = content_top + Inches(0.35)
            add_text_box(
                slide, "→", arr_x, arr_y, gap - Inches(0.16), Inches(0.4),
                token=Typography.BADGE, color=theme.accent, alignment=PP_ALIGN.CENTER
            )

        # Step Title
        add_text_box(
            slide, title_text,
            step_x + Inches(0.25), content_top + Inches(0.85),
            step_w - Inches(0.5), Inches(0.7),
            token=Typography.CARD_TITLE, color=theme.text, bold=True, word_wrap=True
        )

        # Step Detail
        add_text_box(
            slide, detail_text,
            step_x + Inches(0.25), content_top + Inches(1.6),
            step_w - Inches(0.5), card_h - Inches(1.8),
            token=Typography.BODY, color=theme.text_muted, word_wrap=True
        )


def _render_thin_rule_variant(
    slide: Slide,
    steps_data: list,
    content_top,
    theme: ThemeColors,
) -> None:
    """
    Alternative variant: plain "01" / "02" numerals over a thin colored
    underline rule, each with bold header + one description line.
    Cleaner, magazine-style aesthetic.
    """
    n_steps = len(steps_data)
    gap = Inches(0.35)
    step_w = (CONTENT_WIDTH - gap * (n_steps - 1)) // n_steps
    card_h = Inches(3.8)

    for idx, (title_text, detail_text) in enumerate(steps_data):
        step_x = MARGIN_LEFT + idx * (step_w + gap)

        # Card container (lighter, borderless for clean feel)
        add_card(slide, step_x, content_top, step_w, card_h,
                 fill_color=theme.surface, border_color=theme.border_light)

        # Large plain numeral "01", "02", etc.
        numeral = f"{idx + 1:02d}"
        add_text_box(
            slide, numeral,
            step_x + Inches(0.25), content_top + Inches(0.2),
            Inches(1.2), Inches(0.55),
            token=Typography.NUMERAL_STEP, color=theme.primary,
            alignment=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.BOTTOM,
        )

        # Thin colored underline rule beneath numeral
        rule_y = content_top + Inches(0.82)
        add_filled_rect(
            slide, step_x + Inches(0.25), rule_y,
            Inches(1.0), Inches(0.035),
            fill_color=theme.accent,
        )

        # Step Title — bold, below the rule
        add_text_box(
            slide, title_text,
            step_x + Inches(0.25), content_top + Inches(1.0),
            step_w - Inches(0.5), Inches(0.65),
            token=Typography.CARD_TITLE, color=theme.text, bold=True, word_wrap=True
        )

        # Step Detail
        add_text_box(
            slide, detail_text,
            step_x + Inches(0.25), content_top + Inches(1.7),
            step_w - Inches(0.5), card_h - Inches(1.9),
            token=Typography.BODY, color=theme.text_muted, word_wrap=True
        )


def render_numbered_process(
    slide: Slide,
    content: SlideContent,
    theme: ThemeColors,
    **kw
) -> None:
    """Render a step-by-step numbered process with variant selection."""
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

    steps_data = _extract_steps(content)
    content_top = ZONE_CONTENT_TOP + Inches(0.2)

    # Variant selection: thin-rule preferred by editorial/minimal themes
    prefer_thin_rule = kw.get("prefer_thin_rule", False)

    if prefer_thin_rule:
        _render_thin_rule_variant(slide, steps_data, content_top, theme)
    else:
        _render_circular_badge_variant(slide, steps_data, content_top, theme)

    add_footer(slide, kw.get("slide_number", 1), kw.get("total_slides", 1), theme, section_name=kw.get("deck_title", ""))
    add_speaker_notes(slide, content.speaker_note)
