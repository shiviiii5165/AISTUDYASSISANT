"""
LearnByGenie — Learner Context Pydantic Schemas
Strict typing for learner profiles, updates, learner context adapter, and completeness.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class ProfileCompleteness(BaseModel):
    is_complete: bool = Field(..., description="Whether the core educational fields are populated")
    status: str = Field(..., description="Deterministic status message e.g. 'Profile ready' or 'Needs academic goal'")
    completion_percentage: int = Field(..., description="Transparent deterministic percentage 0-100")
    missing_fields: List[str] = Field(default_factory=list, description="List of uncompleted required fields")


class AcademicConfigResponse(BaseModel):
    education_levels: List[Dict[str, Any]]
    curricula: List[Dict[str, Any]]
    academic_streams: List[Dict[str, Any]]
    exam_tracks: List[Dict[str, Any]]
    subjects: List[Dict[str, Any]]
    academic_goals: List[Dict[str, Any]]
    languages: List[Dict[str, Any]]
    session_durations_minutes: List[int]


class LearnerProfileBase(BaseModel):
    education_level: str = Field("class_11", description="Canonical level ID e.g. 'class_11', 'class_10', 'ug_year_1'")
    grade_or_class: str = Field("Class 11", description="Human-readable class name e.g. 'Class 11'")
    education_stage: str = Field("SENIOR_SECONDARY", description="Stage: PRIMARY, MIDDLE, SECONDARY, SENIOR_SECONDARY, EXAM_PREP, UNDERGRADUATE")
    board_or_curriculum: str = Field("CBSE", description="Curriculum or Board e.g. CBSE, ICSE_ISC, STATE_BOARD, IB, CAMBRIDGE, UNIVERSITY")
    academic_stream: Optional[str] = Field("science_pcm", description="Stream e.g. science_pcm, science_pcb, commerce, humanities, general")
    target_exam: Optional[str] = Field("JEE", description="Target exam track e.g. JEE, NEET, BOARDS, SCHOOL_EXAMS, UG_SEMESTER, FOUNDATION")
    target_year: Optional[int] = Field(None, description="Target completion/exam year")
    subjects: List[str] = Field(default_factory=lambda: ["Physics", "Chemistry", "Mathematics"])
    
    preferred_language: str = Field("hinglish", description="Primary preferred language code e.g. hinglish, en, hi")
    secondary_language: Optional[str] = Field("en", description="Secondary language code e.g. en, hi")
    explanation_language_preference: str = Field("hinglish", description="Explanation tone/language e.g. hinglish, en, hi")
    country_or_region: str = Field("IN", description="Country/region code")
    
    short_term_goal: Optional[str] = Field(None, description="Short term goal e.g. 'Master Kinematics and revise mechanics'")
    long_term_goal: Optional[str] = Field(None, description="Long term goal e.g. 'Excel in JEE Advanced 2027'")
    weekly_study_availability_hours: Optional[float] = Field(10.0, description="Hours available for study per week")
    preferred_session_minutes: int = Field(30, description="Session length in minutes (15, 30, 45, 60)")
    
    content_difficulty_preference: str = Field("standard", description="foundational, standard, advanced")
    voice_preference: str = Field("neutral", description="Voice tone preference")
    accessibility_preferences: Dict[str, Any] = Field(default_factory=dict)
    
    onboarding_completed: bool = Field(False, description="Whether onboarding has been completed")


class LearnerProfileCreate(LearnerProfileBase):
    pass


class LearnerProfileUpdate(BaseModel):
    education_level: Optional[str] = None
    grade_or_class: Optional[str] = None
    education_stage: Optional[str] = None
    board_or_curriculum: Optional[str] = None
    academic_stream: Optional[str] = None
    target_exam: Optional[str] = None
    target_year: Optional[int] = None
    subjects: Optional[List[str]] = None
    preferred_language: Optional[str] = None
    secondary_language: Optional[str] = None
    explanation_language_preference: Optional[str] = None
    country_or_region: Optional[str] = None
    short_term_goal: Optional[str] = None
    long_term_goal: Optional[str] = None
    weekly_study_availability_hours: Optional[float] = None
    preferred_session_minutes: Optional[int] = None
    content_difficulty_preference: Optional[str] = None
    voice_preference: Optional[str] = None
    accessibility_preferences: Optional[Dict[str, Any]] = None
    onboarding_completed: Optional[bool] = None


class LearnerProfileResponse(LearnerProfileBase):
    user_id: str
    profile_version: int = 1
    completeness: ProfileCompleteness
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EducationContext(BaseModel):
    level: str
    level_id: str
    stage: str
    board: str
    stream: Optional[str] = None
    exam_tracks: List[str] = Field(default_factory=list)


class GoalsContext(BaseModel):
    primary: Optional[str] = None
    short_term: Optional[str] = None
    long_term: Optional[str] = None
    target_year: Optional[int] = None


class PreferencesContext(BaseModel):
    preferred_language: str
    secondary_language: Optional[str] = None
    explanation_language: str
    content_difficulty: str
    preferred_session_minutes: int
    weekly_study_availability_hours: Optional[float] = None
    voice_preference: str = "neutral"


class LearningActivitySummary(BaseModel):
    recent_subjects: List[str] = Field(default_factory=list)
    total_documents: int = 0
    total_quiz_attempts: int = 0
    last_active: Optional[str] = None


class LearnerContext(BaseModel):
    """
    The canonical Learner Context consumed by AI Chat, Teach Me, Tutor,
    and all downstream intelligence modules.
    Contains NO fabricated mastery scores or rank predictions.
    """
    student_id: str
    role: str = "student"
    profile_version: int = 1
    education: EducationContext
    goals: GoalsContext
    subjects: List[str] = Field(default_factory=list)
    preferences: PreferencesContext
    profile_completeness: ProfileCompleteness
    learning_activity_summary: LearningActivitySummary
    mistake_dna_summary: Optional[Dict[str, Any]] = None
    practice_summary: Optional[Dict[str, Any]] = None
