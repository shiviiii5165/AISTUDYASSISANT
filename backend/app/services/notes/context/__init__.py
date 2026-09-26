"""
LearnByGenie Notes Context Engine
===============================
Independent context collection, normalization, deterministic prioritization,
conflict preservation, completeness evaluation, and immutable snapshotting.
"""
from .schemas import (
    NotesContextSource,
    ContextResolutionStatus,
    FieldProvenance,
    ContextConflict,
    ContextCompleteness,
    RequestContext,
    ExplicitInputContext,
    StudentContext,
    CurriculumContext,
    LessonContext,
    AssessmentContext,
    TeachMeContext,
    PPTContext,
    SourcesContext,
    ResolvedContext,
    ProvenanceContext,
    CanonicalNotesContext,
    ContextSnapshot,
    AnalyzeContextRequest,
    AnalyzeContextResponse,
    SOURCE_PRIORITY_MAP,
    SOURCE_CONFIDENCE_MAP,
)
from .normalizer import ContextNormalizer
from .conflict_detector import ConflictDetector, CandidateValue
from .resolver import ContextResolver
from .completeness import CompletenessEvaluator
from .snapshot import ContextSnapshotManager
from .analyzer import NotesContextAnalyzer

__all__ = [
    "NotesContextSource",
    "ContextResolutionStatus",
    "FieldProvenance",
    "ContextConflict",
    "ContextCompleteness",
    "RequestContext",
    "ExplicitInputContext",
    "StudentContext",
    "CurriculumContext",
    "LessonContext",
    "AssessmentContext",
    "TeachMeContext",
    "PPTContext",
    "SourcesContext",
    "ResolvedContext",
    "ProvenanceContext",
    "CanonicalNotesContext",
    "ContextSnapshot",
    "AnalyzeContextRequest",
    "AnalyzeContextResponse",
    "SOURCE_PRIORITY_MAP",
    "SOURCE_CONFIDENCE_MAP",
    "ContextNormalizer",
    "ConflictDetector",
    "CandidateValue",
    "ContextResolver",
    "CompletenessEvaluator",
    "ContextSnapshotManager",
    "NotesContextAnalyzer",
]
