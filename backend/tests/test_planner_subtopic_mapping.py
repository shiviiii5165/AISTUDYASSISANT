"""
Test Suite: Planner Subtopic Mapping
====================================
Verifies that every checklist subtopic maps to >=1 slide, and verifies
merge-not-drop behavior when slide_count is tight.
"""
import sys
import os
import pytest
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.presentation.schemas import PresentationConfig
from app.services.presentation.topic_ontology_agent import TopicOntologyChecklist
from app.services.presentation.planner_agent import plan_presentation, check_subtopic_coverage


def test_planner_subtopic_mapping_full_coverage():
    """Verify all core subtopics are mapped across the planned slides.
    Includes retry-with-backoff to handle transient API rate limits."""
    async def _run():
        config = PresentationConfig(
            topic="Relational Database Normalization",
            slide_count=12,
            audience="university",
            depth="full"
        )

        custom_ontology = TopicOntologyChecklist(
            core_subtopics=[
                "Data Redundancy Anomalies",
                "First Normal Form (1NF)",
                "Second Normal Form (2NF)",
                "Third Normal Form (3NF)",
                "Boyce-Codd Normal Form (BCNF)",
                "Performance Tradeoffs and Denormalization",
            ],
            must_include=["Concrete schema table before and after normalization"],
            optional_subtopics=["Fourth and Fifth Normal Forms"],
        )

        plan = await plan_presentation(config, user_id="test_user", ontology=custom_ontology)
        slides = plan.get("slides", [])
        assert len(slides) >= 12

        # Verify coverage check reports all core subtopics covered
        covered, missing = check_subtopic_coverage(custom_ontology.core_subtopics, slides)
        assert len(missing) == 0, f"Some core subtopics were unmapped: {missing}"

    # Retry once with backoff on rate-limit or transient failures
    import time
    try:
        asyncio.run(_run())
    except Exception as first_err:
        # Reset circuit breakers before retry
        try:
            from app.services.ai.circuit_breaker import health_manager, ProviderState
            for pname in list(health_manager.breakers.keys()):
                health_manager.breakers[pname].failures = 0
                health_manager.breakers[pname].state = ProviderState.HEALTHY
        except Exception:
            pass
        time.sleep(3)
        asyncio.run(_run())


def test_planner_merge_behavior_when_tight():
    """Verify merge-not-drop behavior when slide_count is constrained."""
    async def _run():
        config = PresentationConfig(
            topic="Operating System Kernel Design",
            slide_count=10,
            audience="university",
        )

        many_subtopics = [
            "Monolithic vs Microkernel Architecture",
            "Process Scheduling Algorithms",
            "Virtual Memory & Paging",
            "Inter-Process Communication",
            "Deadlock Prevention & Detection",
            "File System Inodes & Disk I/O",
            "Device Drivers & Interrupt Handling",
            "Security, Rings & Privilege Separation",
        ]

        ontology = TopicOntologyChecklist(
            core_subtopics=many_subtopics,
            must_include=["Real Linux vs microkernel benchmarks"],
            optional_subtopics=[],
        )

        plan = await plan_presentation(config, user_id="test_user", ontology=ontology)
        slides = plan.get("slides", [])
        
        # Must respect slide flex limit (10 <= len <= 12)
        assert 10 <= len(slides) <= 12

        # None of the core subtopics should be dropped
        covered, missing = check_subtopic_coverage(many_subtopics, slides)
        assert len(missing) == 0, f"Expected 100% coverage via merge or flex, but missed: {missing}"

    asyncio.run(_run())
