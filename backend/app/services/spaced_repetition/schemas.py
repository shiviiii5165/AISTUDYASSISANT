from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date
from enum import Enum


class CardType(str, Enum):
    CONCEPT_CHECK = "concept_check"
    FORMULA_RECALL = "formula_recall"
    MISTAKE_AVOIDANCE = "mistake_avoidance"


class SpacedCard(BaseModel):
    id: str
    user_id: str
    skill_id: str
    card_type: CardType
    prompt: str
    answer: str
    explanation: str = ""
    ease_factor: float = 2.50
    interval_days: int = 1
    repetition_number: int = 0
    next_review_date: date
    created_at: datetime
    updated_at: datetime


class ReviewSubmissionRequest(BaseModel):
    card_id: str
    quality_rating: int = Field(..., ge=0, le=5, description="0=Complete blackout, 3=Passed with effort, 5=Perfect instant recall")


class ReviewFeedbackResponse(BaseModel):
    card_id: str
    quality_rating: int
    previous_interval: int
    new_interval: int
    previous_ease_factor: float
    new_ease_factor: float
    next_review_date: date
    xp_awarded: int


class QueueSummaryResponse(BaseModel):
    user_id: str
    total_cards: int
    due_today_count: int
    upcoming_this_week_count: int
    cards: List[SpacedCard]

