"""
Test Suite: Topic Ontology Coverage
===================================
Given a topic, verifies that the generated ontology checklist contains expected
standard subtopics (foundational principles, mechanisms, metrics, case studies, tradeoffs).
"""
import sys
import os
import pytest
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.presentation.schemas import PresentationConfig
from app.services.presentation.topic_ontology_agent import (
    generate_topic_ontology, TopicOntologyChecklist, compute_ontology_key
)


def test_topic_ontology_coverage_machine_learning():
    """Verify standard ML subtopics are generated in the ontology checklist.
    Includes retry-with-backoff to handle transient API rate limits."""
    async def _run():
        config = PresentationConfig(
            topic="Machine Learning",
            slide_count=12,
            audience="university",
            depth="full"
        )
        
        checklist = await generate_topic_ontology(config)
        assert isinstance(checklist, TopicOntologyChecklist)
        assert len(checklist.core_subtopics) >= 5, "Checklist should contain at least 5 core subtopics"
        
        # Check for presence of fundamental concepts
        all_text = " ".join(checklist.core_subtopics).lower()
        expected_concepts = ["definition", "learning", "mechanism", "metric", "case", "tradeoff", "limitation", "principle", "workflow", "model"]
        matches = [c for c in expected_concepts if c in all_text]
        assert len(matches) >= 3, f"Expected coverage of standard ML curriculum concepts, found: {matches}"
        assert len(checklist.must_include) >= 1, "Must include at least one concrete pedagogical requirement"

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


def test_topic_ontology_key_determinism():
    """Verify compute_ontology_key is deterministic and case-insensitive."""
    key1 = compute_ontology_key("Machine Learning", "University", "Full")
    key2 = compute_ontology_key("machine learning", "university", "full")
    assert key1 == key2
    assert len(key1) == 64
