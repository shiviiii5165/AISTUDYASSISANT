"""
Test Suite: Image Query Relevance
=================================
Verifies that generated image_query is specific, visual, and describes a real scene,
not just the generic deck topic string.
"""
import sys
import os
import pytest
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.presentation.schemas import PresentationConfig
from app.services.presentation.content_agent import expand_presentation_content
from app.services.presentation.image_source_router import score_relevance


def test_image_query_generation_specificity():
    """Verify that expanded slides generate concrete photographic queries."""
    async def _run():
        config = PresentationConfig(
            topic="Neural Network Training and Gradient Descent",
            slide_count=10,
            audience="university",
        )

        mock_outline = {
            "deck_title": "Neural Network Training and Gradient Descent",
            "slides": [
                {
                    "slide_no": 1,
                    "type": "hero",
                    "title": "Neural Network Optimization at Scale",
                    "key_message": "Gradient descent adjusts millions of parameters using backpropagation.",
                    "visual_hint": "image",
                },
                {
                    "slide_no": 2,
                    "type": "concept",
                    "title": "GPU Acceleration in Modern AI Data Centers",
                    "key_message": "Matrix multiplication pipelines require high-bandwidth memory architectures.",
                    "visual_hint": "image",
                },
            ]
        }

        expanded = await expand_presentation_content(config, user_id="test_user", outline_data=mock_outline)
        assert len(expanded) >= 2

        for s in expanded:
            img_q = s.get("image_query", "")
            assert img_q, f"Slide {s.get('slide_no')} missing image_query"
            # Must not be just the raw topic name alone
            assert img_q.strip().lower() != config.topic.lower(), "image_query should be a visual scene, not just the deck topic"
            assert len(img_q.split()) >= 3, f"image_query should be a multi-word descriptive phrase: '{img_q}'"
    asyncio.run(_run())


def test_relevance_scoring_function():
    """Test keyword relevance scoring."""
    query = "data center server racks with blue led lights"
    good_tags = "data center, server rack, glowing blue led, network hardware"
    bad_tags = "smiling corporate business meeting in bright office"

    score_good = score_relevance(query, good_tags)
    score_bad = score_relevance(query, bad_tags)

    assert score_good >= 0.5, f"Expected high relevance score, got {score_good}"
    assert score_bad < 0.2, f"Expected near-zero relevance score, got {score_bad}"
