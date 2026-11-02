"""Role dashboards for students, parents, teachers and creators."""
from __future__ import annotations

import csv
import io
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode

from app.modules import store, xp
from app.modules.curriculum.ncert_seed import CONCEPTS_BY_ID, concepts_for_class
from app.modules.error_to_mastery.engine import NotFound, is_unlocked, load_state
from app.modules.gamification_v1 import quests
from app.modules.privacy import service as privacy

PLAN_MINUTES = 30
PLAN_SPLIT = {"spaced_error_repair": 0.30, "core_progression": 0.50, "interleaved_transfer": 0.20}
TIER_WORDS = {0: "not started", 1: "just introduced", 2: "getting there", 3: "can do it independently",
              4: "can apply it to new problems", 5: "remembers it weeks later"}
TOKENS = tuple(f"E{i:02d}" for i in range(1, 21))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _task(category: str, concept_id: str, action: str) -> dict[str, str]:
    return {"category": category, "concept_id": concept_id, "title": CONCEPTS_BY_ID[concept_id].title, "action": action}


def daily_plan(student_id: str, class_level: int) -> dict[str, Any]:
    """Minutes follow 30/50/20. Each category offers tasks; the student picks one of 3."""
    concepts = concepts_for_class(class_level)
    states = {c.concept_id: load_state(student_id, c.concept_id) for c in concepts}
    now_iso = _now().isoformat()
    repair = [
        _task("spaced_error_repair", r["skill_id"], "review")
        for r in sorted(store.select("review_schedule", student_id=student_id), key=lambda r: r["due_at"])
        if r["due_at"] <= now_iso and r["skill_id"] in states
    ]
    seen_tokens = set()
    for token in store.select("error_tokens", student_id=student_id, status="active"):
        if token["concept_id"] in states and token["concept_id"] not in seen_tokens:
            seen_tokens.add(token["concept_id"])
            repair.append(_task("spaced_error_repair", token["concept_id"], "repair"))
    core = [_task("core_progression", c.concept_id, "learn") for c in concepts
            if states[c.concept_id]["tier"] < 3 and is_unlocked(student_id, c)]
    transfer = [_task("interleaved_transfer", c.concept_id, "transfer") for c in concepts
                if states[c.concept_id]["tier"] == 3]
    buckets = {"spaced_error_repair": repair, "core_progression": core, "interleaved_transfer": transfer}
    # An empty category gives its minutes to core progression.
    minutes = {k: round(PLAN_MINUTES * share) if buckets[k] else 0 for k, share in PLAN_SPLIT.items()}
    minutes["core_progression"] += PLAN_MINUTES - sum(minutes.values())
    choices = next_choices(buckets)
    return {
        "date": _now().date().isoformat(), "total_minutes": PLAN_MINUTES, "split_percent": {k: int(v * 100) for k, v in PLAN_SPLIT.items()},
        "minutes": minutes, "tasks": buckets, "choices": choices,
    }


def next_choices(buckets: dict[str, list[dict]]) -> list[dict]:
    """Up to 3 valid tasks, taken from different categories first to give a real choice."""
    choices: list[dict] = []
    for bucket in buckets.values():
        if bucket:
            choices.append(bucket[0])
    for bucket in buckets.values():
        for task in bucket[1:]:
            if len(choices) < 3:
                choices.append(task)
    return choices[:3]


def set_intention(student_id: str, when: str, action: str) -> dict[str, Any]:
    return store.upsert("implementation_intentions", {
        "student_id": student_id, "when_text": when[:120], "action_text": action[:120],
        "statement": f"When {when[:120]}, I will {action[:120]}", "updated_at": _now().isoformat(),
    }, ("student_id",))


def student_dashboard(student_id: str, class_level: int) -> dict[str, Any]:
    quests.record_activity(student_id)
    return {
        "plan": daily_plan(student_id, class_level),
        "intention": store.get_one("implementation_intentions", student_id=student_id),
        "daily_quest": quests.daily_quest(student_id),
        "recovery_quests": [q for q in store.select("quests", student_id=student_id, kind="recovery") if q["status"] == "active"],
        "shield": quests.weekly_shield(student_id),
        "xp": xp.balances(student_id),
        "consent": privacy.consent_status(student_id),
        "mastery": [
            {"concept_id": c.concept_id, "title": c.title, "tier": load_state(student_id, c.concept_id)["tier"],
             "p_mastery": round(load_state(student_id, c.concept_id)["p_l"], 3)}
            for c in concepts_for_class(class_level)
        ],
    }


def family_progress_card(student_id: str) -> dict[str, Any]:
    week_ago = (_now() - timedelta(days=7)).isoformat()
    states = [s for s in store.select("learner_bkt_state", student_id=student_id)]
    recent_days = [d for d in store.select("activity_days", student_id=student_id) if d["day"] >= week_ago[:10]]
    repaired = [t for t in store.select("error_tokens", student_id=student_id, status="resolved") if (t.get("resolved_at") or "") >= week_ago]
    active = store.select("error_tokens", student_id=student_id, status="active")
    moved = [s for s in states if (s.get("updated_at") or "") >= week_ago and s["tier"] >= 3]
    focus = sorted({t["concept_id"] for t in active})[:2]
    lines = [f"Studied on {len(recent_days)} of the last 7 days.",
             f"Fixed {len(repaired)} mistake{'s' if len(repaired) != 1 else ''} this week."]
    if moved:
        names = ", ".join(CONCEPTS_BY_ID[s["skill_id"]].title for s in moved[:3] if s["skill_id"] in CONCEPTS_BY_ID)
        lines.append(f"Can now do these independently: {names}.")
    if focus:
        lines.append("Working on next: " + ", ".join(CONCEPTS_BY_ID[c].title for c in focus) + ".")
    return {
        "student_id": student_id, "week_ending": _now().date().isoformat(), "summary": lines,
        "topics": [{"title": CONCEPTS_BY_ID[s["skill_id"]].title, "status": TIER_WORDS[s["tier"]]}
                   for s in states if s["skill_id"] in CONCEPTS_BY_ID],
        "how_to_help": "Ask them to explain one idea to you in their own words; praise the effort, not the marks.",
    }


def parent_dashboard(parent_id: str) -> dict[str, Any]:
    cards = []
    awaiting = []
    for link in store.select("parent_student_links", parent_id=parent_id, verification_status="verified"):
        student_id = link["student_id"]
        if privacy.has_consent(student_id, "parent_reports"):
            cards.append(family_progress_card(student_id))
        else:
            awaiting.append(student_id)
    return {"cards": cards, "awaiting_consent": awaiting}


def _owned_classroom(teacher_id: str, classroom_id: str) -> dict[str, Any]:
    classroom = store.get_one("classrooms", id=classroom_id, teacher_id=teacher_id)
    if classroom is None:
        raise NotFound(classroom_id)
    return classroom


def _roster(classroom_id: str) -> list[str]:
    return [e["student_id"] for e in store.select("classroom_enrollments", classroom_id=classroom_id)
            if e.get("status", "enrolled") == "enrolled"]


def _visible_students(classroom_id: str) -> list[str]:
    """Only students with school-sharing consent appear in teacher analytics."""
    return [s for s in _roster(classroom_id) if privacy.has_consent(s, "school_sharing")]


def heatmap(teacher_id: str, classroom_id: str) -> dict[str, Any]:
    _owned_classroom(teacher_id, classroom_id)
    students = _visible_students(classroom_id)
    concept_ids = set()
    rows = []
    token_totals = {t: 0 for t in TOKENS}
    for student_id in students:
        cells: dict[str, int] = {}
        for token in store.select("error_tokens", student_id=student_id, status="active"):
            concept_ids.add(token["concept_id"])
            cells[token["concept_id"]] = cells.get(token["concept_id"], 0) + 1
            token_totals[token["token"]] = token_totals.get(token["token"], 0) + 1
        rows.append({"student_id": student_id, "active_errors_by_concept": cells})
    return {
        "classroom_id": classroom_id, "students": rows, "concepts": sorted(concept_ids),
        "token_totals": token_totals,
        "hidden_without_consent": len(_roster(classroom_id)) - len(students),
    }


def teacher_dashboard(teacher_id: str) -> dict[str, Any]:
    classrooms = store.select("classrooms", teacher_id=teacher_id)
    return {"classrooms": [{"id": c["id"], "name": c["name"], "grade_level": c["grade_level"],
                            "heatmap": heatmap(teacher_id, c["id"])} for c in classrooms]}


def assign_remediation(teacher_id: str, classroom_id: str, concept_id: str, token: Optional[str]) -> dict[str, Any]:
    """One click: assign to the consented students who hold active errors on that concept."""
    _owned_classroom(teacher_id, classroom_id)
    if concept_id not in CONCEPTS_BY_ID:
        raise NotFound(concept_id)
    assigned = []
    for student_id in _visible_students(classroom_id):
        errors = store.select("error_tokens", student_id=student_id, concept_id=concept_id, status="active")
        if token:
            errors = [e for e in errors if e["token"] == token]
        if errors:
            store.insert_unique("homework_assignments", {
                "student_id": student_id, "classroom_id": classroom_id, "concept_id": concept_id,
                "teacher_id": teacher_id, "status": "assigned", "created_at": _now().isoformat(),
            }, ("student_id", "classroom_id", "concept_id"))
            assigned.append(student_id)
    return {"assigned_count": len(assigned), "student_ids": assigned}


def _csv_safe(value: Any) -> Any:
    """Block spreadsheet formula injection in exported cells."""
    text = str(value)
    return f"'{text}" if text[:1] in ("=", "+", "-", "@", "\t", "\r") else value


def sis_csv(teacher_id: str, classroom_id: str) -> str:
    _owned_classroom(teacher_id, classroom_id)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["student_id", "concept_id", "concept", "tier", "p_mastery", "active_errors"])
    for student_id in _visible_students(classroom_id):
        for state in store.select("learner_bkt_state", student_id=student_id):
            concept = CONCEPTS_BY_ID.get(state["skill_id"])
            if concept is None:
                continue
            errors = store.select("error_tokens", student_id=student_id, concept_id=concept.concept_id, status="active")
            writer.writerow([_csv_safe(v) for v in (student_id, concept.concept_id, concept.title, state["tier"],
                                                    round(state["p_l"], 3), len(errors))])
    return buffer.getvalue()


# ---------------------------------------------------------------- creator studio

def create_utm_link(creator_id: str, concept_id: str, campaign: str, base_url: str) -> dict[str, Any]:
    if concept_id not in CONCEPTS_BY_ID:
        raise NotFound(concept_id)
    code = secrets.token_urlsafe(8)
    query = urlencode({"utm_source": "creator", "utm_medium": "video", "utm_campaign": campaign[:60],
                       "utm_content": code, "concept": concept_id})
    url = f"{base_url.rstrip('/')}/diagnostic?{query}"
    store.insert("creator_links", {"code": code, "creator_id": creator_id, "concept_id": concept_id,
                                   "campaign": campaign[:60], "url": url, "created_at": _now().isoformat()})
    return {"code": code, "url": url}


EVENTS = ("click", "signup", "diagnostic_completed", "paid")


def track_event(code: str, event: str) -> bool:
    if event not in EVENTS or store.get_one("creator_links", code=code) is None:
        return False
    store.insert("creator_link_events", {"code": code, "event": event, "created_at": _now().isoformat()})
    return True


def creator_analytics(creator_id: str) -> dict[str, Any]:
    """Aggregate counts only; no student can be identified from this."""
    results = []
    for link in store.select("creator_links", creator_id=creator_id):
        counts = {event: 0 for event in EVENTS}
        for row in store.select("creator_link_events", code=link["code"]):
            counts[row["event"]] += 1
        clicks = counts["click"]
        results.append({"code": link["code"], "campaign": link["campaign"], "url": link["url"],
                        "counts": counts,
                        "click_to_paid_percent": round(100 * counts["paid"] / clicks, 1) if clicks else 0.0})
    return {"links": results}
