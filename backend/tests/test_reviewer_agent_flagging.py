"""
Test Suite: Reviewer Agent Flagging
====================================
Injects an incomplete or redundant deck spec, verifying that the
Reviewer Agent correctly catches defects and flags the offending slide indices.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.presentation.schemas import PresentationConfig, VisualKind
from app.services.presentation.topic_ontology_agent import TopicOntologyChecklist
from app.services.presentation.reviewer_agent import (
    run_deterministic_deck_checks, run_reviewer_critic
)


def test_deterministic_pre_checks_flag_missing_subtopic():
    """Verify pre-checks catch missing core subtopics."""
    ontology = TopicOntologyChecklist(
        core_subtopics=[
            "Foundational Theory",
            "Hardware Accelerators",
            "Quantization and Pruning",
        ],
        must_include=[],
    )

    # Deck only covers Theory and Accelerators, completely omits Quantization
    slides = [
        {"slide_no": 1, "type": "hero", "title": "Model Optimization", "body_bullets": []},
        {"slide_no": 2, "type": "concept", "title": "Foundational Theory", "body_bullets": ["Theory principles."]},
        {"slide_no": 3, "type": "concept", "title": "Hardware Accelerators", "body_bullets": ["TPU architectures."]},
        {"slide_no": 4, "type": "qa", "title": "Questions", "body_bullets": []},
    ]

    deck_issues, slide_issues = run_deterministic_deck_checks(slides, ontology)
    assert any("Quantization" in issue for issue in deck_issues), f"Expected missing Quantization flag, got: {deck_issues}"


def test_deterministic_pre_checks_flag_layout_repetition():
    """Verify pre-checks catch 3 consecutive identical slide types."""
    slides = [
        {"slide_no": 1, "type": "hero", "title": "Hero", "body_bullets": []},
        {"slide_no": 2, "type": "summary", "title": "Concept 1", "body_bullets": ["A"]},
        {"slide_no": 3, "type": "summary", "title": "Concept 2", "body_bullets": ["B"]},
        {"slide_no": 4, "type": "summary", "title": "Concept 3", "body_bullets": ["C"]},
        {"slide_no": 5, "type": "qa", "title": "QA", "body_bullets": []},
    ]

    deck_issues, slide_issues = run_deterministic_deck_checks(slides)
    assert any("Layout repetition" in issue for issue in deck_issues), f"Expected layout repetition flag, got: {deck_issues}"


def test_deterministic_pre_checks_flag_missing_image_bytes():
    """Verify pre-checks catch silent image omissions."""
    slides = [
        {
            "slide_no": 2,
            "type": "image_insight",
            "title": "Satellite Imagery Analysis",
            "visual_spec": {"kind": "image", "asset_required": True, "image_bytes": None},
            "body_bullets": ["Satellite data processing"],
        }
    ]

    deck_issues, slide_issues = run_deterministic_deck_checks(slides)
    assert 2 in slide_issues, "Slide 2 should be flagged for missing image_bytes"
    assert any("image bytes were omitted" in iss for iss in slide_issues[2])
