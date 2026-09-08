"""
Test: Concept split falls back cleanly when no image available
===============================================================
Validates:
1. With image bytes → split layout renders (image + text)
2. Without image → text-only fallback renders
3. Both variants produce valid shapes without errors
"""
import pytest
from pptx import Presentation
from PIL import Image
import io
from app.services.presentation_engine.tokens import SLIDE_WIDTH, SLIDE_HEIGHT, get_theme
from app.services.presentation_engine import SlideContent
from app.services.presentation_engine.renderers.concept_split import render_concept_split


@pytest.fixture
def prs():
    p = Presentation()
    p.slide_width = SLIDE_WIDTH
    p.slide_height = SLIDE_HEIGHT
    return p


@pytest.fixture
def theme():
    return get_theme("blue_professional")


@pytest.fixture
def fake_image_bytes():
    img = Image.new("RGB", (400, 300), color=(45, 100, 180))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_concept_split_with_image_renders(prs, theme, fake_image_bytes):
    """Concept split with image_bytes should produce more shapes (image + text)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    content = SlideContent(
        title="Supervised Learning: Core Mechanism",
        key_insight="Maps labeled pairs through gradient descent.",
        body_bullets=["Training data: labeled features", "Gradient Descent: minimizes loss"],
        image_bytes=fake_image_bytes,
    )
    render_concept_split(slide, content, theme, slide_number=1, total_slides=5)
    assert len(slide.shapes) >= 5  # background + accent bar + title + image + definition


def test_concept_split_without_image_fallback(prs, theme):
    """Concept split without image should fallback to text-only layout without errors."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    content = SlideContent(
        title="Unsupervised Learning",
        key_insight="Discovers hidden patterns in unlabeled data.",
        body_bullets=["No labels needed", "Clustering groups similar points"],
    )
    render_concept_split(slide, content, theme, slide_number=2, total_slides=5)
    assert len(slide.shapes) >= 4  # background + accent bar + title + card


def test_concept_split_title_always_present(prs, theme, fake_image_bytes):
    """Title should be rendered in both variants."""
    for has_img in [True, False]:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        content = SlideContent(
            title="Test Title",
            key_insight="Test insight.",
            body_bullets=["Bullet 1", "Bullet 2"],
            image_bytes=fake_image_bytes if has_img else None,
        )
        render_concept_split(slide, content, theme)
        title_found = any(
            s.has_text_frame and "Test Title" in s.text_frame.text
            for s in slide.shapes
        )
        assert title_found, f"Title not found in {'image' if has_img else 'no-image'} variant"
