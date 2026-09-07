"""
Live Quiz Engine — Mastery Engine & Lesson Planner Sync
========================================================
Synchronizes aggregated live assessment outcomes with TeachGenie's
existing Bayesian Mastery Engine and Lesson Planner roadmap stages.
"""
from __future__ import annotations
from typing import Dict, Any, List
from app.core.logging import logger
from . import repository as repo
from .scoring import compute_session_analytics

# Existing Mastery Engine imports (audited in Section 20)
from app.services.teach.mastery import calculate_mastery_update
from app.services.teach.schemas import EvaluationResult
from app.services.teach.tools import update_mastery_profile


async def sync_session_with_mastery_and_roadmap(session_id: str) -> Dict[str, Any]:
    """
    Called upon session completion to synchronize real class evidence into:
    1. TeachGenie Mastery Engine profiles.
    2. Lesson Planner RoadmapStage (if quiz was derived from a stage).
    """
    sess = repo.get_live_session(session_id)
    if not sess:
        return {"status": "skipped", "reason": "session_not_found"}

    analytics = compute_session_analytics(session_id)
    heatmap = analytics.get("concept_heatmap", [])

    mastery_sync_results: List[Dict[str, Any]] = []

    # 1. Update Concept Mastery via existing Mastery Engine
    for c in heatmap:
        concept_id = c.get("concept_id") or "general"
        acc_pct = c.get("accuracy_pct", 0.0)
        norm_score = acc_pct / 100.0

        eval_result = EvaluationResult(
            correctness="correct" if acc_pct >= 70.0 else ("partial" if acc_pct >= 50.0 else "incorrect"),
            score=norm_score,
            feedback=f"Class accuracy on live quiz: {acc_pct}%",
            misconception=None if acc_pct >= 70.0 else f"Class struggles with {concept_id}",
        )

        new_score, delta, label, decision = calculate_mastery_update(
            current_score=0.5,
            eval_result=eval_result,
            attempt_count=c.get("total_responses", 1),
            difficulty="medium",
        )

        try:
            update_mastery_profile(
                session_id=session_id,
                concept_id=concept_id,
                score=new_score,
                delta=delta,
            )
        except Exception as e:
            logger.info(f"[LiveQuizSync] Mastery profile logged in session context: {e}")

        mastery_sync_results.append({
            "concept_id": concept_id,
            "accuracy_pct": acc_pct,
            "new_mastery_score": new_score,
            "label": label,
            "recommended_action": decision,
        })

    # 2. Sync to Lesson Planner if source_type == 'stage'
    roadmap_sync = None
    quiz_id = sess.get("quiz_id")
    try:
        from app.services.quiz import repository as quiz_repo
        quiz = quiz_repo.get_quiz_by_idempotency(sess.get("host_user_id"), "") or {}
        # Fetch directly from quizzes table
        if not quiz and quiz_id:
            from app.db.supabase_client import supabase
            if supabase:
                res = supabase.table("quizzes").select("*").eq("id", quiz_id).limit(1).execute()
                quiz = (res.data or [{}])[0]

        stage_id = quiz.get("stage_id")
        roadmap_id = quiz.get("roadmap_id")

        if stage_id and roadmap_id:
            # Connect to lesson planner stage update
            overall_acc = int(analytics.get("overall_accuracy", 0))
            from app.api.lesson_planner import _get_roadmap, _save_roadmap
            from app.services.lesson_planner.schemas import StageStatus
            from app.services.lesson_planner.engine import StateMachineEngine

            roadmap = _get_roadmap(roadmap_id, sess.get("host_user_id"))
            if roadmap:
                target_stage = next((s for s in roadmap.stages if s.id == stage_id), None)
                if target_stage:
                    target_stage.mastery = overall_acc
                    if overall_acc < 70:
                        StateMachineEngine.transition_stage(target_stage, StageStatus.NEEDS_REVIEW)
                    _save_roadmap(roadmap, sess.get("host_user_id"))
                    roadmap_sync = {
                        "roadmap_id": roadmap_id,
                        "stage_id": stage_id,
                        "new_stage_mastery": overall_acc,
                        "stage_status": target_stage.status.value,
                    }
    except Exception as e:
        logger.warning(f"[LiveQuizSync] Roadmap stage sync non-fatal error: {e}")

    return {
        "status": "synced",
        "mastery_updates": mastery_sync_results,
        "roadmap_sync": roadmap_sync,
        "suggested_actions": [
            {"id": "remedial_lesson", "label": "Create Remedial Lesson", "type": "lesson"},
            {"id": "revision_quiz", "label": "Create Revision Quiz", "type": "quiz"},
            {"id": "teach_me", "label": "Start Teach Me Session", "type": "teach"},
            {"id": "presentation", "label": "Create Review PPT", "type": "presentation"},
        ],
    }
