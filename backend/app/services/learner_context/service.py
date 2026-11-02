"""
LearnByGenie — Canonical Learner Context Service
Primary entrypoint for student profile management, context generation,
academic configuration, and downstream AI module context adapters.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.logging import logger
from app.db.supabase_client import supabase
from app.services.learner_context.schemas import (
    LearnerProfileBase,
    LearnerProfileUpdate,
    LearnerProfileResponse,
    LearnerContext,
    EducationContext,
    GoalsContext,
    PreferencesContext,
    LearningActivitySummary,
    AcademicConfigResponse
)
from app.services.learner_context.academic_catalog import (
    get_academic_config_payload,
    get_stage_for_level,
    get_default_subjects_for_level_and_stream,
    EDUCATION_LEVELS,
    EducationStage
)
from app.services.learner_context.validation import (
    validate_education_level,
    validate_academic_stream,
    validate_exam_track,
    validate_target_year,
    validate_subjects,
    validate_language,
    validate_session_minutes,
    validate_weekly_hours
)
from app.services.learner_context.repository import (
    LearnerProfileRepository,
    calculate_profile_completeness
)


def get_default_profile_payload(user_id: str) -> Dict[str, Any]:
    """Generates safe neutral default profile values for new or legacy users."""
    current_year = datetime.now().year
    return {
        "user_id": user_id,
        "education_level": "class_11",
        "grade_or_class": "Class 11",
        "education_stage": "SENIOR_SECONDARY",
        "board_or_curriculum": "CBSE",
        "academic_stream": "science_pcm",
        "target_exam": None,
        "target_year": current_year + 1,
        "subjects": ["Physics", "Chemistry", "Mathematics"],
        "preferred_language": "hinglish",
        "secondary_language": "en",
        "explanation_language_preference": "hinglish",
        "country_or_region": "IN",
        "short_term_goal": None,
        "long_term_goal": None,
        "weekly_study_availability_hours": 10.0,
        "preferred_session_minutes": 30,
        "content_difficulty_preference": "standard",
        "voice_preference": "neutral",
        "accessibility_preferences": {},
        "onboarding_completed": False,
        "profile_version": 1,
    }


class LearnerContextService:
    """
    Canonical backend service providing Learner Profile and Context operations.
    Every intelligent module requests get_learner_context(user_id) from this service.
    """

    @classmethod
    def get_academic_config(cls) -> AcademicConfigResponse:
        """Returns the database-driven academic configuration."""
        payload = get_academic_config_payload()
        return AcademicConfigResponse(**payload)

    @classmethod
    def get_profile(cls, user_id: str) -> LearnerProfileResponse:
        """
        Retrieves canonical learner profile for user_id.
        If profile absent, returns safe neutral defaults with completeness details.
        """
        raw = LearnerProfileRepository.get_by_user_id(user_id)
        if not raw:
            # Safe default fallback for existing users without profiles
            logger.info("Learner profile absent for user %s; generating safe fallback", user_id[:8])
            raw = get_default_profile_payload(user_id)
            raw["onboarding_completed"] = False

        completeness = calculate_profile_completeness(raw)
        return LearnerProfileResponse(
            **raw,
            completeness=completeness
        )

    @classmethod
    def update_profile(cls, user_id: str, updates: LearnerProfileUpdate) -> LearnerProfileResponse:
        """
        Validates and updates mutable learner profile fields.
        Increments profile_version. Historical evidence is strictly preserved.
        """
        # Fetch current record or default
        current = LearnerProfileRepository.get_by_user_id(user_id)
        if not current:
            current = get_default_profile_payload(user_id)

        update_dict = updates.model_dump(exclude_unset=True)
        if not update_dict:
            return cls.get_profile(user_id)

        # 1. Validate Education Level & Stage
        level_id = update_dict.get("education_level", current.get("education_level"))
        canon_level, grade_name, stage = validate_education_level(level_id)
        update_dict["education_level"] = canon_level
        update_dict["grade_or_class"] = grade_name
        update_dict["education_stage"] = stage

        # 2. Validate Academic Stream
        stream = update_dict.get("academic_stream")
        if stream is None:
            if stage in (EducationStage.PRIMARY, EducationStage.MIDDLE, EducationStage.SECONDARY):
                stream = "general"
            else:
                stream = current.get("academic_stream") or "general"
        update_dict["academic_stream"] = validate_academic_stream(canon_level, stage, stream)

        # 3. Validate Target Exam
        exam = update_dict.get("target_exam", current.get("target_exam"))
        if "target_exam" not in update_dict and stage in (EducationStage.PRIMARY, EducationStage.MIDDLE):
            if exam in ("JEE", "NEET"):
                exam = "SCHOOL_EXAMS"
        update_dict["target_exam"] = validate_exam_track(stage, exam)

        # 4. Validate Target Year
        if "target_year" in update_dict:
            update_dict["target_year"] = validate_target_year(update_dict["target_year"])

        # 5. Validate Subjects
        if "subjects" in update_dict:
            update_dict["subjects"] = validate_subjects(update_dict["subjects"])
        elif not current.get("subjects"):
            update_dict["subjects"] = get_default_subjects_for_level_and_stream(canon_level, stream)

        # 6. Validate Language Preferences
        if "preferred_language" in update_dict:
            update_dict["preferred_language"] = validate_language(update_dict["preferred_language"])
        if "explanation_language_preference" in update_dict:
            update_dict["explanation_language_preference"] = validate_language(update_dict["explanation_language_preference"])

        # 7. Validate Study Durations
        if "preferred_session_minutes" in update_dict:
            update_dict["preferred_session_minutes"] = validate_session_minutes(update_dict["preferred_session_minutes"])
        if "weekly_study_availability_hours" in update_dict:
            update_dict["weekly_study_availability_hours"] = validate_weekly_hours(update_dict["weekly_study_availability_hours"])

        # Persist and increment version
        saved = LearnerProfileRepository.create_or_upsert(user_id, update_dict)
        logger.info("Learner profile updated for user %s, new version %s", user_id[:8], saved.get("profile_version"))

        completeness = calculate_profile_completeness(saved)
        return LearnerProfileResponse(
            **saved,
            completeness=completeness
        )

    @classmethod
    def get_learner_context(cls, user_id: str, role: str = "student") -> LearnerContext:
        """
        Builds the canonical LearnerContext for downstream modules (Chat, Teach Me, Notes, Tutor).
        Integrates education state, goals, preferences, completeness, and lightweight activity summary.
        IMPORTANT: Does NOT fabricate mastery scores or rank predictions.
        """
        profile = cls.get_profile(user_id)
        
        # Build education context
        education = EducationContext(
            level=profile.grade_or_class,
            level_id=profile.education_level,
            stage=profile.education_stage,
            board=profile.board_or_curriculum,
            stream=profile.academic_stream,
            exam_tracks=[profile.target_exam] if profile.target_exam else []
        )

        # Build goals context
        goals = GoalsContext(
            primary=profile.target_exam or profile.short_term_goal,
            short_term=profile.short_term_goal,
            long_term=profile.long_term_goal,
            target_year=profile.target_year
        )

        # Build preferences context
        preferences = PreferencesContext(
            preferred_language=profile.preferred_language,
            secondary_language=profile.secondary_language,
            explanation_language=profile.explanation_language_preference,
            content_difficulty=profile.content_difficulty_preference,
            preferred_session_minutes=profile.preferred_session_minutes,
            weekly_study_availability_hours=profile.weekly_study_availability_hours,
            voice_preference=profile.voice_preference
        )

        # Assemble lightweight activity summary from existing tables (without unbounded dump)
        activity_summary = cls._get_activity_summary(user_id)

        # Feature 5: Bounded Mistake DNA Summary (§28)
        mistake_summary_dict = None
        try:
            from app.services.mistake_dna.service import MistakeDNAService
            compact = MistakeDNAService.get_compact_mistake_summary(user_id)
            if compact.total_patterns > 0:
                mistake_summary_dict = compact.model_dump()
        except Exception:
            pass

        # Feature 6: Bounded Adaptive Practice Summary (§42)
        practice_summary_dict = None
        try:
            from app.services.practice.service import AdaptivePracticeService
            compact_prac = AdaptivePracticeService.get_compact_practice_summary(user_id)
            if compact_prac.total_practice_items_answered > 0 or compact_prac.current_active_focus:
                practice_summary_dict = compact_prac.model_dump()
        except Exception:
            pass

        return LearnerContext(
            student_id=user_id,
            role=role,
            profile_version=profile.profile_version,
            education=education,
            goals=goals,
            subjects=profile.subjects,
            preferences=preferences,
            profile_completeness=profile.completeness,
            learning_activity_summary=activity_summary,
            mistake_dna_summary=mistake_summary_dict,
            practice_summary=practice_summary_dict
        )

    @classmethod
    def _get_activity_summary(cls, user_id: str) -> LearningActivitySummary:
        """Lightweight non-blocking retrieval of user's recent activity."""
        recent_subjects: List[str] = []
        doc_count = 0
        quiz_attempts = 0
        last_active = None

        if supabase is not None:
            try:
                # Query PDFs count & recent subjects
                res_pdf = supabase.table("pdfs").select("subject,created_at").eq("user_id", user_id).limit(10).execute()
                if res_pdf and res_pdf.data:
                    doc_count = len(res_pdf.data)
                    subjects = [p.get("subject") for p in res_pdf.data if p.get("subject")]
                    recent_subjects = list(dict.fromkeys(subjects))[:5]
                    if len(res_pdf.data) > 0:
                        last_active = res_pdf.data[0].get("created_at")

                # Query Quiz attempts count
                res_quiz = supabase.table("quiz_scores").select("id").eq("user_id", user_id).limit(20).execute()
                if res_quiz and res_quiz.data:
                    quiz_attempts = len(res_quiz.data)
            except Exception as e:
                logger.debug("Activity summary query notice for user %s: %s", user_id[:8], e)

        return LearningActivitySummary(
            recent_subjects=recent_subjects,
            total_documents=doc_count,
            total_quiz_attempts=quiz_attempts,
            last_active=last_active
        )

    @classmethod
    def format_learner_prompt_context(cls, context: Any) -> str:
        """
        Adapter helper that transforms a LearnerContext into a concise, non-disruptive
        instruction snippet for AI Chat, Teach Me, Tutor, or Notes generation prompts.
        """
        if isinstance(context, dict):
            edu = context.get("education", {})
            goals = context.get("goals", {})
            pref = context.get("preferences", {})
            subjects = context.get("subjects", [])
            level = edu.get("level", "Standard")
            board = edu.get("board", "General")
            stream = edu.get("stream")
            exam = goals.get("primary", "General Studies")
            target_year = goals.get("target_year")
            lang = pref.get("explanation_language", "Hinglish")
            diff = pref.get("content_difficulty", "standard")
        else:
            edu = context.education
            goals = context.goals
            pref = context.preferences
            subjects = context.subjects
            level = edu.level
            board = edu.board
            stream = edu.stream
            exam = goals.primary
            target_year = goals.target_year
            lang = pref.explanation_language
            diff = pref.content_difficulty

        stream_str = f" ({stream})" if stream and stream != "general" else ""
        year_str = f" {target_year}" if target_year else ""
        subj_str = ", ".join(subjects) if subjects else "General"
        mastery_str = ""
        mastery = context.get("mastery") if isinstance(context, dict) else getattr(context, "mastery", None)
        if mastery:
            sec = ", ".join(mastery.get("secure_skills", [])[:3]) or "None"
            dev = ", ".join(mastery.get("developing_skills", [])[:2]) or "None"
            rep = ", ".join(mastery.get("needs_repair_skills", [])[:2]) or "None"
            rec = ", ".join(mastery.get("recommended_starting_skills", [])[:1]) or "None"
            mastery_str = f" Mastery: Secure: {sec}; Developing: {dev}; Needs Repair: {rep}; Recommended Start: {rec}."

        return (
            f"[Learner Context: Student is studying {level} ({board}){stream_str}, "
            f"Target: {exam}{year_str}. Subjects: {subj_str}. "
            f"Explanation Language: {lang}. Content Difficulty: {diff}.{mastery_str}]"
        )

    @classmethod
    def get_compact_mastery_context(cls, user_id: str, subject: str = "Mathematics") -> Optional[Dict[str, Any]]:
        """Returns compact bounded mastery summary from Feature 3 without prompt bloat (§23)."""
        try:
            from app.services.mastery.service import MasteryGraphService
            summary = MasteryGraphService.get_compact_mastery_summary(user_id, subject)
            return summary.model_dump()
        except Exception as e:
            logger.debug(f"[LearnerContext] Mastery summary optional integration: {e}")
            return None
