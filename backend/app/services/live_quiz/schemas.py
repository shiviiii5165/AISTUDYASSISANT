"""
Live Quiz Engine — Core Domain Schemas & Contracts (VNext Scale & Security)
==========================================================================
Strict domain models mirroring migrations 014_live_quiz.sql and 015_live_quiz_vnext.sql.
Includes zero-leakage student sanitizers, opaque progression tokens, and monitoring models.
"""
from __future__ import annotations
import hmac
import hashlib
import json
import base64
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field

from app.core.config import settings

_PROGRESSION_SECRET = (
    getattr(settings, "SUPABASE_JWT_SECRET", "")
    or getattr(settings, "LEARNBYGENIE_PROGRESSION_SECRET", "")
    or "learnbygenie-progression-token-secret-2026"
)
_LEGACY_PROGRESSION_SECRET = "teachgenie-progression-token-secret-2026"


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


class ConnectionState(str, Enum):
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    IDLE = "idle"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AdminActionType(str, Enum):
    BAN = "BAN"
    UNBAN = "UNBAN"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    REVEAL = "REVEAL"
    SKIP = "SKIP"
    END = "END"
    SETTINGS_UPDATE = "SETTINGS_UPDATE"


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
    # VNEXT scale & risk events
    QUESTION_OPENED = "QUESTION_OPENED"
    ANSWER_SUBMITTED = "ANSWER_SUBMITTED"
    TAB_HIDDEN = "TAB_HIDDEN"
    TAB_RETURNED = "TAB_RETURNED"
    COPY_ATTEMPT = "COPY_ATTEMPT"
    PASTE_ATTEMPT = "PASTE_ATTEMPT"
    RECONNECTED = "RECONNECTED"
    MULTI_SESSION_CONFLICT = "MULTI_SESSION_CONFLICT"
    UNUSUALLY_FAST_RESPONSE = "UNUSUALLY_FAST_RESPONSE"
    FINAL_SUBMIT = "FINAL_SUBMIT"
    PARTICIPANT_BANNED = "PARTICIPANT_BANNED"
    PARTICIPANT_UNBANNED = "PARTICIPANT_UNBANNED"
    AGGREGATED_RESPONSES = "AGGREGATED_RESPONSES"


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

    # VNEXT live snapshot fields
    current_question_index: int = 0
    average_response_ms: int = 0
    last_seen_at: Optional[datetime] = None
    connection_state: ConnectionState = ConnectionState.ACTIVE
    risk_score: int = 0
    risk_level: RiskLevel = RiskLevel.LOW
    is_banned: bool = False
    banned_at: Optional[datetime] = None
    ban_reason: Optional[str] = None
    state_version: int = 1


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


class LiveQuizQuestionStats(BaseModel):
    id: Optional[str] = None
    session_id: str
    question_id: str
    answered_count: int = 0
    correct_count: int = 0
    option_counts: Dict[str, int] = Field(default_factory=dict)
    average_response_ms: int = 0
    updated_at: Optional[datetime] = None


class LiveQuizAdminAction(BaseModel):
    id: Optional[str] = None
    admin_user_id: str
    session_id: str
    participant_id: Optional[str] = None
    action: AdminActionType
    reason: Optional[str] = None
    previous_state: Dict[str, Any] = Field(default_factory=dict)
    new_state: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


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


# ─── Opaque Question Progression Token ────────────────────────────────────────

def create_progression_token(
    session_id: str,
    question_index: int,
    question_id: str,
    deadline_iso: Optional[str] = None,
) -> str:
    """
    Issue an opaque, HMAC-SHA256 signed progression token for the current question.
    Prevents students from enumerating or guessing future questions.
    """
    payload = {
        "sid": session_id,
        "qix": question_index,
        "qid": question_id,
        "dl": deadline_iso,
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    raw_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    signature = hmac.new(
        _PROGRESSION_SECRET.encode("utf-8"),
        raw_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    encoded = base64.urlsafe_b64encode(raw_payload.encode("utf-8")).decode("utf-8")
    return f"{encoded}.{signature}"


def verify_progression_token(
    token: str,
    session_id: str,
    expected_question_index: int,
) -> Dict[str, Any]:
    """
    Validate that the token signature matches and refers to the active question.
    Raises ValueError on tampering, mismatched session, or future question attempts.
    """
    if not token or "." not in token:
        raise ValueError("Invalid progression token format")

    parts = token.split(".", 1)
    try:
        raw_payload = base64.urlsafe_b64decode(parts[0].encode("utf-8")).decode("utf-8")
        data = json.loads(raw_payload)
    except Exception as e:
        raise ValueError(f"Malformed progression token payload: {e}") from e

    expected_sig = hmac.new(
        _PROGRESSION_SECRET.encode("utf-8"),
        raw_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, parts[1]):
        legacy_sig = hmac.new(
            _LEGACY_PROGRESSION_SECRET.encode("utf-8"),
            raw_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(legacy_sig, parts[1]):
            raise ValueError("Progression token signature verification failed")

    if data.get("sid") != session_id:
        raise ValueError("Progression token does not match active session")

    token_qix = data.get("qix")
    if token_qix != expected_question_index:
        raise ValueError(
            f"Progression token question index mismatch: token index {token_qix} != authorized current index {expected_question_index}"
        )

    return data


def to_student_question_dict(
    q_dict: Dict[str, Any],
    progression_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Zero-Leakage Invariant (§2):
    Pre-reveal payload sent to students strictly omits:
      - correct_answer
      - explanation
      - future questions
      - quiz snapshot
      - teacher metadata
      - internal scoring configuration
    Includes opaque progression token.
    """
    return {
        "id": q_dict.get("id"),
        "question_text": q_dict.get("question_text"),
        "type": q_dict.get("type", "mcq"),
        "options": list(q_dict.get("options", [])),
        "difficulty": q_dict.get("difficulty", "medium"),
        "order_index": q_dict.get("order_index", 0),
        "concept_id": q_dict.get("concept_id"),
        "progression_token": progression_token,
    }
