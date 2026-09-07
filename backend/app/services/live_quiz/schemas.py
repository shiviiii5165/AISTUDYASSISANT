"""
Live Quiz Engine — Core Domain Schemas & Contracts
==================================================
Strict domain models mirroring migration 014_live_quiz.sql.
Includes zero-leakage student sanitizers and event contracts.
"""
from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field


class LiveSessionStatus(str, Enum):
    CREATED = "CREATED"
    LOBBY = "LOBBY"
    LIVE = "LIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ENDED = "ENDED"
    EXPIRED = "EXPIRED"


# Active states where 6-digit join codes must remain unique
ACTIVE_SESSION_STATUSES = {
    LiveSessionStatus.CREATED,
    LiveSessionStatus.LOBBY,
    LiveSessionStatus.LIVE,
    LiveSessionStatus.PAUSED,
}

TERMINATED_SESSION_STATUSES = {
    LiveSessionStatus.COMPLETED,
    LiveSessionStatus.ENDED,
    LiveSessionStatus.EXPIRED,
}


class LiveSessionMode(str, Enum):
    TEACHER_LED = "teacher_led"
    STUDENT_PACED = "student_paced"


class LiveParticipantStatus(str, Enum):
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    LEFT = "left"


class LiveEventType(str, Enum):
    SESSION_CREATED = "SESSION_CREATED"
    PARTICIPANT_JOINED = "PARTICIPANT_JOINED"
    PARTICIPANT_LEFT = "PARTICIPANT_LEFT"
    SESSION_STARTED = "SESSION_STARTED"
    QUESTION_STARTED = "QUESTION_STARTED"
    RESPONSE_SUBMITTED = "RESPONSE_SUBMITTED"
    QUESTION_REVEALED = "QUESTION_REVEALED"
    QUESTION_SKIPPED = "QUESTION_SKIPPED"
    SESSION_PAUSED = "SESSION_PAUSED"
    SESSION_RESUMED = "SESSION_RESUMED"
    INTERVENTION_TRIGGERED = "INTERVENTION_TRIGGERED"
    SESSION_ENDED = "SESSION_ENDED"


class LiveTimerConfig(BaseModel):
    enabled: bool = True
    seconds: int = 30
    speed_bonus: bool = False


class LiveSessionSettings(BaseModel):
    sound_fx: bool = True
    leaderboard_enabled: bool = True
    show_correctness_immediately: bool = True


class LiveParticipant(BaseModel):
    id: str
    session_id: str
    user_id: Optional[str] = None
    display_name: str
    avatar_seed: Optional[str] = None
    status: LiveParticipantStatus = LiveParticipantStatus.ACTIVE
    joined_at: Optional[datetime] = None
    connected_at: Optional[datetime] = None
    disconnected_at: Optional[datetime] = None
    score: int = 0
    correct_count: int = 0
    answered_count: int = 0
    streak: int = 0


class LiveResponse(BaseModel):
    id: Optional[str] = None
    session_id: str
    participant_id: str
    question_id: str
    selected_option_id: Optional[str] = None
    submitted_at: Optional[datetime] = None
    response_time_ms: int = 0
    is_correct: Optional[bool] = None
    points: int = 0
    attempt_number: int = 1
    concept_id: Optional[str] = None
    objective_id: Optional[str] = None
    idempotency_key: Optional[str] = None


class LiveQuizSession(BaseModel):
    id: str
    quiz_id: str
    host_user_id: str
    organization_id: Optional[str] = None
    join_code: str
    status: LiveSessionStatus = LiveSessionStatus.CREATED
    mode: LiveSessionMode = LiveSessionMode.TEACHER_LED
    current_question_index: int = 0
    current_question_started_at: Optional[datetime] = None
    current_question_deadline: Optional[datetime] = None
    total_questions: int = 0
    timer_config: LiveTimerConfig = Field(default_factory=LiveTimerConfig)
    settings: LiveSessionSettings = Field(default_factory=LiveSessionSettings)
    questions_snapshot: List[Dict[str, Any]] = Field(default_factory=list)
    question_order: List[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    version: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


def to_student_question_dict(q_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Zero-Leakage Invariant:
    Pre-reveal payload sent to students strictly omits correct_answer and explanation.
    """
    return {
        "id": q_dict.get("id"),
        "question_text": q_dict.get("question_text"),
        "type": q_dict.get("type", "mcq"),
        "options": list(q_dict.get("options", [])),
        "difficulty": q_dict.get("difficulty", "medium"),
        "order_index": q_dict.get("order_index", 0),
        "concept_id": q_dict.get("concept_id"),
    }
