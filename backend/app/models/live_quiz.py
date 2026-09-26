"""
Pydantic Request & Response Wire Models for Live Classroom Quiz API (VNext)
============================================================================
Contracts for the /api/live-quizzes/* endpoints.
"""
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


class StartLiveSessionRequest(BaseModel):
    mode: Literal["teacher_led", "student_paced"] = "teacher_led"
    timer_seconds: int = Field(default=30, ge=5, le=300)
    speed_bonus: bool = False
    sound_fx: bool = True
    leaderboard_enabled: bool = True
    show_correctness_immediately: bool = True


class JoinSessionRequest(BaseModel):
    join_code: str = Field(..., min_length=6, max_length=6)
    display_name: str = Field(..., min_length=1, max_length=40)
    avatar_seed: Optional[str] = None


class SubmitLiveResponseRequest(BaseModel):
    question_id: str
    selected_option_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    progression_token: Optional[str] = None
    response_time_ms: Optional[int] = 0


class BanParticipantRequest(BaseModel):
    reason: Optional[str] = "Removed by teacher"


class ActivitySignalRequest(BaseModel):
    signal_type: str
    metadata: Optional[Dict[str, Any]] = None


class InterventionRequest(BaseModel):
    type: Literal["explain", "visual", "example", "followup"]
    question_id: Optional[str] = None


class UpdateSettingsRequest(BaseModel):
    sound_fx: Optional[bool] = None
    leaderboard_enabled: Optional[bool] = None
    show_correctness_immediately: Optional[bool] = None


class ParticipantJoinResponse(BaseModel):
    participant_id: str
    session_id: str
    display_name: str
    avatar_seed: str
    participant_token: str
    status: str
