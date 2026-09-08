"""
Test: Numbered list variant selection by template
===================================================
Validates:
1. Default (non-minimal/editorial) themes → circular badge variant
2. Minimal/editorial themes → thin rule variant
3. Both variants render correct step count
"""
import pytest
from pptx import Presentation
from app.services.presentation_engine.tokens import SLIDE_WIDTH, SLIDE_HEIGHT, get_theme
from app.services.presentation_engine import SlideContent, ProcessStep
from app.services.presentation_engine.renderers.numbered_process import render_numbered_process


@pytest.fixture
def prs():
    p = Presentation()
    p.slide_width = SLIDE_WIDTH
    p.slide_height = SLIDE_HEIGHT
    return p


def _count_text_shapes_containing(slide, text):
    count = 0
    for shape in slide.shapes:
        if shape.has_text_frame and text in shape.text_frame.text:
            count += 1
    return count


def _make_steps():
    return [
        ProcessStep(number=1, title="Collect", detail="Gather data"),
        ProcessStep(number=2, title="Process", detail="Transform data"),
        ProcessStep(number=3, title="Validate", detail="Verify results"),
    ]


def test_circular_badge_variant_by_default(prs):
    """Blue professional theme → circular badge variant (no prefer_thin_rule)."""
    theme = get_theme("blue_professional")
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    content = SlideContent(title="Data Pipeline", steps=_make_steps())
    render_numbered_process(slide, content, theme, prefer_thin_rule=False)

    # All 3 step titles should be present
    assert _count_text_shapes_containing(slide, "Collect") >= 1
    assert _count_text_shapes_containing(slide, "Process") >= 1
    assert _count_text_shapes_containing(slide, "Validate") >= 1


def test_thin_rule_variant_when_preferred(prs):
    """Minimal charcoal theme with prefer_thin_rule=True → numeral variant."""
    theme = get_theme("minimal_charcoal")
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    content = SlideContent(title="Analysis Steps", steps=_make_steps())
    render_numbered_process(slide, content, theme, prefer_thin_rule=True)

    # Should contain "01", "02", "03" numeral texts
    assert _count_text_shapes_containing(slide, "01") >= 1
    assert _count_text_shapes_containing(slide, "02") >= 1
    assert _count_text_shapes_containing(slide, "03") >= 1


def test_both_variants_render_same_step_titles(prs):
    """Both variants should render all step titles regardless of visual style."""
    for thin_rule in [True, False]:
        theme = get_theme("blue_professional")
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        content = SlideContent(title="Pipeline", steps=_make_steps())
        render_numbered_process(slide, content, theme, prefer_thin_rule=thin_rule)

        for step in ["Collect", "Process", "Validate"]:
            assert _count_text_shapes_containing(slide, step) >= 1, \
                f"Step '{step}' not found in {'thin_rule' if thin_rule else 'badge'} variant"
