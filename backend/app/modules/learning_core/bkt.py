"""Stage 6: Constrained Bayesian Knowledge Tracing."""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class Intervention(str, Enum):
    NO_HELP = "no_help"
    WORKED_EXAMPLE = "worked_example"


TRANSITION_RATES = {Intervention.NO_HELP: 0.08, Intervention.WORKED_EXAMPLE: 0.25}


@dataclass(frozen=True)
class BKTParams:
    p_l0: float = 0.2
    p_s: float = 0.1
    p_g: float = 0.2

    def __post_init__(self) -> None:
        for name in ("p_l0", "p_s", "p_g"):
            if not 0.0 <= getattr(self, name) <= 1.0:
                raise ValueError(f"{name} must be a probability")
        if self.p_s > 0.20:
            raise ValueError("P(S) must be <= 0.20")
        if 1.0 - self.p_s <= self.p_g:
            raise ValueError("Non-degeneracy requires 1 - P(S) > P(G)")


def decay(p_last: float, elapsed_days: float, stability_days: float) -> float:
    """P(L_start) = P(L_last) * exp(-dt / S_k)."""
    if elapsed_days < 0:
        raise ValueError("elapsed_days must be >= 0")
    if stability_days <= 0:
        raise ValueError("stability_days must be > 0")
    return p_last * math.exp(-elapsed_days / stability_days)


def update(
    p_l: float,
    correct: bool,
    params: BKTParams,
    intervention: Intervention = Intervention.NO_HELP,
) -> float:
    """Apply the Bayes evidence step, then the intervention-conditioned learning step."""
    if not 0.0 <= p_l <= 1.0:
        raise ValueError("p_l must be a probability")
    if correct:
        known, unknown = p_l * (1.0 - params.p_s), (1.0 - p_l) * params.p_g
    else:
        known, unknown = p_l * params.p_s, (1.0 - p_l) * (1.0 - params.p_g)
    total = known + unknown
    posterior = known / total if total > 0 else p_l
    p_t = TRANSITION_RATES[intervention]
    return posterior + (1.0 - posterior) * p_t
