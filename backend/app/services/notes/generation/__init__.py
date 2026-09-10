"""
TeachGenie Notes Generation Engine Package (Step 3)
===================================================
Produces structured, pedagogical NotesDocuments from CanonicalNotesContext
and NotesGenerationPlan.
"""
from .schemas import (
    GroundedSources,
    GroundedSourceItem,
    PracticeQuestionItem,
    GenerationResult,
    GenerationMode,
    SemanticDeficit
)
from .prompt_builder import PromptBuilder
from .output_parser import OutputParser
from .structural_compliance import StructuralComplianceValidator
from .engine import generate_notes, ensure_generation_plan

__all__ = [
    "generate_notes",
    "ensure_generation_plan",
    "PromptBuilder",
    "OutputParser",
    "StructuralComplianceValidator",
    "GroundedSources",
    "GroundedSourceItem",
    "PracticeQuestionItem",
    "GenerationResult",
    "GenerationMode",
    "SemanticDeficit",
]
