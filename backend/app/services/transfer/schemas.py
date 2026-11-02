"""
LearnByGenie — Feature 7: AI-Off Transfer Check Schemas
=========================================================
Canonical data contracts for independent verification:
- Strict AI-off boundaries (assistance_level = INDEPENDENT)
- Near-transfer vs. Far-transfer representations
- Non-judgmental pedagogical states (PASSED, NEEDS_MORE_EVIDENCE, ABORTED)
- Leak-free student item projections
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid
from pydantic import BaseModel, Field


class TransferTrigger(str, Enum):
    """Event that qualified the student for independent transfer verification (§2)."""
    TUTOR_REPAIR = "TUTOR_REPAIR"              # Tutor repair turn sequence completed successfully
    PRACTICE_REPAIR = "PRACTICE_REPAIR"        # Adaptive Practice repair session solved correctly
    MISTAKE_DNA_REPAIR = "MISTAKE_DNA_REPAIR"  # Mistake pattern recently addressed
    MASTERY_PROVISIONAL = "MASTERY_PROVISIONAL"# Concept reached developing/provisional mastery
    STUDENT_REQUEST = "STUDENT_REQUEST"        # Student opted to test independence
    MANUAL = "MANUAL"                          # Direct verification request


class TransferLevel(str, Enum):
    """Near vs Far Transfer level (§5)."""
    NEAR_TRANSFER = "NEAR_TRANSFER"  # Same skill, novel problem/context
    FAR_TRANSFER = "FAR_TRANSFER"    # Skill applied in cross-domain or novel applied context


class TransferSessionStatus(str, Enum):
    """Durable transfer session lifecycle states (§10, §12)."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    PASSED = "PASSED"
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"
    ABORTED = "ABORTED"


class TransferOutcome(str, Enum):
    """Evaluative outcome of an independent transfer attempt (§10)."""
    PASSED = "PASSED"                        # Solved independently without support
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE" # Incorrect; requires further practice/repair
    ABORTED = "ABORTED"                      # Interrupted by support request or abandonment


class TransferPolicyConfig(BaseModel):
    """Versioned policy configuration (§9)."""
    version: str = "1.0.0"
    required_independence: str = "INDEPENDENT"
    question_budget: int = 1
    allow_hints: bool = False
    allow_tutor_help: bool = False
    allow_answer_reveal: bool = False
    cooldown_seconds_after_failure: int = 300
    require_novel_item: bool = True
    support_near_transfer: bool = True
    support_far_transfer: bool = True
    pass_threshold_independent_correct: int = 1


class TransferEligibilityResult(BaseModel):
    """Result of checking whether a transfer check can trigger (§2, §42)."""
    is_eligible: bool
    skill_id: str
    trigger: TransferTrigger
    reason: str
    cooldown_remaining_seconds: int = 0
    available_items_count: int = 0


class TransferSession(BaseModel):
    """
    Durable, server-authoritative transfer check session (§12).
    Canonical source of truth in PostgreSQL.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    skill_id: str
    subject: str
    source_trigger: TransferTrigger = TransferTrigger.PRACTICE_REPAIR
    source_trigger_id: str = ""
    transfer_level: TransferLevel = TransferLevel.NEAR_TRANSFER
    policy_version: str = "1.0.0"
    current_item_id: Optional[str] = None

    status: TransferSessionStatus = TransferSessionStatus.IN_PROGRESS
    question_index: int = 0
    question_budget: int = 1
    support_lock_active: bool = True
    abort_reason: Optional[str] = None
    trigger_explanation: str = ""

    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TransferResponse(BaseModel):
    """
    Append-only transfer check response telemetry (§13).
    Strictly records assistance_level = INDEPENDENT.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    user_id: str
    item_id: str
    skill_id: str
    question_index: int = 0
    student_response: Any
    correctness: bool
    assistance_level: str = "INDEPENDENT"
    attempt_sequence: int = 1
    response_time_ms: int = 0
    validator_result: Dict[str, Any] = Field(default_factory=dict)
    transfer_outcome: TransferOutcome = TransferOutcome.PASSED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StudentTransferItemView(BaseModel):
    """
    Sanitized, leak-free student question view (§1, §38).
    Strictly omits correct answers, solutions, and unrevealed hints.
    """
    session_id: str
    item_id: str
    skill_id: str
    subject: str
    grade_band: str
    prompt: str
    options: List[str] = Field(default_factory=list)
    question_type: str = "mcq"
    transfer_level: TransferLevel = TransferLevel.NEAR_TRANSFER
    transfer_badge_text: str = "Independent Check"
    why_explanation: str = ""
    support_disabled: bool = True


class TransferFeedback(BaseModel):
    """
    Educational feedback after an independent transfer attempt (§10, §32).
    Zero shaming, zero gamification, zero fake scores.
    """
    session_id: str
    item_id: str
    skill_id: str
    correctness: bool
    outcome: TransferOutcome
    feedback_headline: str
    educational_explanation: str
    recommended_next_action: str
    is_session_complete: bool = True


class TransferSummary(BaseModel):
    """Pedagogical summary of completed transfer check (§41)."""
    session_id: str
    user_id: str
    skill_id: str
    subject: str
    source_trigger: TransferTrigger
    transfer_level: TransferLevel
    outcome: TransferOutcome
    status: TransferSessionStatus
    duration_seconds: int = 0
    headline: str
    explanation: str
    next_step: str
