"""
Test Suite: Component Selection Matches Content Semantics
=========================================================
Verifies that 6 distinct slide content signals (definition, misconception/contrast,
process, case study, comparison table, activity) map directly to their pedagogical
pattern and matching renderer.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.presentation.content_agent import detect_content_pattern_fallback_dict
from app.services.presentation_engine.layout_engine import CONTENT_PATTERN_MAP

TEST_SIGNALS = [
    (
        {
            "title": "Formal Definition: ACID Transaction Properties",
            "body_bullets": ["A set of database properties guaranteeing valid execution."],
            "example": "Bank fund transfer debiting account A and crediting account B."
        },
        "definition_box"
    ),
    (
        {
            "title": "The Trap: Microservices Premature Optimization",
            "body_bullets": [
                "Common Misconception: Breaking systems into services solves scaling early.",
                "The Discipline: Build modular monolith until domain boundaries solidify."
            ]
        },
        "contrast_pair"
    ),
    (
        {
            "title": "CI/CD Pipeline: 4-Stage Execution Workflow",
            "body_bullets": [
                "Step 1: Linting and static analysis verification",
                "Step 2: Unit test and coverage validation",
                "Step 3: Staging environment container deployment"
            ]
        },
        "numbered_process"
    ),
    (
        {
            "title": "Production Incident Case Study: Cache Stampede",
            "key_insight": "Sudden TTL expiry on 50,000 keys simultaneously crashed Postgres primary.",
            "body_bullets": [
                "System Context: Redis caching without jitter.",
                "Engineering Response: Added randomized TTL and singleflight locking."
            ],
            "example": "Singleflight eliminated 99.8% of redundant database queries during peak."
        },
        "case_study_block"
    ),
    (
        {
            "title": "Comparison Matrix: SQL vs NoSQL Data Stores",
            "columns": [
                {"heading": "Relational (SQL)", "points": ["ACID transactions", "Fixed schema"]},
                {"heading": "Document (NoSQL)", "points": ["Eventual consistency", "Dynamic schema"]}
            ]
        },
        "comparison_table"
    ),
    (
        {
            "title": "Classroom Activity: Thread Deadlock Discovery",
            "body_bullets": [
                "Step 1: Inspect lock order acquisition across thread A and B.",
                "Step 2: Propose lock hierarchy ordering rule to break cyclic wait."
            ]
        },
        "activity_banner"
    ),
    (
        {
            "title": "General Conceptual Overview of Operating Systems",
            "body_bullets": [
                "Kernel manages CPU scheduling and process lifecycle.",
                "Virtual memory maps logical pages to physical frames."
            ]
        },
        "plain_concept"
    )
]

def test_semantic_signal_detection_and_renderer_mapping():
    """Verify each content signal maps to the expected pedagogical component and renderer."""
    for slide_data, expected_pattern in TEST_SIGNALS:
        detected = detect_content_pattern_fallback_dict(slide_data)
        assert detected == expected_pattern, (
            f"For slide '{slide_data['title']}', expected pattern '{expected_pattern}', got '{detected}'"
        )
        assert expected_pattern in CONTENT_PATTERN_MAP, (
            f"Pattern '{expected_pattern}' is not registered in CONTENT_PATTERN_MAP!"
        )
        renderer = CONTENT_PATTERN_MAP[expected_pattern]
        assert callable(renderer), f"Renderer for '{expected_pattern}' must be callable"
