"""
LearnByGenie — Diagnostic Engine Core Schemas (Feature 2)
==========================================================
Strict Pydantic models for educational diagnostic assessment:
domains, skills, items, sessions, responses, results, and Feature 3 ingestion contract.

TRUST-BOUNDARY NOTE:
- `DiagnosticItem.correct_answer` and `explanation` are strictly SERVER-ONLY.
- `StudentItemView` deliberately omits answers, explanations, and branch logic.
"""
from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class DiagnosticStage(str, Enum):
    INITIALIZED = "INITIALIZED"
    ANCHOR = "ANCHOR"
    BRANCH = "BRANCH"
    CONFIRMATION = "CONFIRMATION"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class DiagnosticState(str, Enum):
    NOT_ASSESSED = "NOT_ASSESSED"
    NEEDS_REPAIR = "NEEDS_REPAIR"
    DEVELOPING = "DEVELOPING"
    SECURE = "SECURE"
    FRAGILE = "FRAGILE"


class ConfidenceClass(str, Enum):
    LOW_EVIDENCE = "LOW_EVIDENCE"
    MODERATE_EVIDENCE = "MODERATE_EVIDENCE"
    HIGH_EVIDENCE = "HIGH_EVIDENCE"


class OverallReadiness(str, Enum):
    READY = "READY"
    ON_TRACK = "ON_TRACK"
    PREREQUISITES_NEEDED = "PREREQUISITES_NEEDED"


class GradeBand(str, Enum):
    PRIMARY = "primary"                      # Class 3-5
    MIDDLE = "middle"                        # Class 6-8
    SECONDARY = "secondary"                  # Class 9-10
    SENIOR_SECONDARY = "senior_secondary"    # Class 11-12 / JEE / NEET
    UG = "ug"                                # Undergraduate coursework


class DifficultyBand(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionType(str, Enum):
    MCQ = "mcq"
    NUMERIC = "numeric"
    SHORT_ANSWER = "short_answer"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    PENDING = "pending"
    REJECTED = "rejected"


class DiagnosticDomain(BaseModel):
    id: str
    subject: str
    domain_name: str
    description: str = ""
    education_stage: str = "all"
    order_index: int = 0


class DiagnosticSkill(BaseModel):
    id: str
    domain_id: Optional[str] = None
    subject: str
    skill_code: str
    skill_name: str
    grade_band: str
    min_grade: int = 1
    max_grade: int = 12
    curriculum_context: str = "all"
    prerequisite_skill_ids: List[str] = Field(default_factory=list)
    topic: str = ""
    description: str = ""


class DiagnosticItem(BaseModel):
    id: str
    skill_id: str
    subject: str
    grade_band: str = GradeBand.SECONDARY.value
    difficulty_band: str = DifficultyBand.MEDIUM.value
    question_type: QuestionType = QuestionType.MCQ
    prompt: str
    options: List[str] = Field(default_factory=list)

    # SERVER-ONLY. Never return in student payload before submission.
    correct_answer: Union[str, int, float, List[str]]
    explanation: str = ""

    provenance: str = "curated_bank"
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    language: str = "english"
    discrimination_index: float = 0.50
    status: str = "active"
    version: int = 1

    def to_student_view(self, sequence_number: int, total_budget: int) -> "StudentItemView":
        """Deliberately omits correct_answer and explanation."""
        return StudentItemView(
            id=self.id,
            skill_id=self.skill_id,
            subject=self.subject,
            grade_band=self.grade_band,
            difficulty_band=self.difficulty_band,
            question_type=self.question_type.value,
            prompt=self.prompt,
            options=list(self.options),
            language=self.language,
            sequence_number=sequence_number,
            total_budget=total_budget,
        )


class StudentItemView(BaseModel):
    id: str
    skill_id: str
    subject: str
    grade_band: str
    difficulty_band: str
    question_type: str
    prompt: str
    options: List[str] = Field(default_factory=list)
    language: str = "english"
    sequence_number: int
    total_budget: int


class DiagnosticSession(BaseModel):
    id: str
    user_id: str
    subject: str
    curriculum: str = "CBSE"
    exam_track: str = "Boards"
    enrolled_grade: int = 10
    starting_level: str = "standard"
    preferred_language: str = "english"
    status: str = "IN_PROGRESS"
    current_stage: str = DiagnosticStage.ANCHOR.value
    current_item_id: Optional[str] = None
    question_budget: int = 10
    questions_answered: int = 0
    asked_item_ids: List[str] = Field(default_factory=list)
    active_skill_ids: List[str] = Field(default_factory=list)
    engine_version: str = "2.0.0"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class DiagnosticResponse(BaseModel):
    id: Optional[str] = None
    session_id: str
    user_id: str
    item_id: str
    skill_id: Optional[str] = None
    student_response: Any
    is_correct: bool = False
    response_time_ms: int = 0
    attempt_number: int = 1
    created_at: Optional[datetime] = None


class Feature3SkillEvidence(BaseModel):
    """Immutable Feature 3 (Mastery Graph) ingestion contract."""
    skill_id: str
    diagnostic_state: str
    evidence_count: int
    correct_count: int
    confidence: str
    source: str = "DIAGNOSTIC"
    diagnostic_session_id: str
    timestamp: str
    recommended_action: str


class DiagnosticSkillResult(BaseModel):
    id: Optional[str] = None
    result_id: Optional[str] = None
    session_id: str
    user_id: str
    subject: str
    skill_id: str
    skill_code: str
    skill_name: str
    diagnostic_state: DiagnosticState
    evidence_count: int
    correct_count: int
    confidence_class: ConfidenceClass
    recommended_action: str
    is_recommended_start: bool = False
    prerequisite_depth: int = 0


class DiagnosticResult(BaseModel):
    id: str
    session_id: str
    user_id: str
    subject: str
    enrolled_grade: int
    exam_track: str
    overall_readiness: OverallReadiness
    operating_level_band: str
    summary: str
    total_items_answered: int
    correct_items_count: int
    skill_results: List[DiagnosticSkillResult] = Field(default_factory=list)
    prerequisite_gaps: List[str] = Field(default_factory=list)
    feature3_contract_payload: List[Feature3SkillEvidence] = Field(default_factory=list)
    engine_version: str = "2.0.0"
    created_at: Optional[datetime] = None


class DiagnosticStartRequest(BaseModel):
    subject: str = "Mathematics"
    retake: bool = False


class AnswerSubmissionRequest(BaseModel):
    item_id: str
    student_response: Any
    response_time_ms: int = 0


class DiagnosticStepResponse(BaseModel):
    session: DiagnosticSession
    current_question: Optional[StudentItemView] = None
    is_completed: bool = False
    result: Optional[DiagnosticResult] = None
