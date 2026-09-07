"""
Live Quiz Engine — Deterministic Scoring, Analytics & Concept Heatmaps
======================================================================
100% pure-Python. Zero LLM calls.
Grades responses, enforces speed bonus algorithms, aggregates option distributions,
and computes class-wide concept accuracy heatmaps.
"""
from __future__ import annotations
import re
from typing import Dict, Any, List, Optional, Tuple
from . import repository as repo


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def grade_live_response(
    q_dict: Dict[str, Any],
    selected_option_id: Optional[str],
    response_time_ms: int,
    timer_config: Dict[str, Any],
) -> Tuple[bool, int]:
    """
    Grades answer server-side against frozen correct_answer.
    Returns (is_correct, points_awarded).
    """
    if not selected_option_id:
        return False, 0

    ca = q_dict.get("correct_answer")
    ca_list = ca if isinstance(ca, list) else [ca]
    correct_normalized = {_normalize(str(x)) for x in ca_list if str(x).strip()}

    is_correct = _normalize(selected_option_id) in correct_normalized

    if not is_correct:
        return False, 0

    # Base points
    base_points = 1000
    speed_bonus = 0

    if timer_config.get("speed_bonus"):
        timer_sec = timer_config.get("seconds", 30)
        max_ms = timer_sec * 1000
        if response_time_ms < max_ms:
            fraction_remaining = max(0.0, 1.0 - (response_time_ms / max_ms))
            speed_bonus = int(500 * fraction_remaining)

    total_points = base_points + speed_bonus
    return True, total_points


def compute_session_analytics(session_id: str) -> Dict[str, Any]:
    """
    Computes class performance, question breakdown, and concept heatmaps.
    Zero LLM calls.
    """
    sess = repo.get_live_session(session_id)
    if not sess:
        return {}

    snapshot = sess.get("questions_snapshot", [])
    participants = repo.list_participants(session_id)
    responses = repo.get_responses_for_session(session_id)

    total_participants = len(participants)
    total_questions = len(snapshot)

    total_responses_count = len(responses)
    correct_responses_count = sum(1 for r in responses if r.get("is_correct"))

    overall_accuracy = (
        round((correct_responses_count / total_responses_count) * 100, 1)
        if total_responses_count > 0 else 0.0
    )

    possible_responses = max(1, total_participants * total_questions)
    completion_rate = round(min(100.0, (total_responses_count / possible_responses) * 100), 1)

    avg_response_time = (
        round(sum(r.get("response_time_ms", 0) for r in responses) / total_responses_count)
        if total_responses_count > 0 else 0
    )

    # ─── Per-Question Breakdown & Most Missed ────────────────────────────────
    question_stats: List[Dict[str, Any]] = []
    q_map = {q["id"]: q for q in snapshot}

    for q in snapshot:
        qid = q["id"]
        q_resp = [r for r in responses if r.get("question_id") == qid]
        total_q_resp = len(q_resp)
        correct_q_resp = sum(1 for r in q_resp if r.get("is_correct"))

        acc = (
            round((correct_q_resp / total_q_resp) * 100, 1)
            if total_q_resp > 0 else 0.0
        )

        # Distractor analysis
        distractor_counts: Dict[str, int] = {}
        for r in q_resp:
            opt = r.get("selected_option_id")
            if opt and not r.get("is_correct"):
                distractor_counts[opt] = distractor_counts.get(opt, 0) + 1

        top_distractor = (
            max(distractor_counts.items(), key=lambda x: x[1])[0]
            if distractor_counts else None
        )

        question_stats.append({
            "question_id": qid,
            "question_text": q.get("question_text"),
            "concept_id": q.get("concept_id") or "general",
            "total_responses": total_q_resp,
            "correct_count": correct_q_resp,
            "accuracy_pct": acc,
            "top_distractor": top_distractor,
            "distractor_counts": distractor_counts,
        })

    # Sort to find most missed
    most_missed = sorted(
        [q for q in question_stats if q["total_responses"] > 0],
        key=lambda x: x["accuracy_pct"]
    )[:3]

    # ─── Concept Heatmap Calculation ─────────────────────────────────────────
    concept_map: Dict[str, Dict[str, Any]] = {}
    for q in question_stats:
        cid = q["concept_id"]
        if cid not in concept_map:
            concept_map[cid] = {"concept": cid, "correct": 0, "total": 0}
        concept_map[cid]["correct"] += q["correct_count"]
        concept_map[cid]["total"] += q["total_responses"]

    concept_heatmap: List[Dict[str, Any]] = []
    for cid, data in concept_map.items():
        tot = data["total"]
        acc = round((data["correct"] / tot) * 100, 1) if tot > 0 else 0.0

        if acc >= 70.0:
            status = "strong"      # 🟢 Green
            color = "#15803D"
        elif acc >= 50.0:
            status = "developing"  # 🟡 Yellow
            color = "#B45309"
        else:
            status = "weak"        # 🔴 Red
            color = "#DC2626"

        concept_heatmap.append({
            "concept": cid.replace("_", " ").title(),
            "concept_id": cid,
            "accuracy_pct": acc,
            "total_responses": tot,
            "status": status,
            "color": color,
        })

    # Sort heatmap with weakest concepts first
    concept_heatmap.sort(key=lambda x: x["accuracy_pct"])

    return {
        "session_id": session_id,
        "total_participants": total_participants,
        "total_questions": total_questions,
        "total_responses": total_responses_count,
        "overall_accuracy": overall_accuracy,
        "completion_rate": completion_rate,
        "average_response_time_ms": avg_response_time,
        "concept_heatmap": concept_heatmap,
        "most_missed_questions": most_missed,
        "question_stats": question_stats,
    }


def get_live_leaderboard(session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Returns top participants ordered by score descending."""
    parts = repo.list_participants(session_id)
    sorted_parts = sorted(parts, key=lambda p: p.get("score", 0), reverse=True)
    return sorted_parts[:limit]

