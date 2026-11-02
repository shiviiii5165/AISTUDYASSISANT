"""
LearnByGenie — Learner Context Service Package
"""

from app.services.learner_context.service import LearnerContextService
from app.services.learner_context.schemas import (
    LearnerProfileBase,
    LearnerProfileCreate,
    LearnerProfileUpdate,
    LearnerProfileResponse,
    LearnerContext,
    ProfileCompleteness,
    AcademicConfigResponse
)
from app.services.learner_context.academic_catalog import (
    EducationStage,
    EDUCATION_LEVELS,
    CURRICULA,
    EXAM_TRACKS,
    ACADEMIC_STREAMS,
    CANONICAL_SUBJECTS,
    ACADEMIC_GOALS,
    LANGUAGES
)

__all__ = [
    "LearnerContextService",
    "LearnerProfileBase",
    "LearnerProfileCreate",
    "LearnerProfileUpdate",
    "LearnerProfileResponse",
    "LearnerContext",
    "ProfileCompleteness",
    "AcademicConfigResponse",
    "EducationStage",
    "EDUCATION_LEVELS",
    "CURRICULA",
    "EXAM_TRACKS",
    "ACADEMIC_STREAMS",
    "CANONICAL_SUBJECTS",
    "ACADEMIC_GOALS",
    "LANGUAGES"
]
