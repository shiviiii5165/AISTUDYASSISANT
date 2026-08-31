"""
Pydantic Request & Response Models for the Quiz Engine API
==========================================================
Request/response contracts for the §54 endpoint list. These are the wire types;
the domain types live in app.services.quiz.schemas.
"""
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field


# ─── Config (mirrors services.quiz.schemas.QuizConfig on the wire) ───────────

class QuizConfigModel(BaseModel):
    question_count: int = 10
    difficulty: str = "medium"                       # easy|medium|hard
    types: List[str] = Field(default_factory=lambda: ["mcq"])
    language: str = "english"
    shuffle_questions: bool = True
    shuffle_options: bool = True
    timer_seconds: Optional[int] = None
    adaptive: bool = False


# ─── Generation (§54: POST /quizzes) ─────────────────────────────────────────

class GenerateQuizRequest(BaseModel):
    mode: str = "student"                            # teacher|student
    title: Optional[str] = None

    # Source selection. `source_id` is CLIENT-SUPPLIED and MUST be ownership-
    # checked server-side before any retrieval (§39).
    source_type: str = "topic"                       # topic|pdf|ppt|teach_me|stage
    source_ids: List[str] = Field(default_factory=list)
    topic: Optional[str] = None

    # Pedagogy context (optional lineage).
    roadmap_id: Optional[str] = None
    stage_id: Optional[str] = None
    lesson_id: Optional[str] = None
    teach_session_id: Optional[str] = None

    config: QuizConfigModel = Field(default_factory=QuizConfigModel)

    # Idempotency (§55): repeated generate with the same key returns the same quiz.
    idempotency_key: Optional[str] = None


# ─── Question editor (§21, §22, §50) ─────────────────────────────────────────

class QuestionEditModel(BaseModel):
    question_text: Optional[str] = None
    type: Optional[str] = None
    options: Optional[List[str]] = None
    correct_answer: Optional[Union[str, List[str]]] = None
    explanation: Optional[str] = None
    difficulty: Optional[str] = None


class ReorderQuestionsRequest(BaseModel):
    # Full ordered list of question ids; server rewrites order_index.
    ordered_question_ids: List[str]


class RegenerateQuestionRequest(BaseModel):
    # Optional steer for the single-question regeneration (Phase 3).
    instruction: Optional[str] = None
    idempotency_key: Optional[str] = None


# ─── Attempt lifecycle (§54, §57) ────────────────────────────────────────────

class StartAttemptRequest(BaseModel):
    quiz_id: str


class SubmitAnswerModel(BaseModel):
    question_id: str
    # The student's answer. NO score / is_correct is accepted from the client
    # (§10, §38) — only the raw answer, graded server-side.
    answer: Union[str, List[str], None] = None


class SubmitAttemptRequest(BaseModel):
    attempt_id: str
    answers: List[SubmitAnswerModel] = Field(default_factory=list)
    # Idempotent submission (§55, §56): a duplicate submit with the same key
    # must not double-score.
    idempotency_key: Optional[str] = None


class UpdateQuizStatusRequest(BaseModel):
    status: str                                      # draft|reviewed|published|archived
