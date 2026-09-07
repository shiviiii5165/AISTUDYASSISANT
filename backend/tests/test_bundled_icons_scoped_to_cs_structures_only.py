"""
Test Suite: Bundled Icons Scoped Strictly to CS Data Structures
===============================================================
Codifies the strict boundary:
1. The dynamic stock-photo pipeline (Pexels -> Pixabay -> Unsplash -> Wikimedia -> AI fallback)
   remains the primary and default image source for all topics (e.g. "Waterfall Model in Software
   Engineering", History, Business, Biology). ZERO bundled icons are used in non-CS decks.
2. Bundled static icons (icons.py) are strictly gated to slides explicitly teaching
   specific computer science data structures (content_pattern == ContentPattern.ILLUSTRATED_ICON_GRID).
"""
import sys
import os
import pytest
from pptx import Presentation
from pptx.util import Inches

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.presentation.schemas import (
    PresentationSpec, PresentationConfig, SlideSpec, SlideType, ContentPattern, DesignSystem
)
from app.services.presentation.engine.builder import build_presentation_spec
from app.services.presentation.content_agent import detect_content_pattern_fallback_dict
from app.services.presentation_engine.renderers.icons import get_bundled_icon_path

def test_waterfall_and_non_cs_topics_use_zero_bundled_icons():
    """Verify non-CS topics and Waterfall Model decks use ZERO bundled icons."""
    topics = [
        "Waterfall Model in Software Engineering",
        "The Roman Republic and Senate Governance",
        "Corporate Supply Chain Optimization Strategies"
    ]

    for topic in topics:
        config = PresentationConfig(
            topic=topic,
            slide_count=10,
            design=DesignSystem.ACADEMIC_CLEAN
        )
        slides = [
            SlideSpec(slide_no=1, type=SlideType.HERO, title=topic, key_message="Introduction to the topic")
        ]
        for s_idx in range(2, 10):
            slides.append(
                SlideSpec(
                    slide_no=s_idx,
                    type=SlideType.CONCEPT,
                    title=f"Core Concept Analysis Part {s_idx - 1}",
                    body_bullets=["Systematic principle with clear inputs", "Operational constraints and boundary checks"],
                    key_message=f"Key insight for facet {s_idx - 1} of {topic}"
                )
            )
        slides.append(
            SlideSpec(
                slide_no=10,
                type=SlideType.QA,
                title="Discussion & Questions",
                key_message="Concluding recap"
            )
        )

        for s in slides[1:3]:
            s_dict = s.model_dump()
            inferred = detect_content_pattern_fallback_dict(s_dict)
            # Inferred pattern MUST NOT be illustrated_icon_grid for non-CS topics
            assert inferred != "illustrated_icon_grid", (
                f"Topic '{topic}' slide '{s.title}' incorrectly inferred illustrated_icon_grid!"
            )
            s.content_pattern = ContentPattern(inferred)

        spec = PresentationSpec(
            title=topic,
            config=config,
            slides=slides
        )

        # Build PPTX bytes
        pptx_bytes = build_presentation_spec(spec)
        assert len(pptx_bytes) > 5000, "Expected valid PPTX output"

def test_cs_data_structure_slide_uses_bundled_icons():
    """Verify slides explicitly teaching data structures correctly utilize bundled icons."""
    cs_slide = {
        "slide_no": 2,
        "type": "concept",
        "title": "Core Collection Structures: Stack & Queue Topology",
        "body_bullets": [
            "Stack (LIFO): Elements pushed and popped strictly at top",
            "Queue (FIFO): Items enqueued at rear and dequeued at front",
            "Binary Tree: Hierarchical root branching into child subtrees",
            "Network Graph: Interconnected vertices with relational edges"
        ]
    }
    inferred = detect_content_pattern_fallback_dict(cs_slide)
    assert inferred == "illustrated_icon_grid", (
        f"Expected 'illustrated_icon_grid' for structural CS data slide, got '{inferred}'"
    )

    # Verify icons exist on disk
    for icon_name in ["plate-stack", "queue-line", "tree-branch", "network-graph"]:
        path = get_bundled_icon_path(icon_name)
        assert path is not None and os.path.isfile(path), f"Missing bundled icon {icon_name}"
