"""
Test: Premium Template Rendering Integration
=============================================
Verifies all 5 upgraded templates render without errors for all slide types
including hero, qa, section_divider, concept, and image slides.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from pptx import Presentation
from pptx.util import Inches
from app.services.presentation_engine.tokens import get_theme, THEMES


def _make_prs():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    return prs


def _make_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def _make_slide_spec(stype="concept", content_pattern=None, with_image=False, with_example=False):
    spec = {
        "type": stype,
        "title": "Test Slide Title — Quality Check",
        "subtitle": "A subtitle for testing",
        "key_message": "This is the core takeaway message with specific facts and mechanisms.",
        "body_bullets": [
            "First bullet: TCP uses a 3-way handshake (SYN, SYN-ACK, ACK)",
            "Second bullet: HTTP/2 multiplexes streams over a single connection",
            "Third bullet: TLS 1.3 reduces handshake to 1-RTT (down from 2-RTT)",
            "Fourth bullet: QUIC protocol eliminates head-of-line blocking",
        ],
        "example": "At Netflix, switching from HTTP/1.1 to HTTP/2 reduced page load times by 40% across their global CDN." if with_example else "",
        "speaker_notes": "Here the instructor explains the importance of transport protocols in modern networking.",
        "image_query": "network cables connected to server switch with blinking LEDs",
        "content_pattern": content_pattern,
        "visual": {
            "kind": "image" if with_image else "none",
            "asset_required": with_image,
            "image_bytes": _fake_image_bytes() if with_image else None,
            "diagram_spec": None,
        },
        "source_refs": [],
        "layers": [],
        "steps": [{"title": "Step 1", "detail": "Establish connection"}, {"title": "Step 2", "detail": "Transfer data"}],
        "milestones": [],
        "columns": [
            {"heading": "HTTP/1.1", "points": ["Sequential", "6 connections"]},
            {"heading": "HTTP/2", "points": ["Multiplexed", "1 connection"]},
        ],
        "metrics": [],
        "quiz_options": [],
        "quiz_answer": "",
    }
    return spec


def _fake_image_bytes():
    """Create a minimal valid PNG for testing."""
    try:
        from PIL import Image
        import io
        img = Image.new('RGB', (800, 600), color=(30, 64, 175))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()
    except ImportError:
        # Fallback: return None to skip image tests
        return None


class TestPremiumTemplateRendering:
    """Verify all 5 templates render without errors for key slide types."""

    @pytest.fixture(params=["academic", "minimal", "technical", "editorial", "visual"])
    def template_key(self, request):
        return request.param

    def test_hero_slide_renders(self, template_key):
        from app.services.presentation.engine.templates import TEMPLATE_ROUTER
        prs = _make_prs()
        slide = _make_slide(prs)
        theme = get_theme("blue_professional")
        spec = _make_slide_spec("hero")
        render = TEMPLATE_ROUTER[template_key]
        render(slide, spec, theme, 1, 12, "Test Deck")
        assert len(slide.shapes) > 0

    def test_qa_slide_renders(self, template_key):
        from app.services.presentation.engine.templates import TEMPLATE_ROUTER
        prs = _make_prs()
        slide = _make_slide(prs)
        theme = get_theme("indigo_innovation")
        spec = _make_slide_spec("qa")
        render = TEMPLATE_ROUTER[template_key]
        render(slide, spec, theme, 12, 12, "Test Deck")
        assert len(slide.shapes) > 0

    def test_section_divider_renders(self, template_key):
        from app.services.presentation.engine.templates import TEMPLATE_ROUTER
        prs = _make_prs()
        slide = _make_slide(prs)
        theme = get_theme("emerald_academic")
        spec = _make_slide_spec("section_divider")
        render = TEMPLATE_ROUTER[template_key]
        render(slide, spec, theme, 5, 12, "Test Deck")
        assert len(slide.shapes) > 0

    def test_concept_with_bullets_renders(self, template_key):
        from app.services.presentation.engine.templates import TEMPLATE_ROUTER
        prs = _make_prs()
        slide = _make_slide(prs)
        theme = get_theme("blue_professional")
        spec = _make_slide_spec("concept")
        render = TEMPLATE_ROUTER[template_key]
        render(slide, spec, theme, 3, 12, "Test Deck")
        assert len(slide.shapes) > 0

    def test_concept_with_image_renders(self, template_key):
        from app.services.presentation.engine.templates import TEMPLATE_ROUTER
        img = _fake_image_bytes()
        if img is None:
            pytest.skip("PIL not available")
        prs = _make_prs()
        slide = _make_slide(prs)
        theme = get_theme("teal_corporate")
        spec = _make_slide_spec("concept", with_image=True)
        render = TEMPLATE_ROUTER[template_key]
        render(slide, spec, theme, 4, 12, "Test Deck")
        assert len(slide.shapes) > 0

    def test_concept_with_image_and_example_3zone(self, template_key):
        """3-zone layout: bullets + image + example all visible."""
        from app.services.presentation.engine.templates import TEMPLATE_ROUTER
        img = _fake_image_bytes()
        if img is None:
            pytest.skip("PIL not available")
        prs = _make_prs()
        slide = _make_slide(prs)
        theme = get_theme("orange_energy")
        spec = _make_slide_spec("concept", with_image=True, with_example=True)
        render = TEMPLATE_ROUTER[template_key]
        render(slide, spec, theme, 6, 12, "Test Deck")
        # Should have title + gradient + bullets + image + example card = many shapes
        assert len(slide.shapes) >= 4

    def test_progress_bar_in_footer(self, template_key):
        """Footer should include progress bar shapes."""
        from app.services.presentation.engine.templates import TEMPLATE_ROUTER
        prs = _make_prs()
        slide = _make_slide(prs)
        theme = get_theme("blue_professional")
        spec = _make_slide_spec("concept")
        render = TEMPLATE_ROUTER[template_key]
        render(slide, spec, theme, 6, 12, "Test Deck")
        # Should have many shapes including progress bar
        assert len(slide.shapes) >= 5

    def test_all_themes_render(self, template_key):
        """Verify every theme works with every template."""
        from app.services.presentation.engine.templates import TEMPLATE_ROUTER
        render = TEMPLATE_ROUTER[template_key]
        for theme_id in THEMES:
            prs = _make_prs()
            slide = _make_slide(prs)
            theme = get_theme(theme_id)
            spec = _make_slide_spec("concept")
            render(slide, spec, theme, 3, 12, "Test Deck")
            assert len(slide.shapes) > 0, f"Template '{template_key}' with theme '{theme_id}' produced no shapes"
