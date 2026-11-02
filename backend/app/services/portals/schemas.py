from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date


# ─── 1. PARENT PORTAL SCHEMAS ─────────────────────────────────────────────────

class ParentChildView(BaseModel):
    student_id: str
    student_name: str
    email: str
    grade_or_class: str
    curriculum: str
    target_exam: Optional[str] = None
    total_xp: int = 0
    current_streak: int = 0
    mastered_skills_count: int = 0
    in_progress_skills_count: int = 0
    needs_repair_count: int = 0
    active_mistakes_count: int = 0
    recent_activity_date: Optional[date] = None


class LinkChildRequest(BaseModel):
    invitation_code: str
    relationship: str = "guardian"


class ChildMistakeAlert(BaseModel):
    skill_id: str
    skill_name: str
    error_type: str
    pattern_status: str
    occurrence_count: int
    recommended_repair_action: str


class ChildDetailedProgress(BaseModel):
    student: ParentChildView
    mastery_breakdown: Dict[str, Any]
    active_mistake_alerts: List[ChildMistakeAlert]
    recent_quiz_scores: List[Dict[str, Any]]


class ParentDashboardSummary(BaseModel):
    parent_id: str
    linked_children: List[ParentChildView]
    unread_alerts_count: int


# ─── 2. TEACHER PORTAL SCHEMAS ────────────────────────────────────────────────

class CreateClassroomRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    grade_level: str = "Class 10"
    academic_stream: str = "general"
    academic_year: str = "2026-2027"


class ClassroomView(BaseModel):
    id: str
    school_id: str
    teacher_id: str
    name: str
    grade_level: str
    academic_stream: str
    academic_year: str
    student_count: int
    average_mastery_percentage: int
    created_at: datetime


class ClassroomRosterItem(BaseModel):
    student_id: str
    student_name: str
    email: str
    enrolled_at: datetime
    mastery_percentage: int
    diagnostic_completed: bool
    pending_repairs_count: int


class ClassroomMisconceptionSummary(BaseModel):
    skill_id: str
    skill_name: str
    error_type: str
    affected_students_count: int
    recommended_reteach_strategy: str


class TeacherDashboardSummary(BaseModel):
    teacher_id: str
    classrooms: List[ClassroomView]
    total_students: int
    active_assignments_count: int
    top_class_misconceptions: List[ClassroomMisconceptionSummary]


# ─── 3. SCHOOL ADMINISTRATOR PORTAL SCHEMAS ───────────────────────────────────

class SchoolStats(BaseModel):
    total_students: int
    total_teachers: int
    total_classrooms: int
    average_school_mastery: int
    active_live_quizzes_today: int


class TeacherAssignmentItem(BaseModel):
    teacher_id: str
    teacher_name: str
    email: str
    department: str
    assigned_classrooms_count: int
    status: str


class SchoolOverview(BaseModel):
    school_id: str
    school_name: str
    domain: Optional[str] = None
    subscription_tier: str
    licensed_seats: int
    allocated_seats: int
    stats: SchoolStats
    teachers: List[TeacherAssignmentItem]


# ─── 4. CONTENT CREATOR PORTAL SCHEMAS ────────────────────────────────────────

class ItemBankSummary(BaseModel):
    total_items: int
    mcq_count: int
    numeric_count: int
    derivation_count: int
    verified_items_count: int
    domains_covered_count: int


class CreatorDashboardSummary(BaseModel):
    creator_id: str
    item_bank_stats: ItemBankSummary
    recent_published_modules: List[Dict[str, Any]]
    curriculum_domains_count: int
    pending_review_items_count: int


class CreatePracticeItemRequest(BaseModel):
    skill_id: str
    subject: str = "Mathematics"
    grade_band: str = "secondary"
    difficulty_band: str = "STANDARD"
    question_type: str = "MCQ"
    prompt: str
    options: List[str]
    correct_answer: str
    explanation: str
    hints: List[str] = []
    target_mistake_types: List[str] = []


# ─── 5. SUPER ADMINISTRATOR PORTAL SCHEMAS ────────────────────────────────────

class LLMProviderTelemetry(BaseModel):
    provider_name: str
    model_name: str
    status: str
    error_rate_percentage: float
    average_latency_ms: int
    tokens_consumed_today: int
    circuit_breaker_state: str


class SystemHealthOverview(BaseModel):
    platform_version: str
    active_mode: str
    total_users: int
    total_sessions_today: int
    database_status: str
    llm_providers: List[LLMProviderTelemetry]
    error_log_summary: Dict[str, int]


class UserRoleUpdate(BaseModel):
    target_user_id: str
    new_role: str


# ─── 6. STUDENT PERSONALIZED ROADMAP SCHEMAS (STAGE 8: 30/50/20) ───────────────

class RoadmapTaskChoice(BaseModel):
    task_id: str
    title: str
    category: str  # "SPACED_ERROR_REPAIR" (30%), "CORE_PROGRESSION" (50%), "INTERLEAVED_TRANSFER" (20%)
    weight_percentage: int
    skill_id: str
    skill_name: str
    why_recommended: str
    expected_duration_minutes: int
    current_mastery_state: str
    unlocks_next: str
    action_route: str


class DailyPersonalizedRoadmap(BaseModel):
    user_id: str
    target_exam: str
    daily_goal_minutes: int
    tasks: List[RoadmapTaskChoice]
    recalculated_at: datetime

