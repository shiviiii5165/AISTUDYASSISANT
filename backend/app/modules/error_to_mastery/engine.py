"""The closed loop: diagnostic CAT and step-level practice submission (Stages 1-8)."""
from __future__ import annotations

import math
import re
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

from app.modules import store, xp
from app.modules.curriculum.items import Item, all_items, get_item, items_for
from app.modules.curriculum.ncert_seed import (
    CONCEPTS_BY_ID, PREREQUISITES, Concept, concepts_for_class,
)
from app.modules.error_to_mastery.classifier import classify_error
from app.modules.learning_core import bkt, gaps, irt, math_verifier, retention, selection, tiers
from app.modules.learning_core.math_verifier import Verdict
from app.modules.learning_core.tiers import Evidence, MasteryState

WEAK_P = 0.6
FADE_STAGES = ("full", "late_step", "mid_step", "solo")


class NotFound(Exception):
    """Unknown resource, or one owned by someone else; both look identical to clients."""


class Conflict(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- grading

def _numeric_part(text: str) -> str:
    tail = text.split("=")[-1].strip()
    match = re.match(r"^[-+]?\s*[\d./\s()+\-*]*\d[\d./()\s]*", tail)
    return match.group(0).strip() if match else tail


def grade(item: Item, response: str) -> bool:
    candidate = _numeric_part(response)
    return bool(candidate) and math_verifier.verify_equal(candidate, item.answer) is Verdict.VERIFIED


# ---------------------------------------------------------------- learner state

def load_state(student_id: str, concept_id: str) -> dict[str, Any]:
    return store.get_one("learner_bkt_state", student_id=student_id, skill_id=concept_id) or {
        "student_id": student_id, "skill_id": concept_id, "p_l": bkt.BKTParams().p_l0,
        "p_s": 0.1, "p_g": 0.2, "tier": 0, "unhinted_streak": 0,
        "retention_clock_start": None, "day7_passed": False, "updated_at": None,
    }


def _mastery(state: dict[str, Any]) -> MasteryState:
    return MasteryState(
        tier=state["tier"],
        unhinted_streak=state["unhinted_streak"],
        retention_clock_start=store.parse_time(state["retention_clock_start"]),
        day7_passed=state["day7_passed"],
    )


def _is_weak(student_id: str, concept_id: str) -> bool:
    state = load_state(student_id, concept_id)
    return state["tier"] < 3 and state["p_l"] < WEAK_P


def is_unlocked(student_id: str, concept: Concept) -> bool:
    """Tier 3 on every prerequisite unlocks a concept, unless the diagnostic cleared it."""
    return all(load_state(student_id, p)["tier"] >= 3 or not _is_weak(student_id, p)
               for p in concept.prerequisites)


def latest_theta(student_id: str, subject: str) -> Optional[float]:
    sessions = [s for s in store.select("cat_sessions", student_id=student_id, subject=subject)
                if s.get("completed_at")]
    return max(sessions, key=lambda s: s["completed_at"])["theta"] if sessions else None


def _concept_theta(student_id: str, concept: Concept, p_l: float) -> float:
    """Combine CAT ability with concept evidence: BKT log-odds shift it per concept."""
    base = latest_theta(student_id, concept.subject) or 0.0
    bounded = min(0.99, max(0.01, p_l))
    return base + 0.5 * (math.log(bounded / (1 - bounded)) + 1.386)  # 1.386 cancels P(L0)=0.2.


# ---------------------------------------------------------------- Stage 1: CAT

def start_diagnostic(student_id: str, subject: str, class_level: int) -> dict[str, Any]:
    allowed = {c.concept_id for c in concepts_for_class(class_level, subject)}
    if not allowed:
        raise NotFound("No diagnostic content for this class and subject")
    estimate = irt.estimate_ability([])
    first = _cat_next(estimate.theta, allowed, [])
    session = store.insert("cat_sessions", {
        "student_id": student_id, "subject": subject, "class_level": class_level,
        "theta": estimate.theta, "se": estimate.se, "items_answered": 0, "responses": [],
        "current_item_id": first.item_id, "stop_reason": None,
        "started_at": _now().isoformat(), "completed_at": None,
    })
    return {"session_id": session["id"], "theta": estimate.theta, "se": estimate.se,
            "item": first.public_view(), "complete": False}


def _cat_next(theta: float, allowed: set[str], seen: Sequence[str]) -> Item:
    bank = [i for i in all_items() if i.concept_id in allowed]
    chosen = irt.select_next_item(theta, [i.irt for i in bank], seen)
    return get_item(chosen.item_id) if chosen else None  # type: ignore[return-value]


def answer_diagnostic(student_id: str, session_id: str, item_id: str, response: str) -> dict[str, Any]:
    session = store.get_one("cat_sessions", id=session_id, student_id=student_id)
    if session is None:
        raise NotFound(session_id)
    if session["completed_at"]:
        raise Conflict("Diagnostic already completed")
    if item_id != session["current_item_id"]:
        raise Conflict("That is not the current question")

    item = get_item(item_id)
    responses = session["responses"] + [{"item_id": item_id, "correct": grade(item, response)}]
    estimate = irt.estimate_ability(
        [irt.Response(get_item(r["item_id"]).irt, r["correct"]) for r in responses])
    reason = irt.stop_reason(len(responses), estimate.se)
    allowed = {c.concept_id for c in concepts_for_class(session["class_level"], session["subject"])}
    next_item = None
    if not reason:
        next_item = _cat_next(estimate.theta, allowed, [r["item_id"] for r in responses])
        if next_item is None:
            reason = "bank_exhausted"

    patch: dict[str, Any] = {
        "theta": estimate.theta, "se": estimate.se, "items_answered": len(responses),
        "responses": responses, "current_item_id": next_item.item_id if next_item else None,
    }
    result: dict[str, Any] = {"theta": estimate.theta, "se": estimate.se, "complete": bool(reason)}
    if reason:
        patch.update(stop_reason=reason, completed_at=_now().isoformat())
        result.update(stop_reason=reason, report=_finish_diagnostic(student_id, session, responses))
    else:
        result["item"] = next_item.public_view()
    store.update("cat_sessions", {"id": session_id}, patch)
    return result


def _finish_diagnostic(student_id: str, session: dict, responses: list[dict]) -> dict[str, Any]:
    tally: dict[str, list[bool]] = {}
    for response in responses:
        tally.setdefault(get_item(response["item_id"]).concept_id, []).append(response["correct"])
    report = []
    params = bkt.BKTParams()
    for concept_id, outcomes in tally.items():
        state = load_state(student_id, concept_id)
        p_l = state["p_l"]
        for correct in outcomes:
            p_l = bkt.update(p_l, correct, params)
        state["p_l"] = p_l
        state["updated_at"] = _now().isoformat()
        store.upsert("learner_bkt_state", state, ("student_id", "skill_id"))
        report.append({"concept_id": concept_id, "p_mastery": round(p_l, 3),
                       "correct": sum(outcomes), "asked": len(outcomes),
                       "weak": p_l < WEAK_P})
    xp.award("RULE_XP_01", student_id, f"diagnostic:{session['subject']}")
    return {"concepts": report}


# ---------------------------------------------------------------- practice

def start_practice(student_id: str, concept_id: str, class_level: int, kind: str = "practice") -> dict[str, Any]:
    concept = CONCEPTS_BY_ID.get(concept_id)
    if concept is None or concept.class_level > class_level:
        raise NotFound(concept_id)
    state = load_state(student_id, concept_id)
    if kind == "transfer" and state["tier"] != 3:
        raise Conflict("Transfer checks unlock at Tier 3")
    if kind == "retention" and state["tier"] < 4:
        raise Conflict("Retention checks unlock at Tier 4")
    session = store.insert("practice_sessions_v1", {
        "student_id": student_id, "concept_id": concept_id, "kind": kind, "sequence_index": 0,
        "consecutive_failures": 0, "current_item_id": None, "helped": False, "fade_stage": 0,
        "started_at": _now().isoformat(),
    })
    prescription = prescribe(student_id, concept) if not is_unlocked(student_id, concept) or state["tier"] <= 1 else None
    decision = _next_step(student_id, session, concept, state)
    return {"session_id": session["id"], "tier": state["tier"], "next": decision,
            "prescription": prescription}


def prescribe(student_id: str, concept: Concept, stage: int = 0) -> dict[str, Any]:
    """Stage 4: root-gap repair first, then the concept's faded worked example."""
    path = gaps.remediation_path(concept.concept_id, PREREQUISITES,
                                 lambda c: _is_weak(student_id, c))
    target = CONCEPTS_BY_ID[path[0]] if path else concept
    return {"concept_id": target.concept_id, "remediation_path": path,
            "worked_example": faded_example(target, stage),
            "simulation": target.simulation, "estimated_minutes": 3}


def faded_example(concept: Concept, stage: int) -> dict[str, Any]:
    """Full, then last step blank, then middle onward blank, then solo."""
    stage = max(0, min(stage, len(FADE_STAGES) - 1))
    steps = list(concept.worked_steps)
    if stage == 0:
        visible = len(steps)
    elif stage == 1:
        visible = len(steps) - 1
    elif stage == 2:
        visible = max(1, len(steps) // 2)
    else:
        visible = 0
    return {
        "stage": FADE_STAGES[stage],
        "problem": concept.worked_problem,
        "shown_steps": [
            {"equation": steps[i], "note": concept.worked_notes[i]} for i in range(visible)
        ],
        "blank_steps": len(steps) - visible,
        "citation_id": concept.citation_id,
    }


def _attempted_ids(student_id: str, concept_id: str) -> set[str]:
    rows = store.select("practice_attempts_v1", student_id=student_id, concept_id=concept_id)
    return {row["item_id"] for row in rows}


def _next_step(student_id: str, session: dict, concept: Concept, state: dict) -> dict[str, Any]:
    theta = _concept_theta(student_id, concept, state["p_l"])
    siblings = [i.irt for s in concept.siblings for i in items_for(s)]
    decision = selection.select_practice(
        theta=theta, tier=state["tier"], sequence_index=session["sequence_index"],
        consecutive_failures=session["consecutive_failures"],
        current_items=[i.irt for i in items_for(concept.concept_id)],
        sibling_items=siblings if session["kind"] == "practice" else (),
        seen_item_ids=_attempted_ids(student_id, concept.concept_id),
    )
    if decision.action == "simulation":
        store.update("practice_sessions_v1", {"id": session["id"]},
                     {"current_item_id": None, "consecutive_failures": 0})
        return {"action": "simulation", "activity": concept.simulation,
                "reason": "Let's see this one visually before trying again."}
    if decision.action == "exhausted":
        store.update("practice_sessions_v1", {"id": session["id"]}, {"current_item_id": None})
        return {"action": "exhausted"}
    store.update("practice_sessions_v1", {"id": session["id"]}, {"current_item_id": decision.item.item_id})
    item = get_item(decision.item.item_id)
    return {"action": "item", "item": item.public_view(), "source": decision.source,
            "in_zpd": decision.in_zpd}


def complete_intervention(student_id: str, session_id: str) -> dict[str, Any]:
    """The student finished a worked example or simulation: Tier 1 and raised P(T)."""
    session = store.get_one("practice_sessions_v1", id=session_id, student_id=student_id)
    if session is None:
        raise NotFound(session_id)
    state = load_state(student_id, session["concept_id"])
    mastery = tiers.advance(_mastery(state), Evidence.INTERVENTION_COMPLETED, _now())
    state["tier"] = mastery.tier
    state["updated_at"] = _now().isoformat()
    store.upsert("learner_bkt_state", state, ("student_id", "skill_id"))
    stage = min(session["fade_stage"] + 1, len(FADE_STAGES) - 1)
    store.update("practice_sessions_v1", {"id": session_id}, {"helped": True, "fade_stage": stage})
    concept = CONCEPTS_BY_ID[session["concept_id"]]
    session = {**session, "helped": True, "fade_stage": stage}
    return {"tier": state["tier"], "next_example": faded_example(concept, stage),
            "next": _next_step(student_id, session, concept, state)}


def _attribution(steps: Sequence[str], bad_step: Optional[int], correct: bool) -> Optional[dict]:
    """Say what went right before naming the step to fix."""
    if correct or not steps:
        return None
    if bad_step is None:
        result = math_verifier.verify_derivation(steps)
        bad_step = result.first_bad_step
    if bad_step is None:
        return {"succeeded": f"Your working through step {len(steps)} is consistent.",
                "fix": "Check how you read your final answer from the last line."}
    return {"succeeded": f"Your work up to step {bad_step} was spot-on.",
            "fix": f"Let's look again at step {bad_step + 1}: {steps[bad_step]}",
            "bad_step": bad_step}


def _resolve_active_tokens(student_id: str, concept_id: str, item_unseen: bool) -> int:
    count = 0
    for token in store.select("error_tokens", student_id=student_id, concept_id=concept_id, status="active"):
        store.update("error_tokens", {"id": token["id"]},
                     {"status": "resolved", "resolved_at": _now().isoformat()})
        xp.award("RULE_XP_02", student_id, f"token:{token['id']}", item_unseen=item_unseen)
        count += 1
    return count


def submit(
    student_id: str, session_id: str, item_id: str, response: str, idempotency_key: str,
    steps: Sequence[str] = (), confidence: Optional[str] = None, hints_used: int = 0,
) -> dict[str, Any]:
    session = store.get_one("practice_sessions_v1", id=session_id, student_id=student_id)
    if session is None:
        raise NotFound(session_id)
    replay = store.get_one("practice_attempts_v1", student_id=student_id, idempotency_key=idempotency_key)
    if replay is not None:
        return {**replay["result"], "replayed": True}
    if item_id != session["current_item_id"]:
        raise Conflict("That is not the current question")

    item = get_item(item_id)
    item_concept = CONCEPTS_BY_ID[item.concept_id]
    now = _now()
    seen_before = item_id in _attempted_ids(student_id, item.concept_id)
    correct = grade(item, response)
    hinted = hints_used > 0
    state = load_state(student_id, item.concept_id)
    tier_before = state["tier"]

    # Stage 6: decay since last evidence, then Bayes update conditioned on intervention.
    review_row = store.get_one("review_schedule", student_id=student_id, skill_id=item.concept_id)
    p_l = state["p_l"]
    last = store.parse_time(state["updated_at"])
    if last is not None and review_row is not None:
        p_l = bkt.decay(p_l, (now - last).total_seconds() / 86400, review_row["stability_days"])
    intervention = bkt.Intervention.WORKED_EXAMPLE if session["helped"] else bkt.Intervention.NO_HELP
    params = bkt.BKTParams(p_s=state["p_s"], p_g=state["p_g"])
    state["p_l"] = bkt.update(p_l, correct, params, intervention)

    evidence = {
        "practice": Evidence.PRACTICE_PASS if correct else Evidence.PRACTICE_FAIL,
        "transfer": Evidence.TRANSFER_PASS if correct else Evidence.PRACTICE_FAIL,
        "retention": Evidence.RETENTION_PASS if correct else Evidence.RETENTION_FAIL,
    }[session["kind"]]
    mastery = tiers.advance(_mastery(state), evidence, now, hinted=hinted,
                            item_previously_seen=seen_before)
    state.update(
        tier=mastery.tier, unhinted_streak=mastery.unhinted_streak,
        retention_clock_start=mastery.retention_clock_start.isoformat() if mastery.retention_clock_start else None,
        day7_passed=mastery.day7_passed, updated_at=now.isoformat(),
    )
    store.upsert("learner_bkt_state", state, ("student_id", "skill_id"))

    # Stage 2-3: classify the error and map the gap.
    token_result = None
    remediation: list[str] = []
    entrenched = False
    if not correct:
        weak = [p for p in item_concept.prerequisites if _is_weak(student_id, p)]
        token_result = classify_error(
            prompt=item.prompt, expected=f"{item.answer} {item.unit}".strip(), response=response,
            subject=item_concept.subject, concept_id=item.concept_id, student_id=student_id,
            item_id=item_id, traps=item.traps, steps=steps, confidence=confidence,
            weak_prerequisites=weak,
        )
        entrenched = confidence == "Sure"
        store.insert("error_tokens", {
            "student_id": student_id, "concept_id": item.concept_id, "item_id": item_id,
            "token": token_result.token, "tier": token_result.tier, "rule": token_result.rule,
            "deterministic": token_result.deterministic, "entrenched": entrenched,
            "status": "active", "created_at": now.isoformat(), "resolved_at": None,
        })
        if token_result.token == "E02":
            remediation = gaps.remediation_path(item.concept_id, PREREQUISITES,
                                                lambda c: _is_weak(student_id, c))
            from app.modules.gamification_v1.quests import open_recovery_quest
            open_recovery_quest(student_id, item.concept_id, remediation)

    # Stage 7: review queue.
    review = retention.ReviewState(
        review_row["stability_days"], review_row["step"]
    ) if review_row else retention.ReviewState()
    if session["kind"] == "retention":
        review = retention.apply_review(review, correct, item.b, _concept_theta(student_id, item_concept, state["p_l"]))
    if session["kind"] == "retention" or (review_row is None and correct):
        store.upsert("review_schedule", {
            "student_id": student_id, "skill_id": item.concept_id,
            "stability_days": review.stability, "step": review.step,
            "due_at": retention.next_due(review, now).isoformat(),
            "last_reviewed_at": now.isoformat(),
        }, ("student_id", "skill_id"))

    # XP from verified events only.
    resolved = _resolve_active_tokens(student_id, item.concept_id, not seen_before) \
        if correct and not hinted else 0
    awards = []
    if tier_before < 3 <= mastery.tier:
        awards.append(xp.award("RULE_XP_03", student_id, item.concept_id))
    if tier_before < 4 <= mastery.tier:
        awards.append(xp.award("RULE_XP_04", student_id, item.concept_id))
    if tier_before < 5 <= mastery.tier:
        awards.append(xp.award("RULE_XP_05", student_id, item.concept_id))
    if correct and tier_before >= 3 and seen_before:
        awards.append(xp.award("RULE_XP_07", student_id, item_id))

    failures = 0 if correct else session["consecutive_failures"] + 1
    updated = {**session, "sequence_index": session["sequence_index"] + 1,
               "consecutive_failures": failures, "helped": False}
    store.update("practice_sessions_v1", {"id": session_id}, {
        "sequence_index": updated["sequence_index"], "consecutive_failures": failures, "helped": False,
    })
    session_concept = CONCEPTS_BY_ID[session["concept_id"]]
    # Selection works from the session's concept, even for an interleaved sibling.
    next_step = _next_step(student_id, updated, session_concept,
                           load_state(student_id, session["concept_id"]))

    result = {
        "correct": correct,
        "error_token": asdict(token_result) if token_result else None,
        "entrenched_misconception": entrenched,
        "attribution": _attribution(steps, token_result.bad_step if token_result else None, correct),
        "remediation_path": remediation,
        "p_mastery": round(state["p_l"], 4),
        "tier": mastery.tier,
        "tier_changed": mastery.tier != tier_before,
        "unlocks_children": mastery.unlocks_children,
        "tokens_resolved": resolved,
        "xp_awarded": [{"rule_id": a["rule_id"], "ledger": a["ledger"], "amount": a["amount"],
                        "badge": a["badge"]} for a in awards if a],
        "correct_answer": None if correct else f"{item.answer} {item.unit}".strip(),
        "next": next_step,
    }
    store.insert("practice_attempts_v1", {
        "student_id": student_id, "session_id": session_id, "concept_id": item.concept_id,
        "item_id": item_id, "correct": correct, "idempotency_key": idempotency_key,
        "confidence": confidence, "hints_used": hints_used, "result": result,
        "created_at": now.isoformat(),
    })
    return result
