"""
LearnByGenie — Learner Profile Validation Engine
Deterministic backend validation ensuring academic consistency,
stage compatibility, valid subjects, language codes, and time ranges.
"""

from datetime import datetime
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from app.services.learner_context.academic_catalog import (
    EDUCATION_LEVELS,
    CURRICULA,
    EXAM_TRACKS,
    ACADEMIC_STREAMS,
    LANGUAGES,
    EducationStage,
    get_stage_for_level
)

VALID_LEVEL_IDS = {lvl["id"] for lvl in EDUCATION_LEVELS}
VALID_CURRICULA = {cur["id"] for cur in CURRICULA}
VALID_EXAMS = {ex["id"] for ex in EXAM_TRACKS}
VALID_LANGUAGES = {lang["id"] for lang in LANGUAGES} | {lang["code"] for lang in LANGUAGES}


def validate_education_level(level_id: str) -> Tuple[str, str, str]:
    """
    Validates level ID and returns (canonical_id, grade_name, stage).
    Raises HTTPException(400) if invalid.
    """
    clean = (level_id or "").strip().lower()
    for lvl in EDUCATION_LEVELS:
        if lvl["id"].lower() == clean or lvl["name"].lower() == clean:
            return lvl["id"], lvl["name"], lvl["stage"]
            
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid education level '{level_id}'. Must be one of: {sorted(list(VALID_LEVEL_IDS))}"
    )


def validate_academic_stream(level_id: str, stage: str, stream: Optional[str]) -> Optional[str]:
    """
    Validates that academic streams are only assigned to eligible stages (Class 11, 12, UG).
    """
    if not stream or stream.lower() in ("none", "null", ""):
        return "general" if stage in (EducationStage.PRIMARY, EducationStage.MIDDLE, EducationStage.SECONDARY) else None

    clean_stream = stream.strip().lower()

    if stage in (EducationStage.PRIMARY, EducationStage.MIDDLE, EducationStage.SECONDARY):
        if clean_stream not in ("general", "none"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Education stage {stage} does not support specialized academic stream '{stream}'. Must be 'general' or omitted."
            )
        return "general"

    # For Senior Secondary
    if stage in (EducationStage.SENIOR_SECONDARY, EducationStage.EXAM_PREP):
        allowed = {"science_pcm", "science_pcb", "commerce", "humanities", "general"}
        if clean_stream not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid stream '{stream}' for {stage}. Allowed: {sorted(list(allowed))}"
            )
        return clean_stream

    # For Undergraduate
    if stage == EducationStage.UNDERGRADUATE:
        allowed = {"engineering_cs", "engineering_core", "basic_sciences", "commerce_finance", "humanities"}
        if clean_stream not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid stream '{stream}' for Undergraduate. Allowed: {sorted(list(allowed))}"
            )
        return clean_stream

    return clean_stream


def validate_exam_track(stage: str, exam: Optional[str]) -> Optional[str]:
    """
    Validates exam track compatibility with education stage.
    JEE / NEET are only permissible for SENIOR_SECONDARY and EXAM_PREP.
    """
    if not exam or exam.upper() in ("NONE", "NULL", ""):
        return "FOUNDATION"

    clean_exam = exam.strip().upper()
    if clean_exam not in VALID_EXAMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid exam track '{exam}'. Allowed tracks: {sorted(list(VALID_EXAMS))}"
        )

    # JEE & NEET restriction: Not allowed for Primary or Middle school
    if clean_exam in ("JEE", "NEET"):
        if stage in (EducationStage.PRIMARY, EducationStage.MIDDLE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exam track '{clean_exam}' is only available for Senior Secondary (Class 11-12) or Exam Prep stages, not {stage}."
            )

    # UG Semester restriction
    if clean_exam == "UG_SEMESTER" and stage != EducationStage.UNDERGRADUATE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam track 'UG_SEMESTER' is only applicable for Undergraduate coursework."
        )

    return clean_exam


def validate_target_year(year: Optional[int]) -> Optional[int]:
    """
    Validates target examination or completion year within a realistic horizon.
    """
    if year is None:
        return None
        
    current_year = datetime.now().year
    min_year = current_year - 1
    max_year = current_year + 8

    if not (min_year <= year <= max_year):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target year {year} is invalid. Must be between {min_year} and {max_year}."
        )
    return year


def validate_subjects(subjects: Optional[List[str]]) -> List[str]:
    """
    Validates and sanitizes selected subject list.
    """
    if subjects is None:
        return []

    cleaned = []
    for s in subjects:
        if not isinstance(s, str):
            continue
        item = s.strip()
        if not item or len(item) > 60:
            continue
        if item not in cleaned:
            cleaned.append(item)

    if len(cleaned) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one valid subject must be selected."
        )

    return cleaned


def validate_language(lang: Optional[str]) -> str:
    """
    Validates preferred language code.
    """
    if not lang:
        return "hinglish"

    clean_lang = lang.strip().lower()
    if clean_lang not in VALID_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid language '{lang}'. Supported: {sorted(list(VALID_LANGUAGES))}"
        )
    return clean_lang


def validate_session_minutes(minutes: Optional[int]) -> int:
    """
    Validates preferred session duration.
    """
    if minutes is None:
        return 30
    if not (10 <= minutes <= 180):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session minutes {minutes} out of range. Must be between 10 and 180 minutes."
        )
    return minutes


def validate_weekly_hours(hours: Optional[float]) -> Optional[float]:
    """
    Validates weekly study availability hours.
    """
    if hours is None:
        return 10.0
    if not (1.0 <= hours <= 100.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Weekly study hours {hours} out of range. Must be between 1.0 and 100.0 hours."
        )
    return round(float(hours), 1)
