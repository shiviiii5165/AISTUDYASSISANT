"""
LearnByGenie — Adaptive Practice Engine (Feature 6)
===================================================
Canonical service, schemas, policy, adapters, item bank, and repository.
"""
from .schemas import (
    PracticeMode, DifficultyBand, QuestionType, AssistanceLevel,
    SelectionCategory, ProvenanceType, VerificationStatus,
    PracticeSessionStatus, ContentCoverageStatus, PracticeItem,
    StudentPracticeItemView, PracticeSession, PracticeResponse,
    PracticeResponseSubmission, PracticeFeedback,
    PracticeSelectionExplanation, SessionSummary,
    CompactPracticeSummary, ContentAuditReport
)
from .policy import (
    PracticePolicy, get_policy, register_policy, DEFAULT_PRACTICE_POLICY_V1
)
from .repository import PracticeRepository
from .item_bank import (
    get_practice_item, get_practice_items_for_skill,
    get_all_practice_items, register_practice_item,
    make_practice_uuid, CANONICAL_PRACTICE_ITEMS
)
from .adapters import (
    BaseDomainValidator, GenericMCQValidator, NumericValidator,
    MathAdapter, PhysicsAdapter, ChemistryAdapter, BiologyAdapter,
    CSAdapter, DomainAdapterRegistry
)
from .audit import ContentAuditor
from .service import AdaptivePracticeService

__all__ = [
    "PracticeMode",
    "DifficultyBand",
    "QuestionType",
    "AssistanceLevel",
    "SelectionCategory",
    "ProvenanceType",
    "VerificationStatus",
    "PracticeSessionStatus",
    "ContentCoverageStatus",
    "PracticeItem",
    "StudentPracticeItemView",
    "PracticeSession",
    "PracticeResponse",
    "PracticeResponseSubmission",
    "PracticeFeedback",
    "PracticeSelectionExplanation",
    "SessionSummary",
    "CompactPracticeSummary",
    "ContentAuditReport",
    "PracticePolicy",
    "get_policy",
    "register_policy",
    "DEFAULT_PRACTICE_POLICY_V1",
    "PracticeRepository",
    "get_practice_item",
    "get_practice_items_for_skill",
    "get_all_practice_items",
    "register_practice_item",
    "make_practice_uuid",
    "CANONICAL_PRACTICE_ITEMS",
    "BaseDomainValidator",
    "GenericMCQValidator",
    "NumericValidator",
    "MathAdapter",
    "PhysicsAdapter",
    "ChemistryAdapter",
    "BiologyAdapter",
    "CSAdapter",
    "DomainAdapterRegistry",
    "ContentAuditor",
    "AdaptivePracticeService",
]
