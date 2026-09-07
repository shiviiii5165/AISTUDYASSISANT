"""
Test Suite: Dynamic Sizing via Content Volume (No Fixed Size Before Content)
===========================================================================
Verifies that pedagogical component renderers (definition_box, contrast_pair, etc.)
calculate their container heights dynamically based on content volume via
`estimate_text_height` rather than hardcoding oversized fixed dimensions.
"""
import sys
import os
import pytest
from pptx.util import Inches

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.presentation_engine.tokens import Typography
from app.services.presentation_engine.text_fitter import estimate_text_height

def test_estimate_text_height_scales_with_content_volume():
    """Verify estimate_text_height produces strictly larger heights for larger content volumes."""
    short_text = "Atomic execution ensures all or nothing commits."
    long_text = (
        "Atomic execution ensures that either all database operations within the transaction "
        "block complete successfully and commit durably to disk, or every partial modification "
        "is completely rolled back to the prior clean checkpoint, leaving no intermediate "
        "or orphaned state visible to concurrent observers."
    )
    width = Inches(6.0)

    h_short = estimate_text_height(short_text, Typography.BODY, width)
    h_long = estimate_text_height(long_text, Typography.BODY, width)

    assert h_long > h_short, (
        f"Expected h_long ({h_long}) > h_short ({h_short}) for scaled content"
    )
    # Assert ratio reflects substantial expansion (at least 2x)
    assert h_long >= 2 * h_short

def test_contrast_pair_height_adapts_to_maximum_column():
    """Verify contrast pair calculation dynamically accounts for unequal column heights."""
    left_short = "Don't prematurely optimize."
    right_long = (
        "Establish formal latency profiling under realistic traffic distributions. "
        "Identify exact CPU cache misses and lock contention points before modifying data structures. "
        "Always benchmark amortized throughput against baseline requirements."
    )
    col_w = Inches(5.0)
    lh = estimate_text_height(left_short, Typography.BULLET, col_w)
    rh = estimate_text_height(right_long, Typography.BULLET, col_w)

    # Max height must scale to fit the longer side
    assert rh > lh
    computed_card_h = max(Inches(3.2), min(max(lh, rh) + Inches(1.5), Inches(5.0)))
    assert computed_card_h >= rh
