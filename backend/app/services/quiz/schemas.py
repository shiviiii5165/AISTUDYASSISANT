"""
Quiz Engine — Core Domain Schemas
=================================
Strict Pydantic contracts mirroring migration 009_quiz_engine.sql.

Trust-boundary note (§10, §38): `QuizQuestion.correct_answer` is server-only.
The student-facing serializer (`to_student_dict`) deliberately omits it and
`explanation`, so the correct answer is never shipped to the browser before
grading. Do not add correct_answer to any student-facing payload.
"""
from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field


class QuizMode(str, Enum):
    TEACHER = "teacher"
    STUDENT = "student"


class QuizStatus(str, Enum):
    # Teacher lifecycle (§23)
    DRAFT = "draft"
    REVIEWED = "reviewed"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    # Student lifecycle (§23)
    READY = "ready"
    ATTEMPTED = "attempted"
    COMPLETED = "completed"


TEACHER_STATUSES = {QuizStatus.DRAFT, QuizStatus.REVIEWED, QuizStatus.PUBLISHED, QuizStatus.ARCHIVED}
STUDENT_STATUSES = {QuizStatus.READY, QuizStatus.ATTEMPTED, QuizStatus.COMPLETED}


class QuestionType(str, Enum):
    MCQ = "mcq"
    TRUE_FALSE = "tf"
    FILL_BLANK = "fill_blank"
    SHORT_ANSWER = "short_answer"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class AttemptStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    EXPIRED = "expired"


class SourceRef(BaseModel):
    """Citation back to a source location (§18)."""
    source_type: str = "general"
    source_id: Optional[str] = None
    page: Optional[int] = None
    slide: Optional[int] = None
    timestamp: Optional[str] = None
    snippet: Optional[str] = None


class QuizConfig(BaseModel):
    """Generation config (§49). Drives generation, allocation, and the cache key."""
    question_count: int = 10
    difficulty: Difficulty = Difficulty.MEDIUM
    types: List[QuestionType] = Field(default_factory=lambda: [QuestionType.MCQ])
    language: str = "english"
    shuffle_questions: bool = True
    shuffle_options: bool = True
    timer_seconds: Optional[int] = None          # None = untimed (§43)
    # Personalized/adaptive quizzes must NOT be cached across users (§36).
    adaptive: bool = False


class QuizQuestion(BaseModel):
    id: Optional[str] = None
    quiz_id: Optional[str] = None
    question_text: str
    type: QuestionType = QuestionType.MCQ
    options: List[str] = Field(default_factory=list)

    # SERVER-ONLY. For mcq: the correct option text (or index-as-str). For tf:
    # "true"/"false". For fill_blank/short_answer: the accepted answer(s).
    correct_answer: Union[str, List[str]] = ""
    explanation: str = ""

    difficulty: Difficulty = Difficulty.MEDIUM
    bloom_level: Optional[str] = None
    objective_id: Optional[str] = None
    concept_id: Optional[str] = None
    misconception_id: Optional[str] = None
    source_ref: Optional[SourceRef] = None
    order_index: int = 0

    def to_student_dict(self) -> Dict[str, Any]:
        """Student-facing payload — NEVER includes correct_answer or explanation."""
        return {
            "id": self.id,
            "question_text": self.question_text,
            "type": self.type.value,
            "options": list(self.options),
            "difficulty": self.difficulty.value,
            "order_index": self.order_index,
        }

    def to_db_dict(self) -> Dict[str, Any]:
        ca = self.correct_answer
        return {
            "quiz_id": self.quiz_id,
            "question_text": self.question_text,
            "type": self.type.value,
            "options": list(self.options),
            "correct_answer": ca if isinstance(ca, list) else [ca] if ca != "" else [],
            "explanation": self.explanation,
            "difficulty": self.difficulty.value,
            "bloom_level": self.bloom_level,
            "objective_id": self.objective_id,
            "concept_id": self.concept_id,
            "misconception_id": self.misconception_id,
            "source_ref": self.source_ref.dict() if self.source_ref else None,
            "order_index": self.order_index,
        }


class Quiz(BaseModel):
    id: Optional[str] = None
    owner_user_id: str
    mode: QuizMode = QuizMode.STUDENT
    title: str = "Untitled Quiz"

    organization_id: Optional[str] = None
    course_id: Optional[str] = None
    lesson_id: Optional[str] = None
    roadmap_id: Optional[str] = None
    stage_id: Optional[str] = None
    teach_session_id: Optional[str] = None

    source_type: str = "topic"
    source_ids: List[str] = Field(default_factory=list)
    topic: Optional[str] = None

    status: QuizStatus = QuizStatus.DRAFT
    version: int = 1
    config: QuizConfig = Field(default_factory=QuizConfig)
    cache_key: Optional[str] = None

    questions: List[QuizQuestion] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_db_dict(self) -> Dict[str, Any]:
        """Row for the `quizzes` table (questions are stored separately)."""
        return {
            "owner_user_id": self.owner_user_id,
            "mode": self.mode.value,
            "title": self.title,
            "organization_id": self.organization_id,
            "course_id": self.course_id,
            "lesson_id": self.lesson_id,
            "roadmap_id": self.roadmap_id,
            "stage_id": self.stage_id,
            "teach_session_id": self.teach_session_id,
            "source_type": self.source_type,
            "source_ids": list(self.source_ids),
            "topic": self.topic,
            "status": self.status.value,
            "version": self.version,
            "config": self.config.dict(),
            "cache_key": self.cache_key,
        }


class PerQuestionResult(BaseModel):
    question_id: str
    concept_id: Optional[str] = None
    given_answer: Union[str, List[str], None] = None
    is_correct: bool = False
    partial: float = 0.0                 # 0.0–1.0 for short_answer partial credit
    correct_answer: Union[str, List[str], None] = None  # revealed only post-submit


class QuizAttempt(BaseModel):
    id: Optional[str] = None
    quiz_id: str
    user_id: str
    status: AttemptStatus = AttemptStatus.IN_PROGRESS

    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    score: Optional[float] = None
    correct_count: Optional[int] = None
    total_questions: Optional[int] = None
    time_spent_seconds: Optional[int] = None

    per_question_results: List[PerQuestionResult] = Field(default_factory=list)
    concept_performance: Dict[str, Any] = Field(default_factory=dict)

    question_order_seed: int = 0
    option_order_seed: int = 0
    idempotency_key: Optional[str] = None
