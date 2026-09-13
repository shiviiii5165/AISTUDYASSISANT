"""
Test Suite: Slide Count Flex
============================
Verifies that when a broad topic cannot fit all core subtopics without destructive
merging, the planner flexes by at most +2 slides and records the expansion reason.
Also verifies it does not flex when subtopic count comfortably fits the target count.

Guarantees the exact same structural invariants across all failure modes:
1. Healthy Provider
2. Forced HTTP 429
3. Provider Timeout
4. Deterministic Fallback
"""
import sys
import os
import pytest
import asyncio
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.presentation.schemas import PresentationConfig
from app.services.presentation.topic_ontology_agent import TopicOntologyChecklist
from app.services.presentation.planner_agent import plan_presentation


BROAD_ONTOLOGY = TopicOntologyChecklist(
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

NARROW_ONTOLOGY = TopicOntologyChecklist(
    core_subtopics=[
        "Divide and Conquer Foundations",
        "Pre-conditions and Invariant Maintenance",
        "Time Complexity Analysis (O(log n))",
        "Edge Cases (Empty arrays, singletons, duplicates)",
    ],
    must_include=["Pseudocode implementation"],
)

CONFIG_TIGHT = PresentationConfig(
    topic="Distributed Systems Consensus Protocols",
    slide_count=10,
    audience="university",
)

CONFIG_GENEROUS = PresentationConfig(
    topic="Binary Search Algorithm",
    slide_count=12,
    audience="university",
)


def test_planner_flexes_when_subtopics_exceed_tight_count():
    """Force 8 distinct core subtopics into a 10-slide count, verifying planner expands by up to +2."""
    async def _run():
        plan = await plan_presentation(CONFIG_TIGHT, user_id="test_user", ontology=BROAD_ONTOLOGY)
        slides = plan.get("slides", [])
        assert 10 <= len(slides) <= 12, f"Slide count {len(slides)} outside [10..12]"
        if len(slides) > 10:
            assert plan.get("expansion_reason"), "Should record expansion_reason when flexing"
    asyncio.run(_run())


def test_planner_does_not_expand_when_not_needed():
    """When slide_count is generous, planner should not expand beyond target."""
    async def _run():
        plan = await plan_presentation(CONFIG_GENEROUS, user_id="test_user", ontology=NARROW_ONTOLOGY)
        slides = plan.get("slides", [])
        assert len(slides) == 12, f"Expected exactly target count 12, got {len(slides)}"
    asyncio.run(_run())


def test_planner_under_forced_http_429():
    """Verify tight and generous slide count invariants when provider throws HTTP 429 quota exhaustion."""
    async def _run():
        mock_429 = AsyncMock(side_effect=RuntimeError("GeminiProvider failed across all models: Status 429: Rate limit exceeded"))
        with patch("app.services.presentation.planner_agent.router.generate_json", mock_429):
            # Tight: 10..12
            plan_tight = await plan_presentation(CONFIG_TIGHT, user_id="test_user", ontology=BROAD_ONTOLOGY)
            slides_tight = plan_tight.get("slides", [])
            assert 10 <= len(slides_tight) <= 12, f"Tight count {len(slides_tight)} not in [10..12]"
            if len(slides_tight) > 10:
                assert plan_tight.get("expansion_reason")

            # Generous: exactly 12
            plan_gen = await plan_presentation(CONFIG_GENEROUS, user_id="test_user", ontology=NARROW_ONTOLOGY)
            slides_gen = plan_gen.get("slides", [])
            assert len(slides_gen) == 12, f"Generous count {len(slides_gen)} != 12"
            assert not plan_gen.get("expansion_reason")
    asyncio.run(_run())


def test_planner_under_provider_timeout():
    """Verify tight and generous slide count invariants when provider times out."""
    async def _run():
        mock_timeout = AsyncMock(side_effect=asyncio.TimeoutError("All providers timed out"))
        with patch("app.services.presentation.planner_agent.router.generate_json", mock_timeout):
            # Tight: 10..12
            plan_tight = await plan_presentation(CONFIG_TIGHT, user_id="test_user", ontology=BROAD_ONTOLOGY)
            slides_tight = plan_tight.get("slides", [])
            assert 10 <= len(slides_tight) <= 12, f"Tight count {len(slides_tight)} not in [10..12]"
            if len(slides_tight) > 10:
                assert plan_tight.get("expansion_reason")

            # Generous: exactly 12
            plan_gen = await plan_presentation(CONFIG_GENEROUS, user_id="test_user", ontology=NARROW_ONTOLOGY)
            slides_gen = plan_gen.get("slides", [])
            assert len(slides_gen) == 12, f"Generous count {len(slides_gen)} != 12"
            assert not plan_gen.get("expansion_reason")
    asyncio.run(_run())


def test_planner_under_pure_deterministic_fallback():
    """Verify tight and generous slide count invariants under offline deterministic fallback."""
    async def _run():
        mock_err = AsyncMock(side_effect=Exception("Network isolated - pure fallback"))
        with patch("app.services.presentation.planner_agent.router.generate_json", mock_err):
            # Tight: 10..12
            plan_tight = await plan_presentation(CONFIG_TIGHT, user_id="test_user", ontology=BROAD_ONTOLOGY)
            slides_tight = plan_tight.get("slides", [])
            assert 10 <= len(slides_tight) <= 12, f"Tight count {len(slides_tight)} not in [10..12]"
            if len(slides_tight) > 10:
                assert plan_tight.get("expansion_reason")

            # Generous: exactly 12
            plan_gen = await plan_presentation(CONFIG_GENEROUS, user_id="test_user", ontology=NARROW_ONTOLOGY)
            slides_gen = plan_gen.get("slides", [])
            assert len(slides_gen) == 12, f"Generous count {len(slides_gen)} != 12"
            assert not plan_gen.get("expansion_reason")
    asyncio.run(_run())
