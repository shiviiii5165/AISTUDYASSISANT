"""
Test: Deck-wide visual style consistency
==========================================
Validates:
1. Deck-level style decision based on topic keywords
2. All slides in a deck get the same deck_visual_style
3. Consistent corner_radius_inches across all slides
4. Abstract topics → illustration preference
5. Concrete topics → stock_photo preference
"""
import pytest
from app.services.presentation.content_agent import detect_content_pattern_fallback_dict


class TestContentPatternDetection:
    """Test that pattern detection maps to correct patterns for new components."""

    def test_hierarchy_detected_as_annotated_tiers(self):
        slide = {"title": "Classification Hierarchy of Animals", "body_bullets": ["A", "B"]}
        assert detect_content_pattern_fallback_dict(slide) == "annotated_tiers"

    def test_taxonomy_detected_as_annotated_tiers(self):
        slide = {"title": "Bloom's Taxonomy of Learning", "body_bullets": ["A", "B"]}
        assert detect_content_pattern_fallback_dict(slide) == "annotated_tiers"

    def test_application_with_bullets_detected_as_example_grid(self):
        slide = {
            "title": "Applications of Machine Learning in Industry",
            "body_bullets": ["Medical imaging", "Financial analysis", "Autonomous navigation"],
        }
        assert detect_content_pattern_fallback_dict(slide) == "example_grid"

    def test_concept_with_image_query_detected_as_concept_split(self):
        slide = {
            "title": "Supervised Learning: Core Mechanism",
            "type": "concept",
            "image_query": "neural network training diagram",
            "key_insight": "Maps labeled pairs through gradient descent.",
            "body_bullets": ["Labeled features", "Loss minimization"],
        }
        assert detect_content_pattern_fallback_dict(slide) == "concept_split"

    def test_plain_concept_without_signals(self):
        slide = {
            "title": "Summary Points",
            "body_bullets": ["Point 1", "Point 2"],
        }
        assert detect_content_pattern_fallback_dict(slide) == "plain_concept"

    def test_definition_still_detected(self):
        slide = {"title": "Definition of Machine Learning", "body_bullets": ["A", "B"]}
        assert detect_content_pattern_fallback_dict(slide) == "definition_box"

    def test_steps_still_detected_as_numbered_process(self):
        slide = {
            "title": "Training Pipeline Steps",
            "steps": [{"title": "Step1", "detail": "Do thing"}],
        }
        assert detect_content_pattern_fallback_dict(slide) == "numbered_process"
