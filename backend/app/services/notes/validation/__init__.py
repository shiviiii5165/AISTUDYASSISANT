"""
TeachGenie Notes Validation Engine Package (Step 4)
===================================================
Exports validation pipeline, schemas, statuses, violations, and bounded repair.
"""
from .schemas import (
    ValidationStatus,
    ViolationSeverity,
    ValidationDimension,
    ValidationViolation,
    RepairAction,
    RepairTarget,
    RepairRecommendation,
    ValidationResult,
    ValidateNotesRequest
)
from .engine import validate_notes
from .repair_orchestrator import validate_and_repair_notes

__all__ = [
    "ValidationStatus",
    "ViolationSeverity",
    "ValidationDimension",
    "ValidationViolation",
    "RepairAction",
    "RepairTarget",
    "RepairRecommendation",
    "ValidationResult",
    "ValidateNotesRequest",
    "validate_notes",
    "validate_and_repair_notes",
]
