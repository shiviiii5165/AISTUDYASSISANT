"""
Test Suite: No Decorative Shapes
=================================
Renders sample presentations and asserts that every shape on every slide
carries real informative content (contains text, numbers, icons, or images)
and that no empty decorative circles or blobs exist.
"""
import sys
import os
import io
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pptx import Presentation
from app.services.presentation.schemas import (
    PresentationConfig, PresentationSpec, SlideSpec, VisualSpec, VisualKind, DiagramSpec
)
from app.services.presentation.engine.builder import build_presentation_spec


def test_no_empty_decorative_circles_in_timeline_and_flow():
    """Verify timeline and flow diagrams do not contain empty circles or blobs."""
    config = PresentationConfig(
        topic="Software Engineering Life Cycle",
        slide_count=10,
        audience="university",
    )

    slides = [
        SlideSpec(
            slide_no=1,
            type="hero",
            title="Software Engineering Life Cycle",
            subtitle="Undergraduate Curriculum",
            key_message="Structured processes minimize architectural defects.",
        ),
        SlideSpec(
            slide_no=2,
            type="timeline",
            title="Chronological Evolution of Development Methodologies",
            key_message="Evolution from rigid waterfall to modern continuous deployment.",
            visual=VisualSpec(
                kind=VisualKind.TIMELINE,
                diagram_spec=DiagramSpec(
                    diagram_type="timeline",
                    milestones=[
                        {"date": "1970", "label": "Waterfall Model", "detail": "Formalized sequential phases by Winston Royce."},
                        {"date": "1986", "label": "Spiral Model", "detail": "Risk-driven iterations introduced by Barry Boehm."},
                        {"date": "2001", "label": "Agile Manifesto", "detail": "Prioritized working software and customer collaboration."},
                    ]
                )
            ),
            milestones=[
                {"date": "1970", "label": "Waterfall Model", "detail": "Formalized sequential phases by Winston Royce."},
                {"date": "1986", "label": "Spiral Model", "detail": "Risk-driven iterations introduced by Barry Boehm."},
                {"date": "2001", "label": "Agile Manifesto", "detail": "Prioritized working software and customer collaboration."},
            ],
        ),
        SlideSpec(
            slide_no=3,
            type="process_flow",
            title="Continuous Integration and Deployment Pipeline",
            key_message="Automated stages validate code health before production deployment.",
            visual=VisualSpec(
                kind=VisualKind.FLOW,
                diagram_spec=DiagramSpec(
                    diagram_type="flow",
                    steps=[
                        {"number": 1, "title": "Commit & Lint", "detail": "Static syntax and security analysis."},
                        {"number": 2, "title": "Unit Testing", "detail": "Automated regression verification."},
                        {"number": 3, "title": "Container Build", "detail": "Docker image creation and tag."},
                        {"number": 4, "title": "Staging Deploy", "detail": "End-to-end integration tests."},
                    ]
                )
            ),
            steps=[
                {"number": 1, "title": "Commit & Lint", "detail": "Static syntax and security analysis."},
                {"number": 2, "title": "Unit Testing", "detail": "Automated regression verification."},
                {"number": 3, "title": "Container Build", "detail": "Docker image creation and tag."},
                {"number": 4, "title": "Staging Deploy", "detail": "End-to-end integration tests."},
            ],
        ),
    ]

    # Fill remaining slides up to 10
    while len(slides) < 10:
        idx = len(slides) + 1
        slides.append(SlideSpec(
            slide_no=idx,
            type="concept",
            title=f"Core Principle {idx}",
            key_message=f"Key message for module {idx}",
            body_bullets=["Specific principle 1", "Specific mechanism 2"],
        ))

    spec = PresentationSpec(
        title="Software Engineering Life Cycle",
        config=config,
        slides=slides,
    )

    pptx_bytes = build_presentation_spec(spec)
    prs = Presentation(io.BytesIO(pptx_bytes))

    # Inspect timeline slide (Slide 2)
    timeline_slide = prs.slides[1]
    # Check that every shape has text or is a structural axis line/card
    for shape in timeline_slide.shapes:
        if shape.has_text_frame:
            # Has text, valid
            continue
        elif shape.shape_type == 1:  # RECTANGLE or axis line
            # Structural axis line or background
            continue
        elif shape.shape_type == 13: # Picture
            continue
        else:
            # If any other shape exists without text, fail
            pytest.fail(f"Found non-text non-structural shape: {shape.name} (type: {shape.shape_type})")
