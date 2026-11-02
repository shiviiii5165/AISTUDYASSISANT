"""
LearnByGenie — Diagnostic Repository
======================================
Durable persistence for diagnostic sessions, responses, and results.
Interfaces with Supabase PostgreSQL (migration 022) with resilient in-memory
caching for deterministic test isolation.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

from app.db.supabase_client import supabase
from app.core.logging import logger
from .schemas import (
    DiagnosticSession, DiagnosticResponse, DiagnosticResult,
    DiagnosticSkillResult, DiagnosticStage, DiagnosticState,
    ConfidenceClass, OverallReadiness, Feature3SkillEvidence
)

class DiagnosticRepository:
    _MEMORY_SESSIONS: Dict[str, DiagnosticSession] = {}
    _MEMORY_RESPONSES: Dict[str, List[DiagnosticResponse]] = {}
    _MEMORY_RESULTS: Dict[str, DiagnosticResult] = {}

    @classmethod
    def clear_memory_cache(cls) -> None:
        cls._MEMORY_SESSIONS.clear()
        cls._MEMORY_RESPONSES.clear()
        cls._MEMORY_RESULTS.clear()

    @classmethod
    def find_active_session(cls, user_id: str, subject: str) -> Optional[DiagnosticSession]:
        for sess in cls._MEMORY_SESSIONS.values():
            if sess.user_id == user_id and sess.subject.lower() == subject.lower() and sess.status == "IN_PROGRESS":
                return sess

        if supabase is not None:
            try:
                res = supabase.table("diagnostic_sessions").select("*").eq("user_id", user_id).eq("subject", subject).eq("status", "IN_PROGRESS").limit(1).execute()
                if res.data and len(res.data) > 0:
                    return cls.get_session(res.data[0]["id"])
            except Exception as e:
                logger.debug(f"[DiagnosticRepo] Supabase find_active_session fallback: {e}")

        return None

    # ─── SESSIONS ─────────────────────────────────────────────────────────────

    @classmethod
    def save_session(cls, session: DiagnosticSession) -> DiagnosticSession:
        cls._MEMORY_SESSIONS[session.id] = session

        if supabase is not None:
            try:
                row = {
                    "id": session.id,
                    "user_id": session.user_id,
                    "subject": session.subject,
                    "curriculum": session.curriculum,
                    "exam_track": session.exam_track,
                    "enrolled_grade": session.enrolled_grade,
                    "starting_level": session.starting_level,
                    "preferred_language": session.preferred_language,
                    "status": session.status,
                    "current_stage": session.current_stage,
                    "current_item_id": session.current_item_id,
                    "question_budget": session.question_budget,
                    "questions_answered": session.questions_answered,
                    "asked_item_ids": session.asked_item_ids,
                    "active_skill_ids": session.active_skill_ids,
                    "engine_version": session.engine_version,
                }
                supabase.table("diagnostic_sessions").upsert(row).execute()
            except Exception as e:
                logger.debug(f"[DiagnosticRepo] Supabase session upsert fallback to memory: {e}")

        return session

    @classmethod
    def get_session(cls, session_id: str) -> Optional[DiagnosticSession]:
        if supabase is not None:
            try:
                res = supabase.table("diagnostic_sessions").select("*").eq("id", session_id).execute()
                if res.data and len(res.data) > 0:
                    r = res.data[0]
                    session = DiagnosticSession(
                        id=r["id"],
                        user_id=r["user_id"],
                        subject=r["subject"],
                        curriculum=r.get("curriculum", "CBSE"),
                        exam_track=r.get("exam_track", "Boards"),
                        enrolled_grade=r.get("enrolled_grade", 10),
                        starting_level=r.get("starting_level", "standard"),
                        preferred_language=r.get("preferred_language", "english"),
                        status=r.get("status", "IN_PROGRESS"),
                        current_stage=r.get("current_stage", "ANCHOR"),
                        current_item_id=r.get("current_item_id"),
                        question_budget=r.get("question_budget", 10),
                        questions_answered=r.get("questions_answered", 0),
                        asked_item_ids=r.get("asked_item_ids") or [],
                        active_skill_ids=r.get("active_skill_ids") or [],
                        engine_version=r.get("engine_version", "2.0.0"),
                    )
                    cls._MEMORY_SESSIONS[session.id] = session
                    return session
            except Exception as e:
                logger.debug(f"[DiagnosticRepo] Supabase get_session fallback: {e}")

        return cls._MEMORY_SESSIONS.get(session_id)

    # ─── RESPONSES ────────────────────────────────────────────────────────────

    @classmethod
    def save_response(cls, response: DiagnosticResponse) -> DiagnosticResponse:
        if not response.id:
            response.id = str(uuid.uuid4())
        if not response.created_at:
            response.created_at = datetime.now(timezone.utc)

        # Idempotency check in memory
        session_resps = cls._MEMORY_RESPONSES.setdefault(response.session_id, [])
        for existing in session_resps:
            if existing.item_id == response.item_id:
                return existing  # Return existing idempotent record!

        session_resps.append(response)

        if supabase is not None:
            try:
                row = {
                    "id": response.id,
                    "session_id": response.session_id,
                    "user_id": response.user_id,
                    "item_id": response.item_id,
                    "skill_id": response.skill_id,
                    "student_response": response.student_response,
                    "is_correct": response.is_correct,
                    "response_time_ms": response.response_time_ms,
                    "attempt_number": response.attempt_number,
                }
                supabase.table("diagnostic_responses").insert(row).execute()
            except Exception as e:
                logger.debug(f"[DiagnosticRepo] Supabase save_response fallback: {e}")

        return response

    @classmethod
    def get_responses_for_session(cls, session_id: str) -> List[DiagnosticResponse]:
        if supabase is not None:
            try:
                res = supabase.table("diagnostic_responses").select("*").eq("session_id", session_id).order("created_at").execute()
                if res.data and len(res.data) > 0:
                    ret = []
                    for r in res.data:
                        ret.append(DiagnosticResponse(
                            id=r["id"],
                            session_id=r["session_id"],
                            user_id=r["user_id"],
                            item_id=r["item_id"],
                            skill_id=r.get("skill_id"),
                            student_response=r.get("student_response"),
                            is_correct=r.get("is_correct", False),
                            response_time_ms=r.get("response_time_ms", 0),
                            attempt_number=r.get("attempt_number", 1),
                        ))
                    cls._MEMORY_RESPONSES[session_id] = ret
                    return ret
            except Exception as e:
                logger.debug(f"[DiagnosticRepo] Supabase get_responses fallback: {e}")

        return list(cls._MEMORY_RESPONSES.get(session_id, []))

    # ─── RESULTS ──────────────────────────────────────────────────────────────

    @classmethod
    def save_result(cls, result: DiagnosticResult) -> DiagnosticResult:
        cls._MEMORY_RESULTS[result.session_id] = result

        if supabase is not None:
            try:
                row = {
                    "id": result.id,
                    "session_id": result.session_id,
                    "user_id": result.user_id,
                    "subject": result.subject,
                    "enrolled_grade": result.enrolled_grade,
                    "exam_track": result.exam_track,
                    "overall_readiness": result.overall_readiness.value,
                    "operating_level_band": result.operating_level_band,
                    "summary": result.summary,
                    "total_items_answered": result.total_items_answered,
                    "correct_items_count": result.correct_items_count,
                    "engine_version": result.engine_version,
                }
                supabase.table("diagnostic_results").upsert(row).execute()

                # Also insert skill results
                for sr in result.skill_results:
                    sr_row = {
                        "id": sr.id or str(uuid.uuid4()),
                        "result_id": result.id,
                        "session_id": result.session_id,
                        "user_id": result.user_id,
                        "subject": result.subject,
                        "skill_id": sr.skill_id,
                        "diagnostic_state": sr.diagnostic_state.value,
                        "evidence_count": sr.evidence_count,
                        "correct_count": sr.correct_count,
                        "confidence_class": sr.confidence_class.value,
                        "recommended_action": sr.recommended_action,
                        "is_recommended_start": sr.is_recommended_start,
                        "prerequisite_depth": sr.prerequisite_depth,
                    }
                    supabase.table("diagnostic_skill_results").upsert(sr_row).execute()
            except Exception as e:
                logger.debug(f"[DiagnosticRepo] Supabase save_result fallback: {e}")

        return result

    @classmethod
    def get_result_by_session_id(cls, session_id: str) -> Optional[DiagnosticResult]:
        if session_id in cls._MEMORY_RESULTS:
            return cls._MEMORY_RESULTS[session_id]

        if supabase is not None:
            try:
                res = supabase.table("diagnostic_results").select("*").eq("session_id", session_id).execute()
                if res.data and len(res.data) > 0:
                    r = res.data[0]
                    # fetch skill results
                    sr_res = supabase.table("diagnostic_skill_results").select("*").eq("session_id", session_id).execute()
                    skill_results = []
                    f3_payload = []
                    prereq_gaps = []
                    for sr_row in (sr_res.data or []):
                        sr = DiagnosticSkillResult(
                            id=sr_row["id"],
                            result_id=sr_row["result_id"],
                            session_id=sr_row["session_id"],
                            user_id=sr_row["user_id"],
                            subject=sr_row["subject"],
                            skill_id=sr_row["skill_id"],
                            skill_code=sr_row["skill_id"],
                            skill_name=sr_row["skill_id"],
                            diagnostic_state=DiagnosticState(sr_row["diagnostic_state"]),
                            evidence_count=sr_row["evidence_count"],
                            correct_count=sr_row["correct_count"],
                            confidence_class=ConfidenceClass(sr_row["confidence_class"]),
                            recommended_action=sr_row.get("recommended_action", ""),
                            is_recommended_start=sr_row.get("is_recommended_start", False),
                            prerequisite_depth=sr_row.get("prerequisite_depth", 0),
                        )
                        skill_results.append(sr)
                        if sr.diagnostic_state == DiagnosticState.NEEDS_REPAIR:
                            prereq_gaps.append(sr.skill_name)
                        f3_payload.append(Feature3SkillEvidence(
                            skill_id=sr.skill_id,
                            diagnostic_state=sr.diagnostic_state.value,
                            evidence_count=sr.evidence_count,
                            correct_count=sr.correct_count,
                            confidence=sr.confidence_class.value,
                            source="DIAGNOSTIC",
                            diagnostic_session_id=session_id,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            recommended_action=sr.recommended_action,
                        ))

                    result = DiagnosticResult(
                        id=r["id"],
                        session_id=r["session_id"],
                        user_id=r["user_id"],
                        subject=r["subject"],
                        enrolled_grade=r.get("enrolled_grade", 10),
                        exam_track=r.get("exam_track", "Boards"),
                        overall_readiness=OverallReadiness(r.get("overall_readiness", "ON_TRACK")),
                        operating_level_band=r.get("operating_level_band", ""),
                        summary=r.get("summary", ""),
                        total_items_answered=r.get("total_items_answered", 0),
                        correct_items_count=r.get("correct_items_count", 0),
                        skill_results=skill_results,
                        prerequisite_gaps=prereq_gaps,
                        feature3_contract_payload=f3_payload,
                        engine_version=r.get("engine_version", "2.0.0"),
                    )
                    cls._MEMORY_RESULTS[session_id] = result
                    return result
            except Exception as e:
                logger.debug(f"[DiagnosticRepo] Supabase get_result fallback: {e}")

        return None

    @classmethod
    def get_user_results(cls, user_id: str) -> List[DiagnosticResult]:
        """Returns student's historical diagnostics in descending order (§17, §18)."""
        ret: List[DiagnosticResult] = []
        for r in cls._MEMORY_RESULTS.values():
            if r.user_id == user_id:
                ret.append(r)

        if supabase is not None:
            try:
                res = supabase.table("diagnostic_results").select("session_id").eq("user_id", user_id).order("created_at", desc=True).execute()
                for row in (res.data or []):
                    sess_id = row["session_id"]
                    if not any(x.session_id == sess_id for x in ret):
                        r = cls.get_result_by_session_id(sess_id)
                        if r:
                            ret.append(r)
            except Exception as e:
                logger.debug(f"[DiagnosticRepo] Supabase get_user_results fallback: {e}")

        return sorted(ret, key=lambda x: str(x.created_at or ""), reverse=True)
