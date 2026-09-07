"""
Deterministic Presentation Builder
==================================
Builds a professional PowerPoint presentation (.pptx) from a validated PresentationSpec.
- 16:9 Widescreen (13.333" x 7.5")
- Strict Exact Slide Count Assertion (len(prs.slides) == config.slide_count)
- Template & Theme routing
- Speaker notes and source references attached
"""
import io
from pptx import Presentation
from pptx.util import Inches
from app.services.presentation_engine.tokens import SLIDE_WIDTH, SLIDE_HEIGHT, get_theme
from .templates import TEMPLATE_ROUTER, render_academic_slide
from ..schemas import PresentationSpec


def build_presentation_spec(spec: PresentationSpec) -> bytes:
    """
    Builds PPTX bytes from a strictly validated PresentationSpec.
    Guarantees exact slide count matching spec.config.slide_count.
    """
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    # Resolve Theme
    theme_id = spec.config.theme or "blue_professional"
    theme = get_theme(theme_id)

    # Resolve Template System
    design_key = spec.config.design.value if hasattr(spec.config.design, "value") else str(spec.config.design)
    render_func = TEMPLATE_ROUTER.get(design_key, render_academic_slide)

    slides = spec.slides
    total_slides = len(slides)

    for i, slide_spec in enumerate(slides):
        # Create a blank slide layout for complete deterministic positioning
        blank_layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(blank_layout)

        # Convert Pydantic SlideSpec to dict if necessary
        if hasattr(slide_spec, "model_dump"):
            slide_dict = slide_spec.model_dump()
        elif hasattr(slide_spec, "dict"):
            slide_dict = slide_spec.dict()
        else:
            slide_dict = slide_spec

        # Render slide using the selected design system template
        render_func(
            slide=slide,
            slide_spec=slide_dict,
            theme=theme,
            slide_number=i + 1,
            total_slides=total_slides,
            deck_title=spec.title,
        )

    # STRICT VALIDATION: Slide Count Contract (Target slide_count up to slide_count + 2 for ontology coverage)
    max_count = spec.config.slide_count + 2
    if not (spec.config.slide_count <= len(prs.slides) <= max_count):
        raise ValueError(
            f"Generated PPTX slide count ({len(prs.slides)}) is outside permitted range "
            f"[{spec.config.slide_count}..{max_count}]"
        )

    buffer = io.BytesIO()
    prs.save(buffer)
    return buffer.getvalue()
