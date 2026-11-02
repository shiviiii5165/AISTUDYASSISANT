"""
LearnByGenie — Feature 8: Domain Adapters Registry
===================================================
Exports domain adapters and default registry.
"""
from typing import List
from .base import StepGraderAdapter, StepValidationResult
from .math_adapter import MathStepAdapter
from .physics_adapter import PhysicsStepAdapter
from .chemistry_adapter import ChemistryStepAdapter
from .cs_adapter import CSReasoningAdapter
from .generic_rubric_adapter import GenericSequenceAdapter


def get_default_adapters() -> List[StepGraderAdapter]:
    """Returns the ordered list of default adapters. Specialized STEM adapters first, Generic fallback last."""
    return [
        MathStepAdapter(),
        PhysicsStepAdapter(),
        ChemistryStepAdapter(),
        CSReasoningAdapter(),
        GenericSequenceAdapter(),
    ]


__all__ = [
    "StepGraderAdapter",
    "StepValidationResult",
    "MathStepAdapter",
    "PhysicsStepAdapter",
    "ChemistryStepAdapter",
    "CSReasoningAdapter",
    "GenericSequenceAdapter",
    "get_default_adapters",
]
