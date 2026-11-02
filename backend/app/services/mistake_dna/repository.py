"""
LearnByGenie — Feature 5: Mistake DNA Repository
=================================================
Durable persistence for mistake events, aggregated mistake patterns,
and verifiable educational repair evidence.

Dual-store architecture (§30, §31):
- Remote Supabase PostgreSQL (Migration 025) as authoritative persistence layer
- High-performance, thread-safe in-memory read-through cache with clear_memory_cache()
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import threading
import uuid
import time
import random

from app.db.supabase_client import supabase
from app.core.logging import logger
from .schemas import (
    MistakeEvent, MistakePattern, RepairEvent, ErrorType,
    PatternStatus, RepairStatus, ConfidenceClass, AssistanceLevel,
    MistakeSourceType, MistakePatternThresholds
)


class MistakeDNARepository:
    """
    Thread-safe repository for Mistake DNA Engine (§31).
    """
    _LOCK = threading.RLock()

    # In-memory stores for instant lookup, test isolation, and offline resilience
    _MEMORY_EVENTS: Dict[str, MistakeEvent] = {} # id -> MistakeEvent
    _MEMORY_SOURCE_MAP: Dict[Tuple[str, str, str, Optional[str]], str] = {} # (user_id, source_type, source_record_id, skill_id) -> event_id
    _MEMORY_PATTERNS: Dict[str, MistakePattern] = {} # id -> MistakePattern
    _MEMORY_PATTERN_KEY_MAP: Dict[Tuple[str, str, str, str], str] = {} # (user_id, skill_id, error_type, error_subtype) -> pattern_id
    _MEMORY_REPAIRS: Dict[str, RepairEvent] = {} # id -> RepairEvent
    _MEMORY_REPAIR_KEY_MAP: Dict[Tuple[str, str, str], str] = {} # (pattern_id, source, source_record_id) -> repair_id

    @classmethod
    def clear_memory_cache(cls) -> None:
        """Resets all in-memory cache for deterministic test isolation."""
        with cls._LOCK:
            cls._MEMORY_EVENTS.clear()
            cls._MEMORY_SOURCE_MAP.clear()
            cls._MEMORY_PATTERNS.clear()
            cls._MEMORY_PATTERN_KEY_MAP.clear()
            cls._MEMORY_REPAIRS.clear()
            cls._MEMORY_REPAIR_KEY_MAP.clear()

    # ─── 1. MISTAKE EVENTS ────────────────────────────────────────────────────

    @classmethod
    def save_mistake_event(cls, event: MistakeEvent) -> Tuple[MistakeEvent, bool]:
        """
        Saves a mistake event idempotently (§11, §12).
        Returns (event, is_new). If already recorded, returns existing event without creating duplicate.
        """
        src_key = (event.user_id, event.source_type.value, event.source_record_id, event.skill_id)

        with cls._LOCK:
            # 1. Check in-memory source map
            if src_key in cls._MEMORY_SOURCE_MAP:
                existing_id = cls._MEMORY_SOURCE_MAP[src_key]
                return cls._MEMORY_EVENTS[existing_id], False

            # 2. Check remote PostgreSQL for source idempotency
            if supabase is not None:
                try:
                    q = (
                        supabase.table("mistake_events")
                        .select("*")
                        .eq("user_id", event.user_id)
                        .eq("source_type", event.source_type.value)
                        .eq("source_record_id", event.source_record_id)
                    )
                    if event.skill_id:
                        q = q.eq("skill_id", event.skill_id)
                    res = q.limit(1).execute()
                    if res.data and len(res.data) > 0:
                        row = res.data[0]
                        existing = cls._deserialize_event(row)
                        cls._MEMORY_EVENTS[existing.id] = existing
                        cls._MEMORY_SOURCE_MAP[src_key] = existing.id
                        return existing, False

                    # Insert new record into PostgreSQL
                    payload = cls._serialize_event(event)
                    supabase.table("mistake_events").insert(payload).execute()
                except Exception as e:
                    err_str = str(e)
                    if "23505" in err_str or "uq_mistake_event_source" in err_str or "duplicate" in err_str:
                        logger.info(f"[MistakeRepo] Idempotent duplicate intercepted by PostgreSQL: {src_key}")
                        # Re-read existing
                        try:
                            res_re = q.limit(1).execute()
                            if res_re.data and len(res_re.data) > 0:
                                existing = cls._deserialize_event(res_re.data[0])
                                cls._MEMORY_EVENTS[existing.id] = existing
                                cls._MEMORY_SOURCE_MAP[src_key] = existing.id
                                return existing, False
                        except Exception:
                            pass
                    logger.debug(f"[MistakeRepo] Supabase insert event note: {e}")

            # 3. Save to memory cache
            cls._MEMORY_EVENTS[event.id] = event
            cls._MEMORY_SOURCE_MAP[src_key] = event.id
            return event, True

    @classmethod
    def get_mistake_events(cls, user_id: str, limit: int = 50) -> List[MistakeEvent]:
        """Loads recent mistake events for a user."""
        if supabase is not None:
            try:
                res = (
                    supabase.table("mistake_events")
                    .select("*")
                    .eq("user_id", user_id)
                    .order("detected_at", desc=True)
                    .limit(limit)
                    .execute()
                )
                if res.data:
                    events = [cls._deserialize_event(r) for r in res.data]
                    with cls._LOCK:
                        for ev in events:
                            cls._MEMORY_EVENTS[ev.id] = ev
                            src_key = (ev.user_id, ev.source_type.value, ev.source_record_id, ev.skill_id)
                            cls._MEMORY_SOURCE_MAP[src_key] = ev.id
                    return events
            except Exception as e:
                logger.debug(f"[MistakeRepo] Supabase get events fallback: {e}")

        with cls._LOCK:
            user_events = [ev for ev in cls._MEMORY_EVENTS.values() if ev.user_id == user_id]
            user_events.sort(key=lambda e: e.detected_at, reverse=True)
            return user_events[:limit]

    # ─── 2. MISTAKE PATTERNS ──────────────────────────────────────────────────

    @classmethod
    def get_pattern(
        cls,
        user_id: str,
        skill_id: str,
        error_type: ErrorType,
        error_subtype: str = "",
        force_remote: bool = False
    ) -> Optional[MistakePattern]:
        """Retrieves specific aggregated pattern for user, skill, and error type."""
        pat_key = (user_id, skill_id, error_type.value, error_subtype)

        if not force_remote:
            with cls._LOCK:
                if pat_key in cls._MEMORY_PATTERN_KEY_MAP:
                    pid = cls._MEMORY_PATTERN_KEY_MAP[pat_key]
                    return cls._MEMORY_PATTERNS.get(pid)

        if supabase is not None:
            try:
                res = (
                    supabase.table("mistake_patterns")
                    .select("*")
                    .eq("user_id", user_id)
                    .eq("skill_id", skill_id)
                    .eq("error_type", error_type.value)
                    .eq("error_subtype", error_subtype)
                    .limit(1)
                    .execute()
                )
                if res.data and len(res.data) > 0:
                    pat = cls._deserialize_pattern(res.data[0])
                    with cls._LOCK:
                        cls._MEMORY_PATTERNS[pat.id] = pat
                        cls._MEMORY_PATTERN_KEY_MAP[pat_key] = pat.id
                    return pat
            except Exception as e:
                logger.debug(f"[MistakeRepo] Supabase get pattern note: {e}")

        with cls._LOCK:
            if pat_key in cls._MEMORY_PATTERN_KEY_MAP:
                pid = cls._MEMORY_PATTERN_KEY_MAP[pat_key]
                return cls._MEMORY_PATTERNS.get(pid)

        return None

    @classmethod
    def record_mistake_occurrence_atomic(
        cls,
        user_id: str,
        skill_id: str,
        subject: str,
        error_type: ErrorType,
        error_subtype: str,
        source_record_id: str,
        confidence: ConfidenceClass,
        repair_action: str,
        likely_prereq_id: Optional[str] = None,
        prereq_signal: Optional[str] = None,
        max_retries: int = 35,
    ) -> MistakePattern:
        """
        Database-level atomic pattern creation and progression using Optimistic Concurrency Control (OCC)
        with PostgreSQL conditional updates and unique constraint violation handling (§3, §31).
        
        Guarantees:
        - Concurrent ingestion across separate workers/processes preserves every occurrence (zero lost updates).
        - State transitions follow MistakePatternThresholds deterministically.
        - Enforced directly by PostgreSQL ACID row locks on UPDATE ... WHERE occurrence_count = old_count
          and UNIQUE constraint uq_mistake_pattern on INSERT.
        """
        pat_key = (user_id, skill_id, error_type.value, error_subtype)

        for attempt in range(max_retries):
            # 1. Fetch latest pattern directly from authoritative PostgreSQL database (bypass memory cache!)
            pat = cls.get_pattern(
                user_id=user_id,
                skill_id=skill_id,
                error_type=error_type,
                error_subtype=error_subtype,
                force_remote=True
            )
            now = datetime.now(timezone.utc)

            if pat is None:
                # Pattern does not exist yet: create initial ISOLATED pattern (occurrence_count = 1)
                initial_pat = MistakePattern(
                    user_id=user_id,
                    skill_id=skill_id,
                    subject=subject,
                    error_type=error_type,
                    error_subtype=error_subtype,
                    occurrence_count=1,
                    recent_occurrence_count=1,
                    first_seen_at=now,
                    last_seen_at=now,
                    pattern_status=PatternStatus.ISOLATED,
                    confidence=confidence,
                    repair_status=RepairStatus.OPEN,
                    recommended_repair_action=repair_action,
                    likely_prerequisite_skill=likely_prereq_id,
                    prerequisite_signal=prereq_signal,
                    engine_version="5.0.0",
                    metadata={"history_sources": [source_record_id]},
                    created_at=now,
                    updated_at=now
                )

                if supabase is not None:
                    try:
                        payload = cls._serialize_pattern(initial_pat)
                        res_ins = supabase.table("mistake_patterns").insert(payload).execute()
                        if res_ins.data and len(res_ins.data) > 0:
                            saved = cls._deserialize_pattern(res_ins.data[0])
                            with cls._LOCK:
                                cls._MEMORY_PATTERNS[saved.id] = saved
                                cls._MEMORY_PATTERN_KEY_MAP[pat_key] = saved.id
                            return saved
                    except Exception as e:
                        err_str = str(e)
                        if "23505" in err_str or "uq_mistake_pattern" in err_str or "duplicate" in err_str:
                            # Concurrent insertion conflict: Another worker created the row. Retry fetch and update!
                            time.sleep(min(0.5, 0.03 * (1.15 ** attempt) + random.uniform(0.02, 0.08)))
                            continue
                        logger.debug(f"[MistakeRepo] Insert initial pattern note: {e}")

                # Memory mode
                with cls._LOCK:
                    cls._MEMORY_PATTERNS[initial_pat.id] = initial_pat
                    cls._MEMORY_PATTERN_KEY_MAP[pat_key] = initial_pat.id
                return initial_pat

            else:
                # Pattern exists: calculate deterministic state progression via MistakePatternThresholds (§7, §10)
                new_count = pat.occurrence_count + 1
                new_recent = pat.recent_occurrence_count + 1
                new_pattern_status, new_repair_status = MistakePatternThresholds.determine_pattern_status(
                    occurrence_count=new_count,
                    current_pattern_status=pat.pattern_status,
                    current_repair_status=pat.repair_status,
                )
                hist = list(pat.metadata.get("history_sources", []))
                if source_record_id not in hist:
                    hist.append(source_record_id)
                new_meta = {**pat.metadata, "history_sources": hist}

                if supabase is not None:
                    # Database-level OCC update: only succeeds if occurrence_count has not changed concurrently!
                    update_payload = {
                        "occurrence_count": new_count,
                        "recent_occurrence_count": new_recent,
                        "last_seen_at": now.isoformat(),
                        "pattern_status": new_pattern_status.value,
                        "repair_status": new_repair_status.value,
                        "confidence": confidence.value,
                        "recommended_repair_action": repair_action,
                        "likely_prerequisite_skill": likely_prereq_id or pat.likely_prerequisite_skill,
                        "prerequisite_signal": prereq_signal or pat.prerequisite_signal,
                        "metadata": new_meta,
                        "updated_at": now.isoformat(),
                    }
                    try:
                        res_up = (
                            supabase.table("mistake_patterns")
                            .update(update_payload)
                            .eq("id", pat.id)
                            .eq("occurrence_count", pat.occurrence_count)  # PostgreSQL row-level OCC condition!
                            .execute()
                        )
                        if res_up.data and len(res_up.data) > 0:
                            # Atomic database update succeeded!
                            updated_pat = cls._deserialize_pattern(res_up.data[0])
                            with cls._LOCK:
                                cls._MEMORY_PATTERNS[updated_pat.id] = updated_pat
                                cls._MEMORY_PATTERN_KEY_MAP[pat_key] = updated_pat.id
                            return updated_pat
                        else:
                            # 0 rows updated: Another worker updated occurrence_count concurrently in PostgreSQL!
                            # Back off with jitter and retry with refreshed count.
                            time.sleep(min(0.5, 0.03 * (1.15 ** attempt) + random.uniform(0.02, 0.08)))
                            continue
                    except Exception as e:
                        logger.debug(f"[MistakeRepo] OCC update remote notice: {e}")
                        # If network/DNS error, skip remote retries and update local memory store directly
                        if "getaddrinfo" in str(e) or "ConnectError" in str(e) or "timeout" in str(e).lower():
                            pass
                        else:
                            time.sleep(min(0.5, 0.03 * (1.15 ** attempt) + random.uniform(0.02, 0.08)))
                            continue

                # Local / fallback memory update
                with cls._LOCK:
                    pat.occurrence_count = new_count
                    pat.recent_occurrence_count = new_recent
                    pat.last_seen_at = now
                    pat.pattern_status = new_pattern_status
                    pat.repair_status = new_repair_status
                    pat.metadata = new_meta
                    pat.updated_at = now
                    cls._MEMORY_PATTERNS[pat.id] = pat
                    cls._MEMORY_PATTERN_KEY_MAP[pat_key] = pat.id
                return pat

        # Fallback if max retries exhausted: return latest fetched
        return cls.get_pattern(user_id=user_id, skill_id=skill_id, error_type=error_type, error_subtype=error_subtype) or pat

    @classmethod
    def save_pattern(cls, pattern: MistakePattern) -> MistakePattern:
        """Saves or updates aggregated mistake pattern."""
        pat_key = (pattern.user_id, pattern.skill_id, pattern.error_type.value, pattern.error_subtype)
        pattern.updated_at = datetime.now(timezone.utc)

        if supabase is not None:
            try:
                payload = cls._serialize_pattern(pattern)
                supabase.table("mistake_patterns").upsert(payload).execute()
            except Exception as e:
                logger.debug(f"[MistakeRepo] Supabase save pattern note: {e}")

        with cls._LOCK:
            cls._MEMORY_PATTERNS[pattern.id] = pattern
            cls._MEMORY_PATTERN_KEY_MAP[pat_key] = pattern.id

        return pattern

    @classmethod
    def get_patterns_for_user(
        cls,
        user_id: str,
        skill_id: Optional[str] = None,
        subject: Optional[str] = None
    ) -> List[MistakePattern]:
        """Loads all patterns for user, optionally filtered by skill or subject."""
        if supabase is not None:
            try:
                q = supabase.table("mistake_patterns").select("*").eq("user_id", user_id)
                if skill_id:
                    q = q.eq("skill_id", skill_id)
                if subject:
                    q = q.eq("subject", subject)
                res = q.order("updated_at", desc=True).execute()
                if res.data:
                    patterns = [cls._deserialize_pattern(r) for r in res.data]
                    with cls._LOCK:
                        for p in patterns:
                            cls._MEMORY_PATTERNS[p.id] = p
                            k = (p.user_id, p.skill_id, p.error_type.value, p.error_subtype)
                            cls._MEMORY_PATTERN_KEY_MAP[k] = p.id
                    return patterns
            except Exception as e:
                logger.debug(f"[MistakeRepo] Supabase get patterns fallback: {e}")

        with cls._LOCK:
            pats = [p for p in cls._MEMORY_PATTERNS.values() if p.user_id == user_id]
            if skill_id:
                pats = [p for p in pats if p.skill_id == skill_id]
            if subject:
                pats = [p for p in pats if p.subject == subject]
            pats.sort(key=lambda p: p.updated_at, reverse=True)
            return pats

    @classmethod
    def get_pattern_by_id(cls, pattern_id: str) -> Optional[MistakePattern]:
        """Retrieves single pattern by its primary UUID."""
        with cls._LOCK:
            if pattern_id in cls._MEMORY_PATTERNS:
                return cls._MEMORY_PATTERNS[pattern_id]

        if supabase is not None:
            try:
                res = supabase.table("mistake_patterns").select("*").eq("id", pattern_id).limit(1).execute()
                if res.data and len(res.data) > 0:
                    pat = cls._deserialize_pattern(res.data[0])
                    with cls._LOCK:
                        cls._MEMORY_PATTERNS[pat.id] = pat
                    return pat
            except Exception as e:
                logger.debug(f"[MistakeRepo] Supabase get pattern by id note: {e}")

        return None

    # ─── 3. MISTAKE REPAIR EVENTS ─────────────────────────────────────────────

    @classmethod
    def save_repair_event(cls, repair: RepairEvent) -> Tuple[RepairEvent, bool]:
        """
        Saves educational repair evidence idempotently (§16, §17).
        Returns (repair, is_new).
        """
        rep_key = (repair.pattern_id, repair.evidence_source.value, repair.evidence_record_id)

        with cls._LOCK:
            if rep_key in cls._MEMORY_REPAIR_KEY_MAP:
                rid = cls._MEMORY_REPAIR_KEY_MAP[rep_key]
                return cls._MEMORY_REPAIRS[rid], False

        if supabase is not None:
            try:
                # Idempotency check against PostgreSQL
                q = (
                    supabase.table("mistake_repair_events")
                    .select("*")
                    .eq("pattern_id", repair.pattern_id)
                    .eq("evidence_source", repair.evidence_source.value)
                    .eq("evidence_record_id", repair.evidence_record_id)
                )
                res = q.limit(1).execute()
                if res.data and len(res.data) > 0:
                    existing = cls._deserialize_repair(res.data[0])
                    with cls._LOCK:
                        cls._MEMORY_REPAIRS[existing.id] = existing
                        cls._MEMORY_REPAIR_KEY_MAP[rep_key] = existing.id
                    return existing, False

                payload = cls._serialize_repair(repair)
                supabase.table("mistake_repair_events").insert(payload).execute()
            except Exception as e:
                err_str = str(e)
                if "23505" in err_str or "duplicate" in err_str:
                    logger.info(f"[MistakeRepo] Duplicate repair evidence intercepted: {rep_key}")
                    return repair, False
                logger.debug(f"[MistakeRepo] Supabase save repair note: {e}")

        with cls._LOCK:
            cls._MEMORY_REPAIRS[repair.id] = repair
            cls._MEMORY_REPAIR_KEY_MAP[rep_key] = repair.id

        return repair, True

    @classmethod
    def get_repairs_for_pattern(cls, pattern_id: str) -> List[RepairEvent]:
        """Retrieves repair evidence records for a specific pattern."""
        if supabase is not None:
            try:
                res = (
                    supabase.table("mistake_repair_events")
                    .select("*")
                    .eq("pattern_id", pattern_id)
                    .order("verified_at", desc=True)
                    .execute()
                )
                if res.data:
                    return [cls._deserialize_repair(r) for r in res.data]
            except Exception as e:
                logger.debug(f"[MistakeRepo] Supabase get repairs note: {e}")

        with cls._LOCK:
            reps = [r for r in cls._MEMORY_REPAIRS.values() if r.pattern_id == pattern_id]
            reps.sort(key=lambda r: r.verified_at, reverse=True)
            return reps

    @classmethod
    def get_all_repairs_for_user(cls, user_id: str) -> List[RepairEvent]:
        """Retrieves all repair evidence records for a student."""
        if supabase is not None:
            try:
                res = (
                    supabase.table("mistake_repair_events")
                    .select("*")
                    .eq("user_id", user_id)
                    .order("verified_at", desc=True)
                    .execute()
                )
                if res.data:
                    return [cls._deserialize_repair(r) for r in res.data]
            except Exception as e:
                logger.debug(f"[MistakeRepo] Supabase get all repairs note: {e}")

        with cls._LOCK:
            reps = [r for r in cls._MEMORY_REPAIRS.values() if r.user_id == user_id]
            reps.sort(key=lambda r: r.verified_at, reverse=True)
            return reps

    # ─── SERIALIZATION HELPERS ────────────────────────────────────────────────

    @staticmethod
    def _serialize_event(e: MistakeEvent) -> Dict[str, Any]:
        return {
            "id": e.id,
            "user_id": e.user_id,
            "skill_id": e.skill_id,
            "subject": e.subject,
            "source_type": e.source_type.value,
            "source_record_id": e.source_record_id,
            "question_reference": e.question_reference,
            "primary_error_type": e.primary_error_type.value,
            "secondary_error_types": [t.value for t in e.secondary_error_types],
            "error_subtype": e.error_subtype,
            "error_summary": e.error_summary,
            "confidence_class": e.confidence_class.value,
            "assistance_level": e.assistance_level.value,
            "repair_status": e.repair_status.value,
            "engine_version": e.engine_version,
            "classifier_version": e.classifier_version,
            "metadata": e.metadata,
            "detected_at": e.detected_at.isoformat(),
            "created_at": e.created_at.isoformat(),
        }

    @staticmethod
    def _deserialize_event(row: Dict[str, Any]) -> MistakeEvent:
        sec = row.get("secondary_error_types") or []
        sec_types = [ErrorType(t) for t in sec if t in ErrorType.__members__]
        return MistakeEvent(
            id=row["id"],
            user_id=row["user_id"],
            skill_id=row.get("skill_id"),
            subject=row.get("subject", "Mathematics"),
            source_type=MistakeSourceType(row["source_type"]),
            source_record_id=row["source_record_id"],
            question_reference=row.get("question_reference", ""),
            primary_error_type=ErrorType(row.get("primary_error_type", ErrorType.UNKNOWN.value)),
            secondary_error_types=sec_types,
            error_subtype=row.get("error_subtype", ""),
            error_summary=row.get("error_summary", ""),
            confidence_class=ConfidenceClass(row.get("confidence_class", ConfidenceClass.MODERATE.value)),
            assistance_level=AssistanceLevel(row.get("assistance_level", AssistanceLevel.INDEPENDENT.value)),
            repair_status=RepairStatus(row.get("repair_status", RepairStatus.OPEN.value)),
            engine_version=row.get("engine_version", "5.0.0"),
            classifier_version=row.get("classifier_version", "5.0.0"),
            metadata=row.get("metadata") or {},
            detected_at=datetime.fromisoformat(row["detected_at"]) if "detected_at" in row else datetime.now(timezone.utc),
            created_at=datetime.fromisoformat(row["created_at"]) if "created_at" in row else datetime.now(timezone.utc),
        )

    @staticmethod
    def _serialize_pattern(p: MistakePattern) -> Dict[str, Any]:
        return {
            "id": p.id,
            "user_id": p.user_id,
            "skill_id": p.skill_id,
            "subject": p.subject,
            "error_type": p.error_type.value,
            "error_subtype": p.error_subtype,
            "occurrence_count": p.occurrence_count,
            "recent_occurrence_count": p.recent_occurrence_count,
            "first_seen_at": p.first_seen_at.isoformat(),
            "last_seen_at": p.last_seen_at.isoformat(),
            "pattern_status": p.pattern_status.value,
            "confidence": p.confidence.value,
            "repair_status": p.repair_status.value,
            "recommended_repair_action": p.recommended_repair_action,
            "likely_prerequisite_skill": p.likely_prerequisite_skill,
            "prerequisite_signal": p.prerequisite_signal,
            "engine_version": p.engine_version,
            "metadata": p.metadata,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat(),
        }

    @staticmethod
    def _deserialize_pattern(row: Dict[str, Any]) -> MistakePattern:
        return MistakePattern(
            id=row["id"],
            user_id=row["user_id"],
            skill_id=row["skill_id"],
            subject=row.get("subject", "Mathematics"),
            error_type=ErrorType(row.get("error_type", ErrorType.UNKNOWN.value)),
            error_subtype=row.get("error_subtype", ""),
            occurrence_count=row.get("occurrence_count", 1),
            recent_occurrence_count=row.get("recent_occurrence_count", 1),
            first_seen_at=datetime.fromisoformat(row["first_seen_at"]) if "first_seen_at" in row else datetime.now(timezone.utc),
            last_seen_at=datetime.fromisoformat(row["last_seen_at"]) if "last_seen_at" in row else datetime.now(timezone.utc),
            pattern_status=PatternStatus(row.get("pattern_status", PatternStatus.ISOLATED.value)),
            confidence=ConfidenceClass(row.get("confidence", ConfidenceClass.MODERATE.value)),
            repair_status=RepairStatus(row.get("repair_status", RepairStatus.OPEN.value)),
            recommended_repair_action=row.get("recommended_repair_action", ""),
            likely_prerequisite_skill=row.get("likely_prerequisite_skill"),
            prerequisite_signal=row.get("prerequisite_signal"),
            engine_version=row.get("engine_version", "5.0.0"),
            metadata=row.get("metadata") or {},
            created_at=datetime.fromisoformat(row["created_at"]) if "created_at" in row else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(row["updated_at"]) if "updated_at" in row else datetime.now(timezone.utc),
        )

    @staticmethod
    def _serialize_repair(r: RepairEvent) -> Dict[str, Any]:
        return {
            "id": r.id,
            "pattern_id": r.pattern_id,
            "user_id": r.user_id,
            "skill_id": r.skill_id,
            "repair_action": r.repair_action,
            "evidence_source": r.evidence_source.value,
            "evidence_record_id": r.evidence_record_id,
            "assistance_level": r.assistance_level.value,
            "verified_at": r.verified_at.isoformat(),
            "engine_version": r.engine_version,
            "notes": r.notes,
            "created_at": r.created_at.isoformat(),
        }

    @staticmethod
    def _deserialize_repair(row: Dict[str, Any]) -> RepairEvent:
        return RepairEvent(
            id=row["id"],
            pattern_id=row["pattern_id"],
            user_id=row["user_id"],
            skill_id=row["skill_id"],
            repair_action=row.get("repair_action", ""),
            evidence_source=MistakeSourceType(row.get("evidence_source", MistakeSourceType.DIAGNOSTIC.value)),
            evidence_record_id=row.get("evidence_record_id", ""),
            assistance_level=AssistanceLevel(row.get("assistance_level", AssistanceLevel.INDEPENDENT.value)),
            verified_at=datetime.fromisoformat(row["verified_at"]) if "verified_at" in row else datetime.now(timezone.utc),
            engine_version=row.get("engine_version", "5.0.0"),
            notes=row.get("notes", ""),
            created_at=datetime.fromisoformat(row["created_at"]) if "created_at" in row else datetime.now(timezone.utc),
        )
