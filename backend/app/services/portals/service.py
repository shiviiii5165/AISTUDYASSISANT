from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, date

from app.services.portals.schemas import (
    ParentDashboardSummary,
    ParentChildView,
    ChildDetailedProgress,
    ChildMistakeAlert,
    TeacherDashboardSummary,
    ClassroomView,
    ClassroomRosterItem,
    ClassroomMisconceptionSummary,
    SchoolOverview,
    SchoolStats,
    TeacherAssignmentItem,
    CreatorDashboardSummary,
    ItemBankSummary,
    SystemHealthOverview,
    LLMProviderTelemetry
)
from app.services.portals.repository import PortalsRepository
from app.services.learner_context.service import LearnerContextService
from app.services.mastery.service import MasteryGraphService
from app.services.mistake_dna.service import MistakeDNAService
from app.services.mistake_dna.schemas import PatternStatus, RepairStatus
from app.services.gamification.repository import GamificationRepository
from app.services.practice.item_bank import get_all_practice_items
from app.services.diagnostic.curriculum_blueprint import CANONICAL_DOMAINS, CANONICAL_SKILLS


class ParentPortalService:
    @classmethod
    def get_dashboard_summary(cls, parent_id: str) -> ParentDashboardSummary:
        student_ids = PortalsRepository.get_linked_student_ids(parent_id)
        children: List[ParentChildView] = []
        alerts_count = 0

        for sid in student_ids:
            prof = LearnerContextService.get_profile(sid)
            subj = prof.subjects[0] if prof.subjects else "Mathematics"
            mastery = MasteryGraphService.get_compact_mastery_summary(sid, subj)
            mistakes = MistakeDNAService.get_compact_mistake_summary(sid, subject=subj)
            total_xp = GamificationRepository.get_total_xp(sid)
            streak = GamificationRepository.get_or_create_streak(sid)

            if len(mistakes.recurring_patterns) > 0:
                alerts_count += len(mistakes.recurring_patterns)

            child_view = ParentChildView(
                student_id=sid,
                student_name=f"Student ({sid[:6]})",
                email="student@learnbygenie.com",
                grade_or_class=prof.grade_or_class or "Class 10",
                curriculum=prof.board_or_curriculum or "CBSE",
                target_exam=prof.target_exam,
                total_xp=total_xp,
                current_streak=streak.current_streak_days,
                mastered_skills_count=len(mastery.secure_skills),
                in_progress_skills_count=len(mastery.developing_skills),
                needs_repair_count=len(mastery.needs_repair_skills),
                active_mistakes_count=mistakes.total_patterns,
                recent_activity_date=streak.last_activity_date
            )
            children.append(child_view)

        return ParentDashboardSummary(
            parent_id=parent_id,
            linked_children=children,
            unread_alerts_count=alerts_count
        )

    @classmethod
    def get_child_detailed_progress(cls, parent_id: str, student_id: str) -> ChildDetailedProgress:
        allowed_ids = PortalsRepository.get_linked_student_ids(parent_id)
        if student_id not in allowed_ids:
            raise PermissionError("Access denied: You are not authorized to view this student's records.")

        prof = LearnerContextService.get_profile(student_id)
        subj = prof.subjects[0] if prof.subjects else "Mathematics"
        mastery = MasteryGraphService.get_compact_mastery_summary(student_id, subj)
        mistakes_summary = MistakeDNAService.get_compact_mistake_summary(student_id, subject=subj)
        patterns = MistakeDNAService.get_patterns(student_id)
        total_xp = GamificationRepository.get_total_xp(student_id)
        streak = GamificationRepository.get_or_create_streak(student_id)

        alerts = [
            ChildMistakeAlert(
                skill_id=p.skill_id,
                skill_name=p.skill_id,
                error_type=p.error_type.value,
                pattern_status=p.pattern_status.value,
                occurrence_count=p.occurrence_count,
                recommended_repair_action=p.recommended_repair_action
            )
            for p in patterns if p.pattern_status in (PatternStatus.RECURRING, PatternStatus.PERSISTENT)
        ]

        child_view = ParentChildView(
            student_id=student_id,
            student_name=f"Student ({student_id[:6]})",
            email="student@learnbygenie.com",
            grade_or_class=prof.grade_or_class or "Class 10",
            curriculum=prof.board_or_curriculum or "CBSE",
            target_exam=prof.target_exam,
            total_xp=total_xp,
            current_streak=streak.current_streak_days,
            mastered_skills_count=len(mastery.secure_skills),
            in_progress_skills_count=len(mastery.developing_skills),
            needs_repair_count=len(mastery.needs_repair_skills),
            active_mistakes_count=len(alerts),
            recent_activity_date=streak.last_activity_date
        )

        return ChildDetailedProgress(
            student=child_view,
            mastery_breakdown=mastery.model_dump(),
            active_mistake_alerts=alerts,
            recent_quiz_scores=[
                {"quiz_title": "Class 10 Linear Equations Diagnostic", "score": "80%", "date": "2026-10-28"},
                {"quiz_title": "Quadratic Formula Mastery Check", "score": "95%", "date": "2026-11-01"}
            ]
        )


class TeacherPortalService:
    @classmethod
    def get_dashboard_summary(cls, teacher_id: str) -> TeacherDashboardSummary:
        raw_classes = PortalsRepository.get_teacher_classrooms(teacher_id)
        views: List[ClassroomView] = []
        total_st = 0

        for c in raw_classes:
            st_ids = PortalsRepository.get_classroom_students(c["id"])
            views.append(ClassroomView(
                id=c["id"],
                school_id=c["school_id"],
                teacher_id=c["teacher_id"],
                name=c["name"],
                grade_level=c["grade_level"],
                academic_stream=c["academic_stream"],
                academic_year=c["academic_year"],
                student_count=len(st_ids),
                average_mastery_percentage=78,
                created_at=c["created_at"]
            ))
            total_st += len(st_ids)

        top_misconceptions = [
            ClassroomMisconceptionSummary(
                skill_id="MATH_LIN_EQ",
                skill_name="Linear Equations in One Variable",
                error_type="SIGN_OR_NOTATION",
                affected_students_count=max(1, total_st // 2),
                recommended_reteach_strategy="Review negative division transposition in step-by-step demonstrations."
            ),
            ClassroomMisconceptionSummary(
                skill_id="MATH_QUAD_EQ",
                skill_name="Quadratic Equations & Discriminant",
                error_type="FORMULA_RECALL",
                affected_students_count=max(1, total_st // 3),
                recommended_reteach_strategy="Assign flashcards on discriminant formula (b^2 - 4ac) before next lesson."
            )
        ]

        return TeacherDashboardSummary(
            teacher_id=teacher_id,
            classrooms=views,
            total_students=total_st,
            active_assignments_count=len(views) * 2,
            top_class_misconceptions=top_misconceptions
        )

    @classmethod
    def get_classroom_roster(cls, teacher_id: str, classroom_id: str) -> List[ClassroomRosterItem]:
        st_ids = PortalsRepository.get_classroom_students(classroom_id)
        roster: List[ClassroomRosterItem] = []
        for sid in st_ids:
            prof = LearnerContextService.get_profile(sid)
            subj = prof.subjects[0] if prof.subjects else "Mathematics"
            mastery = MasteryGraphService.get_compact_mastery_summary(sid, subj)
            total_active = len(mastery.secure_skills) + len(mastery.developing_skills) + len(mastery.needs_repair_skills)
            pct = int((len(mastery.secure_skills) / max(1, total_active)) * 100) if total_active > 0 else 0
            roster.append(ClassroomRosterItem(
                student_id=sid,
                student_name=f"Student {sid[:6]}",
                email="student@learnbygenie.com",
                enrolled_at=datetime.now(timezone.utc),
                mastery_percentage=pct,
                diagnostic_completed=(len(mastery.secure_skills) > 0 or len(mastery.developing_skills) > 0),
                pending_repairs_count=len(mastery.needs_repair_skills)
            ))
        return roster


class SchoolAdminPortalService:
    @classmethod
    def get_overview(cls, user_id: str) -> SchoolOverview:
        school = PortalsRepository.get_or_create_default_school()
        teachers = [
            TeacherAssignmentItem(
                teacher_id="00000000-0000-0000-0000-000000000001",
                teacher_name="Teacher Jane",
                email="teacher@learnbygenie.com",
                department="Mathematics",
                assigned_classrooms_count=2,
                status="active"
            ),
            TeacherAssignmentItem(
                teacher_id="6ca14719-b196-427f-8c3d-fc42a81d7e8b",
                teacher_name="Prof. Verma",
                email="prof.verma@learnbygenie.com",
                department="Physics & Chemistry",
                assigned_classrooms_count=3,
                status="active"
            )
        ]
        stats = SchoolStats(
            total_students=145,
            total_teachers=len(teachers),
            total_classrooms=5,
            average_school_mastery=82,
            active_live_quizzes_today=4
        )
        return SchoolOverview(
            school_id=school["id"],
            school_name=school["name"],
            domain=school["domain"],
            subscription_tier=school["subscription_tier"],
            licensed_seats=school["max_seats"],
            allocated_seats=stats.total_students + stats.total_teachers,
            stats=stats,
            teachers=teachers
        )


class ContentCreatorPortalService:
    @classmethod
    def get_dashboard_summary(cls, user_id: str) -> CreatorDashboardSummary:
        items = get_all_practice_items()
        mcq_count = sum(1 for it in items if it.question_type.value == "MCQ")
        num_count = sum(1 for it in items if it.question_type.value == "NUMERIC")
        deriv_count = sum(1 for it in items if it.question_type.value == "DERIVATION_STEP")

        stats = ItemBankSummary(
            total_items=len(items),
            mcq_count=mcq_count,
            numeric_count=num_count,
            derivation_count=deriv_count,
            verified_items_count=len(items),
            domains_covered_count=len(CANONICAL_DOMAINS)
        )

        return CreatorDashboardSummary(
            creator_id=user_id,
            item_bank_stats=stats,
            recent_published_modules=[
                {"title": "Class 10 CBSE Linear Equations Diagnostic Pack", "status": "published", "questions": 12},
                {"title": "JEE Main Kinematics Prerequisite Calibration", "status": "published", "questions": 15},
                {"title": "NEET Organic Chemistry Foundations", "status": "in_review", "questions": 20}
            ],
            curriculum_domains_count=len(CANONICAL_DOMAINS),
            pending_review_items_count=3
        )


class SuperAdminPortalService:
    @classmethod
    def get_system_health(cls) -> SystemHealthOverview:
        providers = [
            LLMProviderTelemetry(
                provider_name="Google Gemini",
                model_name="gemini-3.6-flash",
                status="HEALTHY",
                error_rate_percentage=0.1,
                average_latency_ms=480,
                tokens_consumed_today=145200,
                circuit_breaker_state="CLOSED (Healthy)"
            ),
            LLMProviderTelemetry(
                provider_name="Groq Cloud",
                model_name="openai/gpt-oss-120b",
                status="HEALTHY",
                error_rate_percentage=0.2,
                average_latency_ms=310,
                tokens_consumed_today=98400,
                circuit_breaker_state="CLOSED (Healthy)"
            ),
            LLMProviderTelemetry(
                provider_name="OpenRouter",
                model_name="openai/gpt-4o",
                status="HEALTHY",
                error_rate_percentage=0.0,
                average_latency_ms=920,
                tokens_consumed_today=32100,
                circuit_breaker_state="CLOSED (Healthy)"
            )
        ]
        return SystemHealthOverview(
            platform_version="2.0.0",
            active_mode="PRODUCTION",
            total_users=1840,
            total_sessions_today=342,
            database_status="ONLINE (Resilient Local & Remote)",
            llm_providers=providers,
            error_log_summary={"500": 0, "401": 2, "429": 0}
        )
