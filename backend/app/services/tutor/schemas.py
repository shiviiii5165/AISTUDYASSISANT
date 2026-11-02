"""
LearnByGenie — Feature 4: Personalized Socratic Tutor V2 Schemas
================================================================
Canonical data contracts for:
- Socratic pedagogical state machine (ORIENT -> EXPLAIN -> CHECK -> HINT -> RETEACH -> APPLY -> WRAP_UP)
- Hint Ladder (HINT_1 -> HINT_2 -> HINT_3 -> HINT_4 -> FULL_EXPLANATION)
- Bounded TutorContext (consuming LearnerContextService & MasteryGraphService)
- Checking questions and evidence contracts
- Deterministic STEM verification
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid
from pydantic import BaseModel, Field

from app.services.mastery.schemas import MasteryState, ReadinessState, AssistanceLevel, EvidenceSource


# ─── ENUMS ────────────────────────────────────────────────────────────────────

class TutorMode(str, Enum):
    QUICK_ASK = "QUICK_ASK"
    TUTOR = "TUTOR"


class PedagogicalState(str, Enum):
    ORIENT = "ORIENT"       # Identify what student knows / starting baseline
    EXPLAIN = "EXPLAIN"     # Teach one manageable conceptual chunk
    CHECK = "CHECK"         # Ask one meaningful checking question
    HINT = "HINT"           # Progressive assistance on partial/stuck response
    RETEACH = "RETEACH"     # Use a different, simpler analogy for misunderstanding
    APPLY = "APPLY"         # Deepen with application or next concept
    WRAP_UP = "WRAP_UP"     # Milestone recap after verified checks


class HintLevel(str, Enum):
    NONE = "NONE"
    HINT_1 = "HINT_1"                   # Intuitive conceptual direction
    HINT_2 = "HINT_2"                   # Identify relevant principle / rule
    HINT_3 = "HINT_3"                   # Partial mathematical / logical setup
    HINT_4 = "HINT_4"                   # Worked intermediate step
    FULL_EXPLANATION = "FULL_EXPLANATION" # Complete worked solution (escape hatch)


class CheckType(str, Enum):
    OBJECTIVE_MCQ = "OBJECTIVE_MCQ"
    OBJECTIVE_NUMERIC = "OBJECTIVE_NUMERIC"
    CONCEPTUAL_EXPLANATION = "CONCEPTUAL_EXPLANATION"


class CheckOutcome(str, Enum):
    CORRECT = "CORRECT"
    PARTIALLY_CORRECT = "PARTIALLY_CORRECT"
    INCORRECT = "INCORRECT"
    UNCERTAIN = "UNCERTAIN"


# ─── MODELS ───────────────────────────────────────────────────────────────────

class STEMVerificationResult(BaseModel):
    """Deterministic STEM calculation / numerical verification result (§19)."""
    is_verified: bool
    expression: str
    computed_value: Optional[float] = None
    expected_value: Optional[float] = None
    error_margin: Optional[float] = None
    note: str = ""


class TutorCheck(BaseModel):
    """An explicit pedagogical checking question (§15, §18)."""
    check_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    skill_id: str
    skill_name: str
    question: str
    expected_answer: Optional[str] = None
    check_type: CheckType = CheckType.CONCEPTUAL_EXPLANATION
    hints_ladder: List[str] = Field(default_factory=list)
    attempts_count: int = 0
    status: str = "PENDING"  # "PENDING", "ANSWERED", "SKIPPED"
    idempotency_key: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])


class BoundedTutorContext(BaseModel):
    """
    Compact, token-bounded educational context (§5, §6, §7).
    Never injects the full graph, raw PDF text, or infinite history.
    """
    education_level: str = "Class 10"
    education_stage: str = "SECONDARY"
    curriculum: str = "CBSE"
    exam_track: Optional[str] = None
    explanation_language: str = "English"  # "English", "Hindi", "Hinglish"
    target_subject: str = "Mathematics"
    target_skill_id: Optional[str] = None
    target_skill_name: Optional[str] = None
    mastery_state: Optional[str] = None
    readiness_state: Optional[str] = None
    blocking_prerequisites: List[str] = Field(default_factory=list)
    repair_path: List[str] = Field(default_factory=list)
    recommended_start: Optional[str] = None
    retrieved_material: List[Dict[str, Any]] = Field(default_factory=list)


class TutorSessionState(BaseModel):
    """Durable multi-turn learning session state (§27, §28)."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_mode: TutorMode = TutorMode.TUTOR
    target_subject: str = "Mathematics"
    target_skill_id: Optional[str] = None
    pedagogical_state: PedagogicalState = PedagogicalState.ORIENT
    assistance_level: AssistanceLevel = AssistanceLevel.INDEPENDENT
    hint_level: HintLevel = HintLevel.NONE
    current_check: Optional[TutorCheck] = None
    checks_passed: int = 0
    checks_total: int = 0
    history: List[Dict[str, str]] = Field(default_factory=list) # [{role, content}]
    source_references: List[Dict[str, Any]] = Field(default_factory=list)
    engine_version: str = "2.0.0"
    state_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TutorTurnResponse(BaseModel):
    """Comprehensive user-facing response from Socratic Tutor V2 (§34)."""
    session_id: str
    message: str
    mode: TutorMode
    pedagogical_state: PedagogicalState
    active_check: Optional[TutorCheck] = None
    active_hints: Optional[str] = None
    hint_level: HintLevel = HintLevel.NONE
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    prerequisite_repair: Optional[Dict[str, Any]] = None
    mastery_feedback: Optional[str] = None
    stem_verification: Optional[STEMVerificationResult] = None
