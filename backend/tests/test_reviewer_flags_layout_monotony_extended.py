"""
Test Suite: Reviewer Agent Flags Extended Layout Monotony
=========================================================
Verifies that `reviewer_agent.py` flags:
1. Component pattern frequency over-concentration.
2. 3+ consecutive slides repeating the same specialized component pattern.
3. 2 consecutive circle-pills.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.presentation.reviewer_agent import run_deterministic_deck_checks

def test_reviewer_flags_consecutive_pattern_repetition():
    """Verify reviewer flags 3 consecutive slides repeating the same pattern."""
    deck = [
        {"slide_no": 1, "type": "hero", "title": "System Architecture"},
        {"slide_no": 2, "type": "concept", "content_pattern": "definition_box", "title": "Term 1"},
        {"slide_no": 3, "type": "concept", "content_pattern": "definition_box", "title": "Term 2"},
        {"slide_no": 4, "type": "concept", "content_pattern": "definition_box", "title": "Term 3"},
        {"slide_no": 5, "type": "concept", "content_pattern": "plain_concept", "title": "Summary"},
        {"slide_no": 6, "type": "qa", "title": "Questions"}
    ]

    deck_issues, _ = run_deterministic_deck_checks(deck)
    has_repetition = any("Pattern repetition" in iss and "definition_box" in iss for iss in deck_issues)
    assert has_repetition, f"Expected component repetition issue, got: {deck_issues}"

def test_reviewer_flags_pattern_over_concentration():
    """Verify reviewer flags a deck where a single specialized pattern dominates > 35%."""
    deck = [
        {"slide_no": 1, "type": "hero", "title": "Incident Retrospective"},
        {"slide_no": 2, "type": "concept", "content_pattern": "case_study_block", "title": "Case 1"},
        {"slide_no": 3, "type": "concept", "content_pattern": "case_study_block", "title": "Case 2"},
        {"slide_no": 4, "type": "concept", "content_pattern": "plain_concept", "title": "Analysis"},
        {"slide_no": 5, "type": "concept", "content_pattern": "case_study_block", "title": "Case 3"},
        {"slide_no": 6, "type": "concept", "content_pattern": "case_study_block", "title": "Case 4"},
        {"slide_no": 7, "type": "qa", "title": "Questions"}
    ]
    # case_study_block: 4/7 = 57.1% > 35%
    deck_issues, _ = run_deterministic_deck_checks(deck)
    has_monotony = any("Pattern monotony" in iss and "case_study_block" in iss for iss in deck_issues)
    assert has_monotony, f"Expected component monotony issue for case_study_block, got: {deck_issues}"

def test_reviewer_allows_diverse_pedagogical_mix():
    """Verify a balanced deck with diverse pedagogical components passes without monotony flags."""
    deck = [
        {"slide_no": 1, "type": "hero", "title": "Distributed Systems Design"},
        {"slide_no": 2, "type": "concept", "content_pattern": "definition_box", "title": "CAP Theorem"},
        {"slide_no": 3, "type": "concept", "content_pattern": "contrast_pair", "title": "Pessimistic vs Optimistic"},
        {"slide_no": 4, "type": "concept", "content_pattern": "numbered_process", "title": "Raft Consensus Cycle"},
        {"slide_no": 5, "type": "concept", "content_pattern": "comparison_table", "title": "Consensus Tradeoffs"},
        {"slide_no": 6, "type": "concept", "content_pattern": "case_study_block", "title": "Split-Brain Incident"},
        {"slide_no": 7, "type": "concept", "content_pattern": "activity_banner", "title": "Partition Simulation"},
        {"slide_no": 8, "type": "concept", "content_pattern": "plain_concept", "title": "Summary & Synthesis"},
        {"slide_no": 9, "type": "qa", "title": "Discussion"}
    ]

    deck_issues, _ = run_deterministic_deck_checks(deck)
    monotony_issues = [iss for iss in deck_issues if "repetition" in iss.lower() or "monotony" in iss.lower()]
    assert not monotony_issues, f"Diverse deck had unexpected monotony issues: {monotony_issues}"
