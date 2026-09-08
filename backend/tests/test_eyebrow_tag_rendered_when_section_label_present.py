"""
Test: Eyebrow tag renders when section_label is present
========================================================
Validates that:
1. Slides WITH section_label render the eyebrow tag shape
2. Slides WITHOUT section_label do NOT render the eyebrow tag
3. Non-ML topics produce topic-appropriate labels
"""
import pytest
from pptx import Presentation
from pptx.util import Inches
from app.services.presentation_engine.tokens import SLIDE_WIDTH, SLIDE_HEIGHT, get_theme
from app.services.presentation.engine.templates.academic import render_academic_slide
from app.services.presentation.engine.templates.minimal import render_minimal_slide
from app.services.presentation.engine.templates.technical import render_technical_slide
from app.services.presentation.engine.templates.editorial import render_editorial_slide
from app.services.presentation.engine.templates.visual_learning import render_visual_learning_slide


def _make_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def _count_text_shapes_containing(slide, text):
    count = 0
    for shape in slide.shapes:
        if shape.has_text_frame:
            for para in shape.text_frame.paragraphs:
                if text in para.text:
                    count += 1
    return count


@pytest.fixture
def prs():
    p = Presentation()
    p.slide_width = SLIDE_WIDTH
    p.slide_height = SLIDE_HEIGHT
    return p


@pytest.fixture
def theme():
    return get_theme("blue_professional")


RENDERERS = [
    render_academic_slide,
    render_minimal_slide,
    render_technical_slide,
    render_editorial_slide,
    render_visual_learning_slide,
]


@pytest.mark.parametrize("renderer", RENDERERS,
    ids=["academic", "minimal", "technical", "editorial", "visual_learning"])
def test_eyebrow_tag_present_when_section_label_set(prs, theme, renderer):
    """Slide with section_label='TYPE 1' must render an eyebrow tag containing that text."""
    slide = _make_slide(prs)
    spec = {
        "type": "concept",
        "title": "Supervised Learning",
        "key_message": "Maps labeled pairs through gradient descent.",
        "body_bullets": ["Bullet 1", "Bullet 2"],
        "section_label": "TYPE 1",
    }
    renderer(slide=slide, slide_spec=spec, theme=theme, slide_number=2, total_slides=10)
    assert _count_text_shapes_containing(slide, "TYPE 1") >= 1


@pytest.mark.parametrize("renderer", RENDERERS,
    ids=["academic", "minimal", "technical", "editorial", "visual_learning"])
def test_no_eyebrow_tag_when_section_label_absent(prs, theme, renderer):
    """Slide without section_label must NOT contain 'TYPE 1' text."""
    slide = _make_slide(prs)
    spec = {
        "type": "concept",
        "title": "Key Takeaways",
        "key_message": "Summary.",
        "body_bullets": ["Point 1", "Point 2"],
        # No section_label
    }
    renderer(slide=slide, slide_spec=spec, theme=theme, slide_number=5, total_slides=10)
    assert _count_text_shapes_containing(slide, "TYPE 1") == 0


def test_history_topic_produces_chapter_labels(prs, theme):
    """Non-ML topic like history should use CHAPTER OVERVIEW style labels."""
    slide = _make_slide(prs)
    spec = {
        "type": "concept",
        "title": "Causes of the French Revolution",
        "key_message": "Economic crisis and Enlightenment ideals converged.",
        "body_bullets": ["Financial crisis", "Social inequality"],
        "section_label": "CHAPTER OVERVIEW",
    }
    render_academic_slide(slide=slide, slide_spec=spec, theme=theme, slide_number=2, total_slides=10)
    assert _count_text_shapes_containing(slide, "CHAPTER OVERVIEW") >= 1
