"""
TeachGenie AI Notes Generation Subsystem
========================================
Independent top-level notes generation engine for Class 3–12 learners.
"""
from .schemas import (
    NotesDocument, NoteSection, GenerateNotesRequest,
    CanonicalNotesContext, DecisionOutput, NotesQualityReport,
    NoteFormat, NoteDepth, NoteDifficulty, VisualSpec, CalloutItem
)
from .context_extractor import NotesContextExtractor
from .decision_engine import NotesDecisionEngine
from .validator import NotesValidator
from .generator import NotesGenerator
from .repository import NotesRepository
from .validation import (
    validate_notes, validate_and_repair_notes,
    ValidationResult, ValidationStatus, ValidationViolation
)

__all__ = [
    "NotesDocument",
    "NoteSection",
    "GenerateNotesRequest",
    "CanonicalNotesContext",
    "DecisionOutput",
    "NotesQualityReport",
    "NoteFormat",
    "NoteDepth",
    "NoteDifficulty",
    "VisualSpec",
    "CalloutItem",
    "NotesContextExtractor",
    "NotesDecisionEngine",
    "NotesValidator",
    "NotesGenerator",
    "NotesRepository",
    "validate_notes",
    "validate_and_repair_notes",
    "ValidationResult",
    "ValidationStatus",
    "ValidationViolation",
]

