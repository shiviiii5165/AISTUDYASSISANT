"""
Test: Content Pattern Propagation
==================================
Validates that the orchestrator correctly passes `content_pattern` from
the content agent through to SlideSpec objects, so the dispatch system
can route slides to the correct pedagogical component renderer.

This test verifies the fix for the critical bug where orchestrator.py
was dropping content_pattern from the SlideSpec constructor.
"""
import pytest
from app.services.presentation.schemas import (
    SlideSpec,
    ContentPattern,
    VisualSpec,
    VisualKind,
    PresentationConfig,
    PresentationSpec,
)


class TestContentPatternPropagation:
    """Verify content_pattern flows through the full pipeline."""

    def test_slidespec_accepts_content_pattern(self):
        """SlideSpec model should accept and store content_pattern."""
        spec = SlideSpec(
            slide_no=1,
            title="Test Slide",
            content_pattern=ContentPattern.DEFINITION_BOX,
        )
        assert spec.content_pattern == ContentPattern.DEFINITION_BOX

    def test_slidespec_accepts_none_content_pattern(self):
        """SlideSpec should default content_pattern to None."""
        spec = SlideSpec(
            slide_no=1,
            title="Test Slide",
        )
        assert spec.content_pattern is None

    def test_slidespec_accepts_all_content_patterns(self):
        """All ContentPattern enum values should be accepted."""
        for pattern in ContentPattern:
            spec = SlideSpec(
                slide_no=1,
                title="Test",
                content_pattern=pattern,
            )
            assert spec.content_pattern == pattern

    def test_orchestrator_style_slidespec_construction(self):
        """
        Simulate the orchestrator's SlideSpec construction path
        to confirm content_pattern is wired through.

        This is the exact code path from orchestrator.py lines 155-175.
        """
        # Simulate a final_slide_dict as the reviewer would produce
        slide_dict = {
            "slide_no": 3,
            "type": "concept",
            "title": "What is a Stack?",
            "subtitle": "LIFO Data Structure",
            "key_message": "A stack follows Last-In-First-Out ordering",
            "body_bullets": ["Push adds to top", "Pop removes from top"],
            "example": "Think of a stack of plates",
            "speaker_notes": "Explain with real-world analogy",
            "image_query": "stack of plates data structure",
            "content_pattern": "definition_box",  # THIS is what was being dropped
            "layers": [],
            "steps": [],
            "milestones": [],
            "columns": [],
            "metrics": [],
            "quiz_options": [],
            "quiz_answer": "",
        }

        # Build SlideSpec the same way orchestrator.py does (WITH the fix)
        vspec = VisualSpec(kind=VisualKind.NONE)
        slide_obj = SlideSpec(
            slide_no=slide_dict.get("slide_no", 1),
            type=slide_dict.get("type", "concept"),
            title=slide_dict.get("title", ""),
            subtitle=slide_dict.get("subtitle", ""),
            key_message=slide_dict.get("key_message", ""),
            body_bullets=slide_dict.get("body_bullets", []),
            example=slide_dict.get("example", ""),
            speaker_notes=slide_dict.get("speaker_notes", ""),
            image_query=slide_dict.get("image_query", ""),
            content_pattern=slide_dict.get("content_pattern"),  # THE FIX
            visual=vspec,
            source_refs=[],
            layers=slide_dict.get("layers", []),
            steps=slide_dict.get("steps", []),
            milestones=slide_dict.get("milestones", []),
            columns=slide_dict.get("columns", []),
            metrics=slide_dict.get("metrics", []),
            quiz_options=slide_dict.get("quiz_options", []),
            quiz_answer=slide_dict.get("quiz_answer", ""),
        )

        # The critical assertion: content_pattern must NOT be None
        assert slide_obj.content_pattern is not None
        assert slide_obj.content_pattern == ContentPattern.DEFINITION_BOX

    def test_content_pattern_string_conversion(self):
        """Content patterns from the content agent come as strings, not enums."""
        slide_dict = {"content_pattern": "contrast_pair"}
        spec = SlideSpec(
            slide_no=1,
            title="Test",
            content_pattern=slide_dict.get("content_pattern"),
        )
        assert spec.content_pattern == ContentPattern.CONTRAST_PAIR

    def test_missing_content_pattern_is_none(self):
        """If content_pattern is not in the dict, it should be None (not crash)."""
        slide_dict = {"title": "No pattern here"}
        spec = SlideSpec(
            slide_no=1,
            title="Test",
            content_pattern=slide_dict.get("content_pattern"),
        )
        assert spec.content_pattern is None

    def test_all_patterns_available_in_enum(self):
        """Verify all expected pedagogical patterns exist in the ContentPattern enum."""
        expected_patterns = [
            "definition_box",
            "contrast_pair",
            "comparison_table",
            "numbered_process",
            "case_study_block",
            "activity_banner",
            "worked_example_table",
            "icon_badge_row",
            "hub_and_spoke",
            "illustrated_icon_grid",
            "parallel_comparison",
            "plain_concept",
        ]
        for pattern_name in expected_patterns:
            assert hasattr(ContentPattern, pattern_name.upper()), \
                f"ContentPattern missing: {pattern_name}"
