"""
LearnByGenie — Diagnostic Service (Feature 2)
==============================================
Orchestration layer connecting LearnerContextService, AdaptiveDecisionEngine,
and DiagnosticRepository.
"""
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timezone
import uuid
from fastapi import HTTPException

from app.core.logging import logger
from app.services.learner_context import LearnerContextService
from .schemas import (
    DiagnosticSession, DiagnosticResponse, DiagnosticResult,
    DiagnosticStepResponse, StudentItemView, DiagnosticStage,
    AnswerSubmissionRequest, DiagnosticStartRequest
)
from .curriculum_blueprint import get_skills_for_subject, get_skill
from .item_bank import get_item, get_items_for_skill
from .adaptive_engine import (
    AdaptiveDecisionEngine, get_default_budget_for_grade
)
from .repository import DiagnosticRepository


def parse_grade_from_level(grade_level: str) -> int:
    """Parses numeric grade from string e.g. 'Class 10' -> 10, 'UG' -> 14."""
    norm = grade_level.lower().replace("class", "").replace("grade", "").strip()
    if norm in ("ug", "undergraduate", "college"):
        return 14
    try:
        return int(norm)
    except ValueError:
        return 10  # default fallback


def evaluate_response_correctness(item_correct_answer: Any, student_response: Any) -> bool:
    """Server-authoritative evaluation of answer correctness (§25)."""
    if student_response is None:
        return False

    # Normalize both
    if isinstance(item_correct_answer, list):
        target_set = {str(x).strip().lower() for x in item_correct_answer}
        if isinstance(student_response, list):
            given_set = {str(x).strip().lower() for x in student_response}
            return target_set == given_set
        return str(student_response).strip().lower() in target_set

    # Single string / numeric comparison
    target_str = str(item_correct_answer).strip().lower()
    given_str = str(student_response).strip().lower()

    if target_str == given_str:
        return True

    # Numeric tolerance check if both can be converted to float
    try:
        f_target = float(target_str)
        f_given = float(given_str)
        return abs(f_target - f_given) < 1e-4
    except ValueError:
        pass

    return False


class DiagnosticService:

    @classmethod
    def start_diagnostic(
        cls,
        user_id: str,
        subject: str,
        retake: bool = False,
    ) -> DiagnosticStepResponse:
        """
        Starts or resumes an adaptive diagnostic session.
        Consumes LearnerContextService for enrolled level and preferences (§19).
        """
        # 1. Consume canonical LearnerContextService (§19)
        context = LearnerContextService.get_learner_context(user_id)
        enrolled_grade = parse_grade_from_level(context.education.level or context.education.level_id)
        curriculum = context.education.board or "CBSE"
        exam_track = (context.education.exam_tracks[0] if context.education.exam_tracks else context.goals.primary) or "Boards"
        language = context.preferences.preferred_language or "english"

        # 2. Check if an active session already exists for this subject (Resume support, §27)
        if not retake:
            existing = cls._find_active_session(user_id, subject)
            if existing:
                return cls.get_session_state(user_id, existing.id)

        # 3. Validate subject availability
        skills = get_skills_for_subject(subject)
        if not skills:
            raise HTTPException(
                status_code=400,
                detail=f"Diagnostic is not currently configured for subject '{subject}'."
            )

        # 4. Initialize session
        budget = get_default_budget_for_grade(enrolled_grade)
        session = DiagnosticSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            subject=subject,
            curriculum=curriculum,
            exam_track=exam_track,
            enrolled_grade=enrolled_grade,
            starting_level="standard",
            preferred_language=language,
            status="IN_PROGRESS",
            current_stage=DiagnosticStage.ANCHOR.value,
            current_item_id=None,
            question_budget=budget,
            questions_answered=0,
            asked_item_ids=[],
            active_skill_ids=[s.id for s in skills[:3]],
            engine_version="2.0.0",
            started_at=datetime.now(timezone.utc),
        )

        # 5. Select initial anchor question
        first_item = AdaptiveDecisionEngine.select_next_item(session, [])
        if not first_item:
            raise HTTPException(
                status_code=500,
                detail=f"No verified diagnostic items available for {subject}."
            )

        session.current_item_id = first_item.id
        session.asked_item_ids.append(first_item.id)
        DiagnosticRepository.save_session(session)

        # 6. Format student payload (DELIBERATELY NO ANSWERS, §25)
        student_view = first_item.to_student_view(
            sequence_number=1,
            total_budget=session.question_budget
        )

        return DiagnosticStepResponse(
            session=session,
            current_question=student_view,
            is_completed=False,
            result=None
        )

    @classmethod
    def submit_answer(
        cls,
        user_id: str,
        session_id: str,
        submission: AnswerSubmissionRequest,
    ) -> DiagnosticStepResponse:
        """
        Grades answer server-side, records telemetry, and branches to next question (§8, §26).
        """
        # 1. Load session and verify ownership (§32)
        session = DiagnosticRepository.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Diagnostic session not found.")
        if session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized access to diagnostic session.")

        # If already completed, return final result
        if session.status == "COMPLETED":
            result = DiagnosticRepository.get_result_by_session_id(session_id)
            return DiagnosticStepResponse(
                session=session,
                current_question=None,
                is_completed=True,
                result=result
            )

        # 2. Idempotency Check (§26)
        existing_responses = DiagnosticRepository.get_responses_for_session(session_id)
        for r in existing_responses:
            if r.item_id == submission.item_id:
                # Already answered this item! Return current session state without duplicate processing
                return cls.get_session_state(user_id, session_id)

        # 3. Load item
        item = get_item(submission.item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Diagnostic item not found.")

        # 4. Server-Authoritative Grading (§25)
        is_correct = evaluate_response_correctness(item.correct_answer, submission.student_response)

        # 5. Save Response
        response = DiagnosticResponse(
            id=str(uuid.uuid4()),
            session_id=session.id,
            user_id=user_id,
            item_id=item.id,
            skill_id=item.skill_id,
            student_response=submission.student_response,
            is_correct=is_correct,
            response_time_ms=submission.response_time_ms,
            attempt_number=1,
            created_at=datetime.now(timezone.utc),
        )
        DiagnosticRepository.save_response(response)
        all_responses = DiagnosticRepository.get_responses_for_session(session_id)

        # 5b. Feature 5: Mistake DNA Engine Integration (§22)
        try:
            from app.services.mistake_dna.service import MistakeDNAService
            from app.services.mistake_dna.schemas import (
                MistakeCandidate, MistakeSourceType, AssistanceLevel as MistakeAssistanceLevel
            )
            if not is_correct:
                cand = MistakeCandidate(
                    user_id=user_id,
                    skill_id=item.skill_id,
                    subject=session.subject,
                    source_type=MistakeSourceType.DIAGNOSTIC,
                    source_record_id=f"{session.id}_{item.id}",
                    question_reference=item.prompt[:120] if item.prompt else "",
                    prompt_text=item.prompt,
                    expected_answer=str(item.correct_answer),
                    student_response=str(submission.student_response),
                    assistance_level=MistakeAssistanceLevel.INDEPENDENT,
                    metadata={"diagnostic_session_id": session.id, "item_id": item.id}
                )
                MistakeDNAService.ingest_error_candidate(cand)
            else:
                MistakeDNAService.mark_repair_evidence(
                    user_id=user_id,
                    skill_id=item.skill_id,
                    evidence_source=MistakeSourceType.DIAGNOSTIC,
                    evidence_record_id=f"{session.id}_{item.id}",
                    assistance_level=MistakeAssistanceLevel.INDEPENDENT,
                    notes="Independent correct answer during diagnostic probe."
                )
        except Exception as e:
            logger.debug(f"[DiagnosticService] Mistake DNA integration note: {e}")

        # 6. Update Session State
        session.questions_answered += 1

        # 7. Adaptive Next-Question Selection
        next_item = AdaptiveDecisionEngine.select_next_item(session, all_responses)

        if next_item is None:
            # ── STOPPING RULE TRIGGERED: Finalize Diagnostic ──
            session.status = "COMPLETED"
            session.current_item_id = None
            session.completed_at = datetime.now(timezone.utc)
            DiagnosticRepository.save_session(session)

            # Compile authoritative final result and Feature 3 ingestion contract
            result = AdaptiveDecisionEngine.compile_final_result(session, all_responses)
            DiagnosticRepository.save_result(result)

            # Ingest into Feature 3 Mastery Graph (§10)
            try:
                from app.services.mastery.service import MasteryGraphService
                MasteryGraphService.ingest_diagnostic_evidence(
                    user_id=user_id,
                    session_id=session.id,
                    contract_payload=result.feature3_contract_payload
                )
            except Exception as e:
                logger.debug(f"[DiagnosticService] Mastery graph ingestion notice: {e}")

            return DiagnosticStepResponse(
                session=session,
                current_question=None,
                is_completed=True,
                result=result
            )
        else:
            # ── ADVANCE TO NEXT QUESTION ──
            session.current_item_id = next_item.id
            session.asked_item_ids.append(next_item.id)
            DiagnosticRepository.save_session(session)

            student_view = next_item.to_student_view(
                sequence_number=session.questions_answered + 1,
                total_budget=session.question_budget
            )
            return DiagnosticStepResponse(
                session=session,
                current_question=student_view,
                is_completed=False,
                result=None
            )

    @classmethod
    def get_session_state(cls, user_id: str, session_id: str) -> DiagnosticStepResponse:
        """Resumes active diagnostic session or returns completed report (§27)."""
        session = DiagnosticRepository.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Diagnostic session not found.")
        if session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized access to diagnostic session.")

        if session.status == "COMPLETED":
            result = DiagnosticRepository.get_result_by_session_id(session_id)
            return DiagnosticStepResponse(
                session=session,
                current_question=None,
                is_completed=True,
                result=result
            )

        # Session in progress: retrieve current question
        current_question = None
        if session.current_item_id:
            it = get_item(session.current_item_id)
            if it:
                current_question = it.to_student_view(
                    sequence_number=session.questions_answered + 1,
                    total_budget=session.question_budget
                )

        return DiagnosticStepResponse(
            session=session,
            current_question=current_question,
            is_completed=False,
            result=None
        )

    @classmethod
    def get_result(cls, user_id: str, session_id: str) -> DiagnosticResult:
        """Retrieves authoritative diagnostic report."""
        session = DiagnosticRepository.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Diagnostic session not found.")
        if session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized access to diagnostic session.")

        result = DiagnosticRepository.get_result_by_session_id(session_id)
        if not result:
            raise HTTPException(status_code=404, detail="Diagnostic result not available yet.")
        return result

    @classmethod
    def get_history(cls, user_id: str) -> List[DiagnosticResult]:
        """Retrieves historical diagnostic assessments (§17, §18)."""
        return DiagnosticRepository.get_user_results(user_id)

    @classmethod
    def _find_active_session(cls, user_id: str, subject: str) -> Optional[DiagnosticSession]:
        """Finds any uncompleted in-progress session for resume."""
        return DiagnosticRepository.find_active_session(user_id, subject)
