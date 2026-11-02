"""Stage 5: ZPD item selection, wheel-spin detection and 60/40 interleaving."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from .irt import IRTItem, probability

ZPD_LOW = 0.65
ZPD_HIGH = 0.78
WHEEL_SPIN_FAILURES = 3
INTERLEAVE_MIN_TIER = 3
SIBLING_SHARE = 0.4


@dataclass(frozen=True)
class PracticeDecision:
    action: str  # "item", "simulation" or "exhausted"
    item: Optional[IRTItem] = None
    source: Optional[str] = None  # "current" or "sibling"
    in_zpd: bool = False


def is_sibling_slot(sequence_index: int, tier: int) -> bool:
    """Spread sibling slots evenly so that exactly 40% of each 5 items are siblings."""
    if tier < INTERLEAVE_MIN_TIER:
        return False
    return int((sequence_index + 1) * SIBLING_SHARE) > int(sequence_index * SIBLING_SHARE)


def _best_item(theta: float, items: Iterable[IRTItem]) -> Optional[tuple[IRTItem, bool]]:
    midpoint = (ZPD_LOW + ZPD_HIGH) / 2

    def rank(item: IRTItem) -> tuple[int, float, str]:
        p = probability(theta, item)
        in_band = ZPD_LOW <= p <= ZPD_HIGH
        return (0 if in_band else 1, abs(p - midpoint), item.item_id)

    best = min(items, key=rank, default=None)
    if best is None:
        return None
    return best, ZPD_LOW <= probability(theta, best) <= ZPD_HIGH


def select_practice(
    theta: float,
    tier: int,
    sequence_index: int,
    consecutive_failures: int,
    current_items: Sequence[IRTItem],
    sibling_items: Sequence[IRTItem] = (),
    seen_item_ids: Iterable[str] = (),
) -> PracticeDecision:
    """Choose the next action; falls back to the nearest item if the band is empty."""
    if consecutive_failures >= WHEEL_SPIN_FAILURES:
        return PracticeDecision(action="simulation")

    seen = set(seen_item_ids)
    current = [i for i in current_items if i.item_id not in seen]
    siblings = [i for i in sibling_items if i.item_id not in seen]
    pools = [("current", current), ("sibling", siblings)]
    if is_sibling_slot(sequence_index, tier):
        pools.reverse()
    elif tier < INTERLEAVE_MIN_TIER:
        pools = pools[:1]

    for source, pool in pools:
        best = _best_item(theta, pool)
        if best is not None:
            return PracticeDecision("item", best[0], source, best[1])
    return PracticeDecision(action="exhausted")
