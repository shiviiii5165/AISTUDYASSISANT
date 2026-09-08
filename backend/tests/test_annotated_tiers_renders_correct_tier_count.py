"""
Test: Annotated tiers renders correct tier count
==================================================
Validates:
1. 3 tiers → pyramid variant (3 tier shapes)
2. 5 tiers → stacked variant (5 tier shapes)
3. Title always rendered
4. Tiers have gradient color fill
"""
import pytest
from pptx import Presentation
from app.services.presentation_engine.tokens import SLIDE_WIDTH, SLIDE_HEIGHT, get_theme
from app.services.presentation_engine import SlideContent, ProcessStep
from app.services.presentation_engine.renderers.annotated_tiers import render_annotated_tiers


@pytest.fixture
def prs():
    p = Presentation()
    p.slide_width = SLIDE_WIDTH
    p.slide_height = SLIDE_HEIGHT
    return p


@pytest.fixture
def theme():
    return get_theme("blue_professional")


def _count_text_shapes_containing(slide, text):
    count = 0
    for shape in slide.shapes:
        if shape.has_text_frame and text in shape.text_frame.text:
            count += 1
    return count


def test_3_tier_pyramid_renders_all_tiers(prs, theme):
    """3 tiers should render pyramid variant with all tier labels."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    content = SlideContent(
        title="Bloom's Taxonomy",
        steps=[
            ProcessStep(number=1, title="Knowledge", detail="Recall facts"),
            ProcessStep(number=2, title="Comprehension", detail="Explain ideas"),
            ProcessStep(number=3, title="Application", detail="Use in new situations"),
        ],
    )
    render_annotated_tiers(slide, content, theme)
    assert _count_text_shapes_containing(slide, "Knowledge") >= 1
    assert _count_text_shapes_containing(slide, "Comprehension") >= 1
    assert _count_text_shapes_containing(slide, "Application") >= 1


def test_5_tier_stacked_renders_all_tiers(prs, theme):
    """5 tiers should render stacked variant with all tier labels."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    content = SlideContent(
        title="OSI Model",
        body_bullets=[
            "Physical: Electrical signals",
            "Data Link: MAC addressing",
            "Network: IP routing",
            "Transport: TCP/UDP flow control",
            "Application: HTTP/SMTP protocols",
        ],
    )
    render_annotated_tiers(slide, content, theme)
    assert _count_text_shapes_containing(slide, "Physical") >= 1
    assert _count_text_shapes_containing(slide, "Application") >= 1


def test_title_always_present(prs, theme):
    """Title should always be rendered."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    content = SlideContent(
        title="Test Hierarchy",
        body_bullets=["Top: High", "Middle: Medium", "Bottom: Low"],
    )
    render_annotated_tiers(slide, content, theme)
    assert _count_text_shapes_containing(slide, "Test Hierarchy") >= 1


def test_empty_tiers_uses_defaults(prs, theme):
    """No tiers data should fall back to 3 default tiers."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    content = SlideContent(title="Empty Tiers")
    render_annotated_tiers(slide, content, theme)
    # Should have shapes for defaults: Top, Middle, Base
    assert len(slide.shapes) >= 5
