"""
Test Suite: Reviewer Repair Cap
===============================
Verifies that the Reviewer Agent and QA Agent strictly cap targeted repairs
at 1 single pass, preventing infinite loops even if a synthetic slide is designed
to always fail structural checks.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, AsyncMock
from app.services.presentation.schemas import PresentationConfig
from app.services.presentation.reviewer_agent import run_reviewer_critic


import asyncio

def test_reviewer_repair_strictly_capped_at_one_pass():
    """Verify repair function is invoked at most once per flagged slide, never looping."""
    async def _run():
        config = PresentationConfig(
            topic="Compiler Design",
            slide_count=10,
            audience="university",
        )

        # Synthetic defective slide
        defective_slide = {
            "slide_no": 3,
            "type": "concept",
            "title": "Lexical Analysis",
            "body_bullets": [], # empty bullets will trigger flag
            "speaker_notes": "",
        }

        slides = [
            {"slide_no": 1, "type": "hero", "title": "Compiler Construction", "body_bullets": []},
            {"slide_no": 2, "type": "concept", "title": "Architecture", "body_bullets": ["Parsing."]},
            defective_slide,
            {"slide_no": 4, "type": "qa", "title": "Questions", "body_bullets": []},
        ]

        slide_repair_counts = {}

        async def mock_repair(slide, issues, directive=""):
            s_no = slide.get("slide_no")
            slide_repair_counts[s_no] = slide_repair_counts.get(s_no, 0) + 1
            # Intentionally return still-defective slide to test that it doesn't loop
            return dict(slide)

        with patch("app.services.presentation.reviewer_agent.repair_single_slide", side_effect=mock_repair):
            result_slides = await run_reviewer_critic(config, slides)

            # Assert no slide was repaired more than once (strictly capped at 1 pass, never looping)
            assert len(slide_repair_counts) > 0, "Expected at least one slide to be repaired"
            for s_no, count in slide_repair_counts.items():
                assert count == 1, f"Slide {s_no} was repaired {count} times, expected exactly 1 pass"
            assert sum(slide_repair_counts.values()) <= 2, "Expected at most 2 targeted repairs per deck"
            assert len(result_slides) == 4
    asyncio.run(_run())
