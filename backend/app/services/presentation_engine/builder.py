"""
TeachGenie — Presentation Builder
===================================
Main entry point: takes a PresentationPlan + theme → produces PPTX bytes.
Integrates: Layout Engine, QA Engine, Design Tokens.
"""
from app.core.logging import logger
import io
from typing import List, Optional
from pptx import Presentation

from . import SlideContent, SlidePurpose, PresentationPlan
from .tokens import ThemeColors, SLIDE_WIDTH, SLIDE_HEIGHT, get_theme, pick_theme_for_topic
from .layout_engine import render_slide, select_layout_for_content
from .qa_engine import auto_compress_slide, evaluate_deck_quality


def build_presentation(
    plan: PresentationPlan,
    theme_id: str = "",
    topic: str = "",
    preset_label: str = "Presentation",
    audience: str = "university",
) -> bytes:
    """
    Build a complete PPTX from a PresentationPlan.

    1. Select theme
    2. Auto-detect layout for any slide without explicit purpose
    3. Run QA auto-compression on each slide
    4. Render each slide using the Layout Engine
    5. Return PPTX bytes
    """
    # 1. Theme selection
    if not theme_id:
        theme_id = pick_theme_for_topic(topic or plan.deck_title)
    theme = get_theme(theme_id)

    # 2. Create presentation
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    slides = list(plan.slides)
    total_slides = len(slides)

    # 3. Ensure cover and closing exist
    if not slides or slides[0].purpose != SlidePurpose.COVER:
        cover = SlideContent(
            id="cover",
            purpose=SlidePurpose.COVER,
            title=plan.deck_title or topic,
            subtitle=f"{audience.replace('_', ' ').title()} Level",
        )
        slides.insert(0, cover)
        total_slides += 1

    if slides[-1].purpose != SlidePurpose.CLOSING:
        closing = SlideContent(
            id="closing",
            purpose=SlidePurpose.CLOSING,
            title="Thank You",
            subtitle="Questions & Discussion",
        )
        slides.append(closing)
        total_slides += 1

    total_slides = len(slides)

    # 4. Process each slide
    for i, content in enumerate(slides):
        # Auto-detect layout if not specified
        if content.purpose == SlidePurpose.CONCEPT:
            detected = select_layout_for_content(content)
            if detected != SlidePurpose.CONCEPT:
                content.purpose = detected

        # QA auto-compression (skip cover/closing)
        if content.purpose not in (SlidePurpose.COVER, SlidePurpose.CLOSING):
            content = auto_compress_slide(content)

        # Add blank slide layout
        slide_layout = prs.slide_layouts[6]  # blank layout
        slide = prs.slides.add_slide(slide_layout)

        # Render
        render_slide(
            slide, content, theme,
            slide_number=i + 1,
            total_slides=total_slides,
            deck_title=plan.deck_title,
            key_takeaways=plan.key_takeaways,
            preset_label=preset_label,
        )

    # 5. Evaluate deck quality (density + contrast)
    qa = evaluate_deck_quality(slides, theme=theme)
    logger.info(f"[QA] Deck QA: {qa['passed']}/{qa['total_slides']} slides passed | "
          f"Layout variety: {qa['variety_score']}% | "
          f"Critical: {qa['critical']}")
    if qa.get("contrast_issues"):
        for ci in qa["contrast_issues"]:
            logger.info(f"[QA][CONTRAST] {ci}")

    # 6. Export
    buffer = io.BytesIO()
    prs.save(buffer)
    return buffer.getvalue()
