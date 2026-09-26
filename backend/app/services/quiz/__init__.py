"""
Quiz Engine Service Package
===========================
Canonical quiz generation, validation, and server-side scoring for LearnByGenie.

ONE canonical Quiz model (§1): `mode` + context fields distinguish teacher vs.
student quizzes — there is no separate engine. Retrieval reuses the existing
knowledge/RAG infrastructure (§4); LLM calls go through services.ai.router (§37);
scoring, randomization, timing and aggregation are deterministic Python (§37).
"""
from .schemas import (
    QuizMode, QuizStatus, QuestionType, Difficulty, AttemptStatus,
    QuizConfig, QuizQuestion, Quiz, PerQuestionResult, QuizAttempt,
)
from .validator import validate_questions, ValidationReport

__all__ = [
    "QuizMode", "QuizStatus", "QuestionType", "Difficulty", "AttemptStatus",
    "QuizConfig", "QuizQuestion", "Quiz", "PerQuestionResult", "QuizAttempt",
    "validate_questions", "ValidationReport",
]
