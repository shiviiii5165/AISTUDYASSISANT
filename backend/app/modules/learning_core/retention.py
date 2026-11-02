"""Stage 7: Ebbinghaus review scheduling.

R(dt) = exp(-dt / S), so retrievability reaches the 78% gate at dt = -S * ln(0.78).
The next review is the earlier of the ladder gap (days 1, 3, 8, 21, 50) and that
gate, so weak memories come back sooner and the ladder is never exceeded.

The blueprint only defines the stability update for a successful review. On a
failure this module halves stability (never below the initial value) and restarts
the ladder.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

LADDER_DAYS = (1, 3, 8, 21, 50)
RETRIEVAL_GATE = 0.78
GATE_FACTOR = -math.log(RETRIEVAL_GATE)
# Stability at which R falls to exactly 78% one day after first learning.
INITIAL_STABILITY = 1.0 / GATE_FACTOR


@dataclass(frozen=True)
class ReviewState:
    stability: float = INITIAL_STABILITY
    step: int = 0  # Number of consecutive successful reviews.


def retrievability(elapsed_days: float, stability: float) -> float:
    if elapsed_days < 0:
        raise ValueError("elapsed_days must be >= 0")
    if stability <= 0:
        raise ValueError("stability must be > 0")
    return math.exp(-elapsed_days / stability)


def updated_stability(stability: float, b: float, theta: float) -> float:
    """S_new = S * (2.4 + 0.2 * (b - theta)); a success can never shrink stability."""
    return stability * max(1.0, 2.4 + 0.2 * (b - theta))


def apply_review(state: ReviewState, passed: bool, b: float, theta: float) -> ReviewState:
    if passed:
        return ReviewState(updated_stability(state.stability, b, theta), state.step + 1)
    return ReviewState(max(INITIAL_STABILITY, state.stability * 0.5), 0)


def next_interval_days(state: ReviewState) -> float:
    gate_days = state.stability * GATE_FACTOR
    if state.step >= len(LADDER_DAYS):
        return gate_days
    previous = LADDER_DAYS[state.step - 1] if state.step > 0 else 0
    return min(float(LADDER_DAYS[state.step] - previous), gate_days)


def next_due(state: ReviewState, reviewed_at: datetime) -> datetime:
    return reviewed_at + timedelta(days=next_interval_days(state))
