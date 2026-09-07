"""
Test Suite: Slide Count Flex
============================
Verifies that when a broad topic cannot fit all core subtopics without destructive
merging, the planner flexes by at most +2 slides and records the expansion reason.
Also verifies it does not flex when subtopic count comfortably fits the target count.
"""
import sys
import os
import pytest
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.presentation.schemas import PresentationConfig
from app.services.presentation.topic_ontology_agent import TopicOntologyChecklist
from app.services.presentation.planner_agent import plan_presentation


def test_planner_flexes_when_subtopics_exceed_tight_count():
    """Force 8 distinct core subtopics into a 10-slide count, verifying planner expands by up to +2."""
    async def _run():
        config = PresentationConfig(
            topic="Distributed Systems Consensus Protocols",
            slide_count=10,
            audience="university",
        )

        broad_ontology = TopicOntologyChecklist(
            core_subtopics=[
                "FLP Impossibility Theorem",
                "Paxos Protocol & Two-Phase Commit",
                "Raft Consensus Algorithm",
                "Byzantine Fault Tolerance (BFT)",
                "Quorum Systems & Vector Clocks",
                "Gossip Protocols & Membership",
                "State Machine Replication",
                "Real-World Production Failures (Kafka/etcd/ZooKeeper)",
            ],
            must_include=["Leader election step-by-step breakdown"],
        )

        plan = await plan_presentation(config, user_id="test_user", ontology=broad_ontology)
        slides = plan.get("slides", [])

        # Target was 10. With 8 core concepts + hero + qa, it should expand to 11 or 12 (at most +2)
        assert 10 <= len(slides) <= 12, f"Slide count {len(slides)} outside [10..12]"
        if len(slides) > 10:
            assert plan.get("expansion_reason"), "Should record expansion_reason when flexing"
    asyncio.run(_run())


def test_planner_does_not_expand_when_not_needed():
    """When slide_count is generous, planner should not expand beyond target."""
    async def _run():
        config = PresentationConfig(
            topic="Binary Search Algorithm",
            slide_count=12,
            audience="university",
        )

        narrow_ontology = TopicOntologyChecklist(
            core_subtopics=[
                "Divide and Conquer Foundations",
                "Pre-conditions and Invariant Maintenance",
                "Time Complexity Analysis (O(log n))",
                "Edge Cases (Empty arrays, singletons, duplicates)",
            ],
            must_include=["Pseudocode implementation"],
        )

        plan = await plan_presentation(config, user_id="test_user", ontology=narrow_ontology)
        slides = plan.get("slides", [])

        assert len(slides) == 12, f"Expected exactly target count 12, got {len(slides)}"
    asyncio.run(_run())
