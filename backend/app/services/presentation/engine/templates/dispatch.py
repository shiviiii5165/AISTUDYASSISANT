"""
Pedagogical Component Dispatcher for Design Templates
=====================================================
Direct lookup dispatcher that maps `content_pattern` from SlideSpec
to the corresponding deterministic pedagogical renderer.
"""
from typing import Optional, Dict, Any
from pptx.slide import Slide
from pptx.util import Emu
from app.services.presentation_engine.tokens import ThemeColors
from app.services.presentation_engine import (
    SlideContent, ProcessStep, ComparisonColumn, KPIMetric, VisualType
)
from app.services.presentation_engine.renderers.definition_box import render_definition_box
from app.services.presentation_engine.renderers.contrast_pair import render_contrast_pair
from app.services.presentation_engine.renderers.comparison_table import render_comparison_table
from app.services.presentation_engine.renderers.numbered_process import render_numbered_process
from app.services.presentation_engine.renderers.case_study_block import render_case_study_block
from app.services.presentation_engine.renderers.activity_banner import render_activity_banner
from app.services.presentation_engine.renderers.worked_example_table import render_worked_example_table
from app.services.presentation_engine.renderers.icon_badge_row import render_icon_badge_row
from app.services.presentation_engine.renderers.hub_and_spoke import render_hub_and_spoke
from app.services.presentation_engine.renderers.illustrated_icon_grid import render_illustrated_icon_grid
from app.services.presentation_engine.renderers.concept_split import render_concept_split
from app.services.presentation_engine.renderers.annotated_tiers import render_annotated_tiers
from app.services.presentation_engine.renderers.example_grid import render_example_grid

COMPONENT_RENDERERS = {
    "definition_box": render_definition_box,
    "contrast_pair": render_contrast_pair,
    "comparison_table": render_comparison_table,
    "numbered_process": render_numbered_process,
    "case_study_block": render_case_study_block,
    "activity_banner": render_activity_banner,
    "worked_example_table": render_worked_example_table,
    "icon_badge_row": render_icon_badge_row,
    "hub_and_spoke": render_hub_and_spoke,
    "illustrated_icon_grid": render_illustrated_icon_grid,
    "concept_split": render_concept_split,
    "annotated_tiers": render_annotated_tiers,
    "example_grid": render_example_grid,
}

def to_slide_content(slide_spec: dict) -> SlideContent:
    """Convert dict slide_spec into SlideContent model for renderers."""
    steps = [
        ProcessStep(number=i+1, title=s.get("title", ""), detail=s.get("detail", s.get("description", "")))
        for i, s in enumerate(slide_spec.get("steps", []))
    ]
    columns = [
        ComparisonColumn(heading=c.get("heading", c.get("title", "")), points=c.get("points", c.get("bullets", [])))
        for c in slide_spec.get("columns", [])
    ]
    visual = slide_spec.get("visual") or slide_spec.get("visual_spec") or {}

    return SlideContent(
        id=str(slide_spec.get("slide_no", "")),
        title=slide_spec.get("title", ""),
        subtitle=slide_spec.get("subtitle", ""),
        body_bullets=slide_spec.get("body_bullets", []),
        body_text=slide_spec.get("body_text", ""),
        example=slide_spec.get("example", ""),
        key_insight=slide_spec.get("key_message", slide_spec.get("key_insight", "")),
        content_pattern=slide_spec.get("content_pattern"),
        steps=steps,
        columns=columns,
        image_bytes=visual.get("image_bytes"),
        speaker_note=slide_spec.get("speaker_notes", "")
    )

def dispatch_pedagogical_component(
    slide: Slide,
    slide_spec: dict,
    theme: ThemeColors,
    slide_number: int = 1,
    total_slides: int = 1,
    deck_title: str = ""
) -> bool:
    """
    Direct lookup: If slide_spec has a recognized `content_pattern`,
    invokes the pedagogical renderer directly and returns True.
    If 'plain_concept' or unhandled, returns False to fall back to template bullets.
    """
    pattern = slide_spec.get("content_pattern")
    if not pattern:
        return False

    pattern_key = str(pattern).lower().replace("contentpattern.", "")

    if pattern_key in ("plain_concept", "parallel_comparison"):
        # Let template handle plain bullets or legacy comparison diagram
        return False

    renderer = COMPONENT_RENDERERS.get(pattern_key)
    if renderer:
        content = to_slide_content(slide_spec)

        # Build extra kwargs for variant selection
        extra_kw = dict(
            slide_number=slide_number,
            total_slides=total_slides,
            deck_title=deck_title,
        )
        # Thin-rule numeral variant for editorial/minimal themes on numbered_process
        if pattern_key == "numbered_process":
            theme_name = getattr(theme, "name", "").lower()
            if any(t in theme_name for t in ["minimal", "charcoal", "editorial"]):
                extra_kw["prefer_thin_rule"] = True

        renderer(
            slide=slide,
            content=content,
            theme=theme,
            **extra_kw,
        )

        # After renderer fires, also add a corner image if available
        # This gives pedagogical slides visual enhancement without disrupting layout
        visual = slide_spec.get("visual") or slide_spec.get("visual_spec") or {}
        img_bytes = visual.get("image_bytes")
        if img_bytes and len(img_bytes) > 100:
            try:
                from pptx.util import Inches
                from app.services.presentation_engine.renderers.base import add_image
                # Place small image in bottom-right corner with rounded corners
                add_image(
                    slide, img_bytes,
                    Inches(10.3), Inches(4.8),
                    Inches(2.5), Inches(2.0),
                    corner_radius=Inches(0.1),
                )
            except Exception:
                pass  # Image placement is best-effort

        return True

    return False
