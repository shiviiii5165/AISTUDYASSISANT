"""
LearnByGenie — Canonical Practice Engine Schemas (Feature 6)
=============================================================
Strict Pydantic contracts for Adaptive Practice:
- Item bank, provenance, validation
- Adaptive session state machine and multi-tab optimistic locking
- Authoritative response telemetry and idempotency
- Pedagogical selection explainability and session summary
"""
from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class PracticeMode(str, Enum):
    FOCUSED = "FOCUSED"               # Student chooses topic/skill
    ADAPTIVE = "ADAPTIVE"             # Engine chooses best current skill dynamically
    REPAIR = "REPAIR"                 # Prioritizes open Mistake DNA & blocked prerequisites
    EXAM_PRACTICE = "EXAM_PRACTICE"   # Exam-appropriate item style while preserving evidence


class DifficultyBand(str, Enum):
    FOUNDATIONAL = "FOUNDATIONAL"     # Class-appropriate foundational / easy
    STANDARD = "STANDARD"             # Core curriculum benchmark / medium
    ADVANCED = "ADVANCED"             # Stretch / higher-order / hard

    @classmethod
    def from_str(cls, val: str) -> "DifficultyBand":
        v = (val or "").strip().upper()
        if v in ("FOUNDATIONAL", "EASY"):
            return cls.FOUNDATIONAL
        if v in ("ADVANCED", "HARD"):
            return cls.ADVANCED
        return cls.STANDARD

    def to_legacy(self) -> str:
        if self == DifficultyBand.FOUNDATIONAL:
            return "easy"
        if self == DifficultyBand.ADVANCED:
            return "hard"
        return "medium"


class QuestionType(str, Enum):
    MCQ = "mcq"
    NUMERIC = "numeric"
    SHORT_ANSWER = "short_answer"


class AssistanceLevel(str, Enum):
    INDEPENDENT = "INDEPENDENT"
    PARTIALLY_ASSISTED = "PARTIALLY_ASSISTED"
    HINT_ASSISTED = "HINT_ASSISTED"
    FULLY_ASSISTED = "FULLY_ASSISTED"


class SelectionCategory(str, Enum):
    PREREQUISITE_REPAIR = "PREREQUISITE_REPAIR"
    MISTAKE_DNA_REPAIR = "MISTAKE_DNA_REPAIR"
    DEVELOPING_SKILL = "DEVELOPING_SKILL"
    READY_NEXT_SKILL = "READY_NEXT_SKILL"
    SECURE_CONCEPT_CHECK = "SECURE_CONCEPT_CHECK"
    EXPLORATORY_PROBE = "EXPLORATORY_PROBE"


class ProvenanceType(str, Enum):
    CURATED = "CURATED"
    TEACHER_VERIFIED = "TEACHER_VERIFIED"
    APPROVED_BANK = "APPROVED_BANK"
    VERIFIED_GENERATED = "VERIFIED_GENERATED"
    LICENSED = "LICENSED"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"


class PracticeSessionStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class ContentCoverageStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    INSUFFICIENT_CONTENT = "INSUFFICIENT_CONTENT"


# ─── 1. ITEM MODELS ───────────────────────────────────────────────────────────

class PracticeItem(BaseModel):
    id: str
    skill_id: str
    subject: str
    grade_band: str = "secondary"
    difficulty_band: DifficultyBand = DifficultyBand.STANDARD
    question_type: QuestionType = QuestionType.MCQ
    prompt: str
    options: List[str] = Field(default_factory=list)

    # SERVER-ONLY. Never expose to client before submission.
    correct_answer: Union[str, int, float, List[str]]
    explanation: str = ""
    hints: List[str] = Field(default_factory=list)

    provenance: ProvenanceType = ProvenanceType.CURATED
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    language: str = "english"
    target_mistake_types: List[str] = Field(default_factory=list)
    discrimination_index: float = 0.50
    metadata: Dict[str, Any] = Field(default_factory=dict)
    status: str = "active"
    version: int = 1

    def to_student_view(
        self,
        sequence_number: int,
        total_budget: int,
        revealed_hints: Optional[List[str]] = None,
        selection_reason: Optional[str] = None
    ) -> "StudentPracticeItemView":
        """Deliberately omits correct_answer, explanation, and unrevealed hints."""
        return StudentPracticeItemView(
            id=self.id,
            skill_id=self.skill_id,
            subject=self.subject,
            grade_band=self.grade_band,
            difficulty_band=self.difficulty_band.value,
            question_type=self.question_type.value,
            prompt=self.prompt,
            options=list(self.options),
            sequence_number=sequence_number,
            total_budget=total_budget,
            hints_total=len(self.hints),
            hints_revealed=revealed_hints or [],
            selection_reason=selection_reason,
        )


class StudentPracticeItemView(BaseModel):
    id: str
    skill_id: str
    subject: str
    grade_band: str
    difficulty_band: str
    question_type: str
    prompt: str
    options: List[str] = Field(default_factory=list)
    sequence_number: int
    total_budget: int
    hints_total: int = 0
    hints_revealed: List[str] = Field(default_factory=list)
    selection_reason: Optional[str] = None


# ─── 2. SESSION MODELS ────────────────────────────────────────────────────────

class PracticeSession(BaseModel):
    id: str
    user_id: str
    subject: str
    mode: PracticeMode = PracticeMode.ADAPTIVE
    curriculum: str = "CBSE"
    exam_track: str = "Boards"
    enrolled_grade: int = 10
    grade_band: str = "secondary"

    requested_skill_id: Optional[str] = None
    current_skill_id: Optional[str] = None
    current_item_id: Optional[str] = None

    question_index: int = 0                  # 0-indexed count of answered items
    question_budget: int = 10
    current_difficulty: DifficultyBand = DifficultyBand.STANDARD
    consecutive_correct: int = 0
    consecutive_incorrect: int = 0
    active_hints_used: int = 0
    policy_version: str = "1.0.0"

    status: PracticeSessionStatus = PracticeSessionStatus.IN_PROGRESS
    asked_item_ids: List[str] = Field(default_factory=list)
    skills_practiced: List[str] = Field(default_factory=list)
    selection_context: Dict[str, Any] = Field(default_factory=dict)

    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


# ─── 3. RESPONSE & FEEDBACK MODELS ───────────────────────────────────────────

class PracticeResponse(BaseModel):
    id: str
    session_id: str
    user_id: str
    item_id: str
    skill_id: str
    question_index: int
    student_response: Union[str, int, float, List[str]]
    correctness: bool
    assistance_level: AssistanceLevel = AssistanceLevel.INDEPENDENT
    difficulty_band: DifficultyBand = DifficultyBand.STANDARD
    response_time_ms: int = 0
    attempt_sequence: int = 1
    selection_reason: str = ""
    selection_category: str = ""
    hints_requested: int = 0
    provenance: str = "CURATED"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PracticeResponseSubmission(BaseModel):
    item_id: str
    question_index: int                      # Must match session.question_index for multi-tab OCC
    student_response: Union[str, int, float, List[str]]
    response_time_ms: int = 0
    attempt_sequence: int = 1


class PracticeFeedback(BaseModel):
    session_id: str
    item_id: str
    skill_id: str
    question_index: int
    correctness: bool
    assistance_level: AssistanceLevel
    authoritative_explanation: str
    current_difficulty: DifficultyBand
    session_completed: bool
    next_question_ready: bool
    mistake_pattern_detected: Optional[str] = None
    repair_recorded: bool = False


# ─── 4. SELECTION EXPLAINABILITY & SUMMARY ───────────────────────────────────

class PracticeSelectionExplanation(BaseModel):
    item_id: str
    skill_id: str
    skill_name: str
    category: SelectionCategory
    reason: str
    prerequisite_skill_id: Optional[str] = None
    mistake_pattern_type: Optional[str] = None
    difficulty: DifficultyBand = DifficultyBand.STANDARD


class SessionSummary(BaseModel):
    session_id: str
    user_id: str
    subject: str
    mode: PracticeMode
    total_questions: int
    correct_count: int
    independent_correct_count: int
    skills_practiced: List[Dict[str, Any]] = Field(default_factory=list)
    stronger_evidence_concepts: List[str] = Field(default_factory=list)
    developing_concepts: List[str] = Field(default_factory=list)
    mistake_patterns_encountered: List[str] = Field(default_factory=list)
    recommended_next_focus: str
    duration_seconds: int = 0


class CompactPracticeSummary(BaseModel):
    recent_practice_skill: Optional[str] = None
    current_active_focus: Optional[str] = None
    total_practice_sessions: int = 0
    total_practice_items_answered: int = 0
    relevant_open_repair: Optional[str] = None


class ContentAuditReport(BaseModel):
    total_items: int
    verified_items: int
    items_by_subject: Dict[str, int]
    items_by_difficulty: Dict[str, int]
    items_by_grade_band: Dict[str, int]
    issues_found: List[str]
    coverage_matrix: Dict[str, ContentCoverageStatus]
    is_valid: bool
