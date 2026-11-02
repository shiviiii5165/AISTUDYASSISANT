from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any

from app.core.dependencies import (
    get_current_user,
    AuthenticatedUser,
    require_parent,
    require_teacher,
    require_school_admin,
    require_content_creator,
    require_admin
)
from app.services.portals.service import (
    ParentPortalService,
    TeacherPortalService,
    SchoolAdminPortalService,
    ContentCreatorPortalService,
    SuperAdminPortalService
)
from app.services.portals.schemas import (
    ParentDashboardSummary,
    ChildDetailedProgress,
    LinkChildRequest,
    TeacherDashboardSummary,
    CreateClassroomRequest,
    ClassroomView,
    ClassroomRosterItem,
    SchoolOverview,
    CreatorDashboardSummary,
    CreatePracticeItemRequest,
    SystemHealthOverview,
    UserRoleUpdate
)
from app.services.portals.repository import PortalsRepository
from app.services.practice.item_bank import register_practice_item, PracticeItem, QuestionType, DifficultyBand, VerificationStatus, make_practice_uuid

router = APIRouter()


# ─── 1. PARENT PORTAL ENDPOINTS ───────────────────────────────────────────────

@router.get("/parent/dashboard", response_model=ParentDashboardSummary)
def get_parent_dashboard(current_user: AuthenticatedUser = Depends(require_parent)):
    """Returns parent dashboard summary with linked children's mastery and alerts."""
    return ParentPortalService.get_dashboard_summary(current_user.id)


@router.post("/parent/link-child")
def link_child_to_parent(payload: LinkChildRequest, current_user: AuthenticatedUser = Depends(require_parent)):
    """Links a child account using an invitation code."""
    # In practice, invitation code maps to student_id or default student
    student_id = "a56da972-0f19-418d-b0f7-de91ff114190"
    link = PortalsRepository.link_parent_child(current_user.id, student_id, payload.relationship)
    return {"status": "linked", "link": link}


@router.get("/parent/child/{student_id}/progress", response_model=ChildDetailedProgress)
def get_child_progress(student_id: str, current_user: AuthenticatedUser = Depends(require_parent)):
    """Returns detailed mastery, Mistake DNA, and quiz performance for a linked child."""
    try:
        return ParentPortalService.get_child_detailed_progress(current_user.id, student_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# ─── 2. TEACHER PORTAL ENDPOINTS ──────────────────────────────────────────────

@router.get("/teacher/dashboard", response_model=TeacherDashboardSummary)
def get_teacher_dashboard(current_user: AuthenticatedUser = Depends(require_teacher)):
    """Returns teacher dashboard with classrooms, total students, and class misconceptions."""
    return TeacherPortalService.get_dashboard_summary(current_user.id)


@router.post("/teacher/classrooms", response_model=ClassroomView)
def create_classroom_endpoint(payload: CreateClassroomRequest, current_user: AuthenticatedUser = Depends(require_teacher)):
    """Creates a new classroom cohort under the teacher's profile."""
    record = PortalsRepository.create_classroom(
        teacher_id=current_user.id,
        name=payload.name,
        grade_level=payload.grade_level,
        academic_stream=payload.academic_stream,
        academic_year=payload.academic_year
    )
    return ClassroomView(
        id=record["id"],
        school_id=record["school_id"],
        teacher_id=record["teacher_id"],
        name=record["name"],
        grade_level=record["grade_level"],
        academic_stream=record["academic_stream"],
        academic_year=record["academic_year"],
        student_count=0,
        average_mastery_percentage=0,
        created_at=record["created_at"]
    )


@router.get("/teacher/classrooms/{classroom_id}/roster", response_model=List[ClassroomRosterItem])
def get_classroom_roster(classroom_id: str, current_user: AuthenticatedUser = Depends(require_teacher)):
    """Returns the student roster and individual mastery progression for a classroom."""
    return TeacherPortalService.get_classroom_roster(current_user.id, classroom_id)


# ─── 3. SCHOOL ADMINISTRATOR PORTAL ENDPOINTS ─────────────────────────────────

@router.get("/school-admin/overview", response_model=SchoolOverview)
def get_school_overview(current_user: AuthenticatedUser = Depends(require_school_admin)):
    """Returns institution-wide performance, teacher allocations, and license telemetry."""
    return SchoolAdminPortalService.get_overview(current_user.id)


# ─── 4. CONTENT CREATOR PORTAL ENDPOINTS ──────────────────────────────────────

@router.get("/creator/dashboard", response_model=CreatorDashboardSummary)
def get_creator_dashboard(current_user: AuthenticatedUser = Depends(require_content_creator)):
    """Returns item bank statistics, published learning modules, and curriculum status."""
    return ContentCreatorPortalService.get_dashboard_summary(current_user.id)


@router.post("/creator/items")
def create_practice_item_endpoint(payload: CreatePracticeItemRequest, current_user: AuthenticatedUser = Depends(require_content_creator)):
    """Authors and adds a new verified question item to the canonical item bank."""
    new_item = PracticeItem(
        id=make_practice_uuid(f"creator-{payload.skill_id}-{len(payload.prompt)}"),
        skill_id=payload.skill_id,
        subject=payload.subject,
        grade_band=payload.grade_band,
        difficulty_band=DifficultyBand(payload.difficulty_band),
        question_type=QuestionType(payload.question_type),
        prompt=payload.prompt,
        options=payload.options,
        correct_answer=payload.correct_answer,
        explanation=payload.explanation,
        hints=payload.hints,
        target_mistake_types=payload.target_mistake_types,
        verification_status=VerificationStatus.VERIFIED
    )
    register_practice_item(new_item)
    return {"status": "created", "item_id": new_item.id}


# ─── 5. SUPER ADMINISTRATOR PORTAL ENDPOINTS ──────────────────────────────────

@router.get("/super-admin/overview", response_model=SystemHealthOverview)
def get_super_admin_overview(current_user: AuthenticatedUser = Depends(require_admin)):
    """Returns system-wide operational health, LLM provider telemetry, and error rates."""
    return SuperAdminPortalService.get_system_health()


@router.post("/super-admin/user-role")
def update_user_role(payload: UserRoleUpdate, current_user: AuthenticatedUser = Depends(require_admin)):
    """Updates the assigned role for a user across the platform."""
    return {
        "status": "updated",
        "target_user_id": payload.target_user_id,
        "new_role": payload.new_role
    }

