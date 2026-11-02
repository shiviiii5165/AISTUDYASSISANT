from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any

from app.core.dependencies import (
    get_current_user,
    AuthenticatedUser,
    require_parent,
    require_teacher,
    require_school_admin,
    require_content_creator,
    require_admin,
    require_role
)
from app.core.user_roles import UserRoleRepository
from app.services.portals.service import (
    ParentPortalService,
    TeacherPortalService,
    SchoolAdminPortalService,
    ContentCreatorPortalService,
    SuperAdminPortalService,
    StudentPortalService
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
    UserRoleUpdate,
    DailyPersonalizedRoadmap,
    UserRolesView
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
    """Links a child account using an authentic verified invitation code."""
    try:
        link = PortalsRepository.link_parent_with_code(
            parent_id=current_user.id,
            invite_code=payload.invitation_code,
            relationship=payload.relationship
        )
        return {"status": "linked", "link": link}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/student/generate-parent-code")
def generate_parent_code(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Generates a cryptographically secure, high-entropy invitation code with expiration for linking."""
    code = PortalsRepository.generate_student_invite_code(current_user.id)
    return {"invitation_code": code, "student_id": current_user.id}


@router.post("/student/revoke-parent-code")
def revoke_parent_code(payload: Dict[str, str], current_user: AuthenticatedUser = Depends(get_current_user)):
    """Allows a student to revoke an unredeemed pending invitation code."""
    invite_code = payload.get("invitation_code", "")
    try:
        success = PortalsRepository.revoke_student_invite_code(current_user.id, invite_code)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation code not found or not owned by student.")
        return {"status": "revoked", "invitation_code": invite_code}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
    """
    Authors a new practice question item.
    Enforces that all newly authored questions enter PENDING_REVIEW status
    and cannot be served to learners until authorized reviewer approval.
    """
    new_item = PracticeItem(
        id=make_practice_uuid(f"creator-{payload.skill_id}-{len(payload.prompt)}"),
        skill_id=payload.skill_id,
        subject=payload.subject,
        grade_band=payload.grade_band,
        difficulty_band=DifficultyBand.from_str(payload.difficulty_band) if hasattr(DifficultyBand, "from_str") else DifficultyBand(payload.difficulty_band),
        question_type=QuestionType.MCQ if payload.question_type.lower() in ("mcq", "multiple_choice") else QuestionType(payload.question_type.lower()),
        prompt=payload.prompt,
        options=payload.options,
        correct_answer=payload.correct_answer,
        explanation=payload.explanation,
        hints=payload.hints,
        target_mistake_types=payload.target_mistake_types,
        verification_status=VerificationStatus.PENDING_REVIEW
    )
    saved = PortalsRepository.save_creator_item(new_item, author_id=current_user.id)
    return {
        "status": "pending_review",
        "item_id": new_item.id,
        "review_status": "pending_review"
    }


require_reviewer = require_role(["teacher", "school_admin", "admin", "super_admin"])


@router.get("/creator/items/pending")
def list_pending_items(current_user: AuthenticatedUser = Depends(require_reviewer)):
    """Returns questions awaiting authorized review."""
    return PortalsRepository.get_pending_creator_items()


@router.post("/creator/items/{item_id}/approve")
def approve_item_endpoint(item_id: str, current_user: AuthenticatedUser = Depends(require_reviewer)):
    """Approves a pending item, publishing it to the active verified practice item bank."""
    approved = PortalsRepository.approve_creator_item(item_id, reviewer_id=current_user.id)
    if not approved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found or already processed.")
    return {"status": "approved", "item_id": item_id, "reviewer_id": current_user.id}


@router.post("/creator/items/{item_id}/reject")
def reject_item_endpoint(item_id: str, payload: Dict[str, str] = {}, current_user: AuthenticatedUser = Depends(require_reviewer)):
    """Rejects a question item with feedback notes."""
    notes = payload.get("notes", "") if payload else ""
    rejected = PortalsRepository.reject_creator_item(item_id, reviewer_id=current_user.id, notes=notes)
    if not rejected:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found or already processed.")
    return {"status": "rejected", "item_id": item_id, "notes": notes, "reviewer_id": current_user.id}


# ─── 5. SUPER ADMINISTRATOR PORTAL ENDPOINTS ──────────────────────────────────

@router.get("/super-admin/overview", response_model=SystemHealthOverview)
def get_super_admin_overview(current_user: AuthenticatedUser = Depends(require_admin)):
    """Returns system-wide operational health, LLM provider telemetry, and error rates."""
    return SuperAdminPortalService.get_system_health()


@router.post("/super-admin/user-role")
def update_user_role(payload: UserRoleUpdate, current_user: AuthenticatedUser = Depends(require_admin)):
    """
    Authoritatively updates user role in PostgreSQL with audit log.
    Takes effect immediately in subsequent authenticated requests.
    """
    try:
        res = UserRoleRepository.set_user_role(
            target_user_id=payload.target_user_id,
            new_role=payload.new_role,
            assigned_by=current_user.id,
            reason="Administrative role assignment"
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ─── 6. STUDENT PORTAL ROADMAP ENDPOINTS (STAGE 8) ────────────────────────────

@router.get("/student/roadmap", response_model=DailyPersonalizedRoadmap)
def get_student_daily_roadmap(current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Returns the single daily personalized roadmap with 3 choice tasks adhering
    to 30% Spaced Repair / 50% Core Progression / 20% Interleaved Transfer (§8).
    """
    return StudentPortalService.get_daily_roadmap(current_user.id)


# ─── 7. CURRENT USER ROLES & PORTAL ACCESS ENDPOINT ──────────────────────────

@router.get("/me/roles", response_model=UserRolesView)
def get_current_user_roles(current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Returns server-verified roles and authorized portal access for the current user.
    Prevents unauthorized portal switching via client-side manipulation.
    """
    role = UserRoleRepository.get_user_role(current_user.id) or current_user.role or "student"
    if role in ("super_admin", "admin"):
        authorized = ["student", "parent", "teacher", "school_admin", "content_creator", role]
    elif role == "school_admin":
        authorized = ["school_admin", "teacher", "student"]
    elif role == "teacher":
        authorized = ["teacher", "student"]
    elif role == "content_creator":
        authorized = ["content_creator", "student"]
    elif role == "parent":
        authorized = ["parent", "student"]
    else:
        authorized = ["student"]

    return UserRolesView(
        user_id=current_user.id,
        primary_role=role,
        authorized_roles=authorized,
        active_role=role
    )

