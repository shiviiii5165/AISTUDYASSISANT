"""
Test Suite: Circle-Pill (Parallel Comparison) Usage Capped
==========================================================
Verifies that circle-pill comparison layouts:
1. Are capped at <= 25% of any generated deck.
2. Are never repeated on 2+ consecutive slides.
3. Reviewer Agent strictly flags any deck violating these bounds.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.presentation.reviewer_agent import run_deterministic_deck_checks

def test_circle_pill_usage_capped_at_25_percent():
    """Verify reviewer flags decks where circle-pill comparison exceeds 25%."""
    # 12-slide deck with 4 circle-pills (33.3% > 25%)
    deck_overused = [
        {"slide_no": 1, "type": "hero", "title": "System Design"},
        {"slide_no": 2, "type": "concept", "content_pattern": "definition_box", "title": "Definition"},
        {"slide_no": 3, "type": "comparison", "content_pattern": "parallel_comparison", "title": "Compare 1"},
        {"slide_no": 4, "type": "concept", "content_pattern": "plain_concept", "title": "Concept A"},
        {"slide_no": 5, "type": "comparison", "content_pattern": "parallel_comparison", "title": "Compare 2"},
        {"slide_no": 6, "type": "concept", "content_pattern": "plain_concept", "title": "Concept B"},
        {"slide_no": 7, "type": "comparison", "content_pattern": "parallel_comparison", "title": "Compare 3"},
        {"slide_no": 8, "type": "concept", "content_pattern": "plain_concept", "title": "Concept C"},
        {"slide_no": 9, "type": "comparison", "content_pattern": "parallel_comparison", "title": "Compare 4"},
        {"slide_no": 10, "type": "concept", "content_pattern": "plain_concept", "title": "Concept D"},
        {"slide_no": 11, "type": "concept", "content_pattern": "plain_concept", "title": "Concept E"},
        {"slide_no": 12, "type": "qa", "title": "Questions"}
    ]

    deck_issues, _ = run_deterministic_deck_checks(deck_overused)
    has_cap_issue = any("Circle-pill comparison overuse" in issue for issue in deck_issues)
    assert has_cap_issue, f"Expected circle-pill overuse issue, got: {deck_issues}"

def test_consecutive_circle_pills_flagged():
    """Verify reviewer flags decks where 2 consecutive slides use circle-pills."""
    deck_consecutive = [
        {"slide_no": 1, "type": "hero", "title": "System Design"},
        {"slide_no": 2, "type": "comparison", "content_pattern": "parallel_comparison", "title": "Compare 1"},
        {"slide_no": 3, "type": "comparison", "content_pattern": "parallel_comparison", "title": "Compare 2"},
        {"slide_no": 4, "type": "concept", "content_pattern": "plain_concept", "title": "Concept"},
        {"slide_no": 5, "type": "qa", "title": "Questions"}
    ]

    deck_issues, _ = run_deterministic_deck_checks(deck_consecutive)
    has_consecutive_issue = any("Consecutive circle-pill" in issue for issue in deck_issues)
    assert has_consecutive_issue, f"Expected consecutive circle-pill issue, got: {deck_issues}"

def test_compliant_deck_passes_cap_check():
    """Verify a compliant deck with <= 25% pills passes without flags."""
    deck_compliant = [
        {"slide_no": 1, "type": "hero", "title": "System Design"},
        {"slide_no": 2, "type": "concept", "content_pattern": "definition_box", "title": "Definition"},
        {"slide_no": 3, "type": "concept", "content_pattern": "contrast_pair", "title": "Pitfalls vs Practice"},
        {"slide_no": 4, "type": "concept", "content_pattern": "numbered_process", "title": "Workflow Steps"},
        {"slide_no": 5, "type": "comparison", "content_pattern": "parallel_comparison", "title": "Compare 1"},
        {"slide_no": 6, "type": "concept", "content_pattern": "plain_concept", "title": "Concept"},
        {"slide_no": 7, "type": "concept", "content_pattern": "plain_concept", "title": "Summary"},
        {"slide_no": 8, "type": "qa", "title": "Questions"}
    ]
    deck_issues, _ = run_deterministic_deck_checks(deck_compliant)
    pill_issues = [iss for iss in deck_issues if "circle-pill" in iss.lower()]
    assert not pill_issues, f"Compliant deck was unexpectedly flagged: {pill_issues}"
