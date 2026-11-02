"""Quests, consistency shield, study guilds and age-safe leagues."""
from __future__ import annotations

import hashlib
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional, Sequence

from app.modules import store, xp
from app.modules.curriculum.items import items_for
from app.modules.curriculum.ncert_seed import CONCEPTS_BY_ID, concepts_for_class
from app.modules.error_to_mastery.engine import NotFound, Conflict, grade

SHIELD_TARGET_DAYS = 4
GUILD_SIZE = 4
MIN_CONTRIBUTION = 0.20
LEAGUE_MIN_CLASS = 9


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


# ---------------------------------------------------------------- quests

def daily_quest(student_id: str, today: Optional[date] = None) -> dict[str, Any]:
    """3 due reviews + 1 error repair, frozen for the day once created."""
    today = today or _now().date()
    existing = store.get_one("quests", student_id=student_id, kind="daily", quest_key=today.isoformat())
    if existing:
        return existing
    now_iso = _now().isoformat()
    due = sorted((r for r in store.select("review_schedule", student_id=student_id) if r["due_at"] <= now_iso),
                 key=lambda r: r["due_at"])[:3]
    tokens = sorted(store.select("error_tokens", student_id=student_id, status="active"),
                    key=lambda t: t["created_at"])[:1]
    tasks = [{"type": "review", "concept_id": r["skill_id"], "done": False} for r in due]
    tasks += [{"type": "error_repair", "concept_id": t["concept_id"], "token": t["token"], "done": False} for t in tokens]
    row, _ = store.insert_unique("quests", {
        "student_id": student_id, "kind": "daily", "quest_key": today.isoformat(), "title": "Daily quest",
        "estimated_minutes": 15, "tasks": tasks, "status": "active", "created_at": now_iso,
    }, ("student_id", "kind", "quest_key"))
    return row


def open_recovery_quest(student_id: str, concept_id: str, path: Sequence[str]) -> dict[str, Any]:
    row, _ = store.insert_unique("quests", {
        "student_id": student_id, "kind": "recovery", "quest_key": concept_id,
        "title": f"Recovery: {CONCEPTS_BY_ID[concept_id].title}", "estimated_minutes": 20,
        "tasks": [{"type": "prerequisite", "concept_id": c, "done": False} for c in path],
        "status": "active", "created_at": _now().isoformat(),
    }, ("student_id", "kind", "quest_key"))
    return row


def start_boss(student_id: str, chapter_concepts: Sequence[str], class_level: int) -> dict[str, Any]:
    """A multi-concept synthesis battle over at least two concepts the student can access."""
    allowed = {c.concept_id for c in concepts_for_class(class_level)}
    concepts = [c for c in chapter_concepts if c in allowed]
    if len(concepts) < 2:
        raise Conflict("A boss battle needs at least two concepts from your class")
    items = []
    for concept_id in concepts:
        pool = sorted(items_for(concept_id), key=lambda i: i.b)
        items += pool[-3:-1]
    key = hashlib.sha256(f"{','.join(sorted(concepts))}:{_now().isoformat()}".encode()).hexdigest()[:16]
    row = store.insert("quests", {
        "student_id": student_id, "kind": "boss", "quest_key": key, "title": "Chapter boss battle",
        "estimated_minutes": 25, "tasks": [{"type": "boss_item", "item_id": i.item_id, "done": False} for i in items],
        "status": "active", "created_at": _now().isoformat(),
    })
    return {"quest_id": row["id"], "minutes": 25, "items": [i.public_view() for i in items]}


def submit_boss(student_id: str, quest_id: str, answers: dict[str, str]) -> dict[str, Any]:
    from app.modules.curriculum.items import get_item

    quest = store.get_one("quests", id=quest_id, student_id=student_id, kind="boss")
    if quest is None:
        raise NotFound(quest_id)
    if quest["status"] != "active":
        raise Conflict("This battle is already finished")
    correct = 0
    tasks = quest["tasks"]
    for task in tasks:
        task["done"] = grade(get_item(task["item_id"]), answers.get(task["item_id"], ""))
        correct += task["done"]
    mastered = correct >= 0.8 * len(tasks)
    store.update("quests", {"id": quest_id}, {"tasks": tasks, "status": "won" if mastered else "retry"})
    return {"correct": correct, "total": len(tasks), "boss_mastered": mastered}


# ---------------------------------------------------------------- consistency shield

def record_activity(student_id: str, day: Optional[date] = None) -> None:
    store.insert_unique("activity_days", {"student_id": student_id, "day": (day or _now().date()).isoformat()},
                        ("student_id", "day"))


def weekly_shield(student_id: str, today: Optional[date] = None) -> dict[str, Any]:
    """Keep the streak with 4 active days in 7; the other days count as protected rest days."""
    today = today or _now().date()
    start = _week_start(today)
    days = {row["day"] for row in store.select("activity_days", student_id=student_id)}
    active = sorted(d for d in days if start.isoformat() <= d <= (start + timedelta(days=6)).isoformat())
    remaining_days = 6 - (today - start).days
    needed = max(0, SHIELD_TARGET_DAYS - len(active))
    streak = 0
    week = _week_start(today) - timedelta(days=7)
    while sum(1 for d in days if week.isoformat() <= d <= (week + timedelta(days=6)).isoformat()) >= SHIELD_TARGET_DAYS:
        streak += 1
        week -= timedelta(days=7)
    return {
        "week_start": start.isoformat(), "active_days": len(active), "target_days": SHIELD_TARGET_DAYS,
        "shield_earned": needed == 0, "still_reachable": needed <= remaining_days + (0 if today.isoformat() in days else 1),
        "rest_days_protected": max(0, 7 - SHIELD_TARGET_DAYS - max(0, (today - start).days + 1 - len(active))),
        "consistent_weeks": streak + (1 if needed == 0 else 0),
    }


# ---------------------------------------------------------------- guilds

def create_guild(student_id: str, name: str, class_level: int) -> dict[str, Any]:
    if store.select("guild_members", student_id=student_id):
        raise Conflict("You are already in a guild")
    guild = store.insert("guilds", {"name": name[:40], "join_code": secrets.token_urlsafe(6),
                                    "class_band": _band(class_level), "created_at": _now().isoformat()})
    store.insert("guild_members", {"guild_id": guild["id"], "student_id": student_id,
                                   "joined_at": _now().isoformat()})
    return guild


def _band(class_level: int) -> str:
    return "6-8" if class_level < LEAGUE_MIN_CLASS else "9-12"


def join_guild(student_id: str, join_code: str, class_level: int) -> dict[str, Any]:
    guild = store.get_one("guilds", join_code=join_code)
    if guild is None:
        raise NotFound("guild")
    if store.select("guild_members", student_id=student_id):
        raise Conflict("You are already in a guild")
    if guild["class_band"] != _band(class_level):
        raise Conflict("Guilds keep similar age groups together")
    if len(store.select("guild_members", guild_id=guild["id"])) >= GUILD_SIZE:
        raise Conflict("This guild is full")
    store.insert("guild_members", {"guild_id": guild["id"], "student_id": student_id,
                                   "joined_at": _now().isoformat()})
    return guild


def _repairs(student_id: str, since: str) -> int:
    return sum(1 for t in store.select("error_tokens", student_id=student_id, status="resolved")
               if (t.get("resolved_at") or "") >= since)


def guild_quest(student_id: str, target: int = 20) -> dict[str, Any]:
    """Weekly repair goal. Completes only if each member gave at least 20% of the target."""
    membership = store.get_one("guild_members", student_id=student_id)
    if membership is None:
        raise NotFound("guild")
    members = store.select("guild_members", guild_id=membership["guild_id"])
    since = _week_start(_now().date()).isoformat()
    counts = {m["student_id"]: _repairs(m["student_id"], since) for m in members}
    total = sum(counts.values())
    floor = max(1, int(target * MIN_CONTRIBUTION + 0.999))
    return {
        "guild_id": membership["guild_id"], "target": target, "total": total,
        "min_each": floor, "complete": total >= target and all(c >= floor for c in counts.values()),
        # Peers see only whether each person met the floor, not who has how many.
        "members_at_minimum": sum(c >= floor for c in counts.values()), "member_count": len(members),
        "my_contribution": counts[student_id],
    }


# ---------------------------------------------------------------- leagues

def _pseudonym() -> str:
    animals = ("Falcon", "Otter", "Lynx", "Heron", "Panda", "Tiger", "Koel", "Gecko")
    return f"{secrets.choice(animals)}-{secrets.randbelow(9000) + 1000}"


def league_opt_in(student_id: str, class_level: Optional[int]) -> dict[str, Any]:
    if class_level is None or class_level < LEAGUE_MIN_CLASS:
        raise PermissionError("Leagues are for Classes 9-12; younger classes use cooperative goals")
    row, _ = store.insert_unique("league_entries", {
        "student_id": student_id, "pseudonym": _pseudonym(), "opted_in": True,
        "joined_at": _now().isoformat(),
    }, ("student_id",))
    store.update("league_entries", {"student_id": student_id}, {"opted_in": True})
    return {"pseudonym": row["pseudonym"], "opted_in": True}


def league_opt_out(student_id: str) -> None:
    store.update("league_entries", {"student_id": student_id}, {"opted_in": False})


def league_board(student_id: str, class_level: Optional[int]) -> dict[str, Any]:
    if class_level is None or class_level < LEAGUE_MIN_CLASS:
        raise PermissionError("Leagues are for Classes 9-12; younger classes use cooperative goals")
    entries = [e for e in store.select("league_entries") if e["opted_in"]]
    me = next((e for e in entries if e["student_id"] == student_id), None)
    if me is None:
        raise Conflict("Opt in to see the league")
    since = _week_start(_now().date()).isoformat()
    scored = sorted(((_repairs(e["student_id"], since), e["pseudonym"]) for e in entries), key=lambda s: (-s[0], s[1]))
    return {"metric": "error_repairs_this_week", "me": me["pseudonym"],
            "board": [{"rank": i + 1, "pseudonym": name, "repairs": score}
                      for i, (score, name) in enumerate(scored[:50])]}


def class_goal(classroom_id: str, student_id: str, target: int = 50) -> dict[str, Any]:
    """The cooperative goal: only the class total is shown, never individuals."""
    enrolled = store.select("classroom_enrollments", classroom_id=classroom_id)
    if not any(e["student_id"] == student_id for e in enrolled):
        raise NotFound(classroom_id)
    since = _week_start(_now().date()).isoformat()
    total = sum(_repairs(e["student_id"], since) for e in enrolled)
    return {"classroom_id": classroom_id, "target": target, "progress": total, "complete": total >= target}


def xp_summary(student_id: str) -> dict[str, int]:
    return xp.balances(student_id)
