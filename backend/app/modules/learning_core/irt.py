"""Stage 1: Computerized Adaptive Testing with 1PL/2PL/3PL IRT.

Ability is estimated by EAP over a fixed grid with a N(0, 1) prior, and SE(theta)
is the posterior standard deviation. EAP stays finite on all-correct and
all-wrong response patterns, where maximum likelihood diverges.

The logistic scaling constant D = 1.7 is what makes SE <= 0.32 reachable inside
15 items. Reaching it needs test information of about 8.8 on top of the prior.
Without D, a perfectly targeted a = 1 item gives only 0.25, or 3.75 over 15 items.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

D = 1.7
TARGET_SE = 0.32
MIN_ITEMS = 8
MAX_ITEMS = 15

_GRID = tuple(-4.0 + 0.05 * i for i in range(161))
_PRIOR = tuple(math.exp(-0.5 * t * t) for t in _GRID)


@dataclass(frozen=True)
class IRTItem:
    """1PL: a=1, c=0. 2PL: c=0. 3PL: all three parameters free."""

    item_id: str
    b: float
    a: float = 1.0
    c: float = 0.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.b):
            raise ValueError("b must be finite")
        if not (math.isfinite(self.a) and self.a > 0):
            raise ValueError("a must be positive")
        if not 0.0 <= self.c < 1.0:
            raise ValueError("c must be in [0, 1)")


@dataclass(frozen=True)
class Response:
    item: IRTItem
    correct: bool


@dataclass(frozen=True)
class AbilityEstimate:
    theta: float
    se: float


def probability(theta: float, item: IRTItem) -> float:
    exponent = max(-35.0, min(35.0, D * item.a * (theta - item.b)))
    return item.c + (1.0 - item.c) / (1.0 + math.exp(-exponent))


def fisher_information(theta: float, item: IRTItem) -> float:
    p = probability(theta, item)
    if p <= item.c or p >= 1.0:
        return 0.0
    return (D * item.a) ** 2 * ((1.0 - p) / p) * ((p - item.c) / (1.0 - item.c)) ** 2


def estimate_ability(responses: Iterable[Response]) -> AbilityEstimate:
    """Return the EAP ability and posterior SD; with no responses, the prior."""
    log_posterior = [0.0] * len(_GRID)
    for response in responses:
        for index, theta in enumerate(_GRID):
            p = probability(theta, response.item)
            log_posterior[index] += math.log(max(p if response.correct else 1.0 - p, 1e-300))
    peak = max(log_posterior)
    weights = [prior * math.exp(lp - peak) for prior, lp in zip(_PRIOR, log_posterior)]
    total = sum(weights)
    mean = sum(t * w for t, w in zip(_GRID, weights)) / total
    variance = sum((t - mean) ** 2 * w for t, w in zip(_GRID, weights)) / total
    return AbilityEstimate(theta=mean, se=math.sqrt(variance))


def select_next_item(
    theta: float, bank: Sequence[IRTItem], administered: Iterable[str]
) -> Optional[IRTItem]:
    """Pick the unseen item with maximum information; ties break on item_id."""
    seen = set(administered)
    candidates = [item for item in bank if item.item_id not in seen]
    if not candidates:
        return None
    return max(candidates, key=lambda i: (fisher_information(theta, i), i.item_id))


def stop_reason(items_answered: int, se: float) -> Optional[str]:
    """Return why the CAT should stop, or None to continue."""
    if items_answered >= MAX_ITEMS:
        return "precision_reached" if se <= TARGET_SE else "max_items"
    if items_answered >= MIN_ITEMS and se <= TARGET_SE:
        return "precision_reached"
    return None
