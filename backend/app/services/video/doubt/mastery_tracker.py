"""
LearnByGenie AI Video Teacher V2.1 — Learner Mastery Tracker & Pedagogical Adaptation
===================================================================================
Tracks concept-level learner state with strict evidence requirements (Decision #1):
- Video playback: NOT_SEEN -> INTRODUCED -> PARTIALLY_UNDERSTOOD (NEVER UNDERSTOOD or MASTERED)
- Learner doubt: transitions to CONFUSED
- Prerequisite deficit: transitions to PREREQUISITE_GAP
- First successful check: transitions to UNDERSTOOD
- MASTERED requires AT LEAST TWO independent positive signals:
    - correct concept check
    - correct application / transfer check
    - successful later recall check
    - successful resolution of a previously confused concept

Throttled event-driven playback synchronization (Decision #2).
Adaptive future explanations driven by mastery profile (Decision #8).
"""
import time
from typing import Dict, List, Optional, Tuple, Any
from ..schemas import (
    LearnerMasteryState, ConceptMasteryRecord, LearnerMasteryProfile,
    VideoKnowledgePackage, ExplanationStrategy, ConfusionType
)
from ..persistence import load_file_json, save_file_json, sync_mastery_to_supabase_background
from app.core.logging import logger


# In-memory store for active session mastery profiles: user_id -> Dict[lesson_id, LearnerMasteryProfile]
MASTERY_STORE: Dict[str, Dict[str, LearnerMasteryProfile]] = {}


def _load_persisted_profiles():
    raw = load_file_json("mastery_store.json", default={})
    if isinstance(raw, dict):
        for uid, lessons in raw.items():
            if uid not in MASTERY_STORE:
                MASTERY_STORE[uid] = {}
            if isinstance(lessons, dict):
                for lid, pdata in lessons.items():
                    try:
                        MASTERY_STORE[uid][lid] = LearnerMasteryProfile.model_validate(pdata)
                    except Exception as e:
                        logger.debug(f"[MasteryTracker] Skipped profile {uid}/{lid}: {e}")

_load_persisted_profiles()


def _persist_profile(profile: LearnerMasteryProfile):
    try:
        if profile.user_id not in MASTERY_STORE:
            MASTERY_STORE[profile.user_id] = {}
        MASTERY_STORE[profile.user_id][profile.lesson_id] = profile
        serialized = {
            u: {l: p.model_dump() for l, p in lessons.items()}
            for u, lessons in MASTERY_STORE.items()
        }
        save_file_json("mastery_store.json", serialized)
        sync_mastery_to_supabase_background(
            profile.user_id, profile.lesson_id, profile.model_dump(), profile.last_active_timestamp
        )
    except Exception as e:
        logger.warning(f"[MasteryTracker] Persistence error: {e}")


class LearnerMasteryTracker:
    """Manages evidence-based concept mastery tracking and pedagogical adaptations."""

    @classmethod
    def clear_profiles(cls):
        """Clears all in-memory and persisted mastery profiles (useful for test isolation)."""
        MASTERY_STORE.clear()
        save_file_json("mastery_store.json", {})

    @classmethod
    def reset_profile(cls, user_id: str, lesson_id: Optional[str] = None):
        """Resets profile for a specific user or user+lesson."""
        if user_id in MASTERY_STORE:
            if lesson_id:
                MASTERY_STORE[user_id].pop(lesson_id, None)
            else:
                MASTERY_STORE.pop(user_id, None)
            serialized = {
                u: {l: p.model_dump() for l, p in lessons.items()}
                for u, lessons in MASTERY_STORE.items()
            }
            save_file_json("mastery_store.json", serialized)

    @classmethod
    def get_or_create_profile(cls, user_id: str, lesson_id: str) -> LearnerMasteryProfile:
        """Retrieves or initializes a learner mastery profile for a given user and lesson."""
        if user_id not in MASTERY_STORE:
            MASTERY_STORE[user_id] = {}
        if lesson_id not in MASTERY_STORE[user_id]:
            MASTERY_STORE[user_id][lesson_id] = LearnerMasteryProfile(
                user_id=user_id,
                lesson_id=lesson_id,
                concepts={},
                last_active_timestamp=0.0,
                last_sync_timestamp=time.time(),
            )
        return MASTERY_STORE[user_id][lesson_id]

    @classmethod
    def sync_playback_progress(
        cls,
        user_id: str,
        lesson_id: str,
        timestamp: float,
        knowledge_pack: VideoKnowledgePackage,
        event_type: str = "throttled_interval",  # throttled_interval, scene_boundary, pause, seek, complete
    ) -> LearnerMasteryProfile:
        """
        Event-driven playback sync (Decision #2).
        Enforces Decision #1: Playback ONLY transitions NOT_SEEN -> INTRODUCED -> PARTIALLY_UNDERSTOOD.
        Never directly grants UNDERSTOOD or MASTERED.
        """
        profile = cls.get_or_create_profile(user_id, lesson_id)
        profile.last_active_timestamp = timestamp
        profile.last_sync_timestamp = time.time()

        for scene in knowledge_pack.scenes:
            cid = scene.concept_id or scene.concept_name or scene.scene_id
            cname = scene.concept_name or scene.teaching_goal or cid

            if cid not in profile.concepts:
                profile.concepts[cid] = ConceptMasteryRecord(
                    concept_id=cid,
                    concept_name=cname,
                    state=LearnerMasteryState.NOT_SEEN,
                )

            record = profile.concepts[cid]

            # If user has watched past the scene start
            if timestamp >= scene.timestamp_start:
                scene_dur = max(1.0, scene.timestamp_end - scene.timestamp_start)
                scene_watch_progress = min(1.0, max(0.0, (timestamp - scene.timestamp_start) / scene_dur))
                record.watch_progress_pct = max(record.watch_progress_pct, scene_watch_progress)

                # State transition rules based purely on playback
                if record.state == LearnerMasteryState.NOT_SEEN:
                    record.state = LearnerMasteryState.INTRODUCED
                elif record.state == LearnerMasteryState.INTRODUCED and scene_watch_progress >= 0.8:
                    record.state = LearnerMasteryState.PARTIALLY_UNDERSTOOD

                # If student was previously CONFUSED or in PREREQUISITE_GAP, re-watching does NOT erase it
                record.last_interaction = time.time()

        _persist_profile(profile)
        return profile

    @classmethod
    def record_doubt_event(
        cls,
        user_id: str,
        lesson_id: str,
        concept_id: str,
        concept_name: str,
        confusion_type: ConfusionType,
        strategy_used: ExplanationStrategy,
        has_prerequisite_gap: bool = False,
        gap_concept: Optional[str] = None,
    ) -> ConceptMasteryRecord:
        """
        Updates concept state when learner raises a doubt:
        Transitions concept to CONFUSED or PREREQUISITE_GAP.
        """
        profile = cls.get_or_create_profile(user_id, lesson_id)

        if concept_id not in profile.concepts:
            profile.concepts[concept_id] = ConceptMasteryRecord(
                concept_id=concept_id,
                concept_name=concept_name,
                state=LearnerMasteryState.INTRODUCED,
            )

        record = profile.concepts[concept_id]
        record.confusion_count += 1
        record.strategies_attempted.append(strategy_used.value)
        record.last_strategy = strategy_used.value
        record.last_interaction = time.time()

        if has_prerequisite_gap:
            record.state = LearnerMasteryState.PREREQUISITE_GAP
            record.prerequisite_gap_count += 1
            if gap_concept:
                gap_id = f"prereq_{gap_concept.lower().replace(' ', '_')}"
                if gap_id not in profile.concepts:
                    profile.concepts[gap_id] = ConceptMasteryRecord(
                        concept_id=gap_id,
                        concept_name=gap_concept,
                        state=LearnerMasteryState.PREREQUISITE_GAP,
                        prerequisite_gap_count=1,
                    )
        else:
            record.state = LearnerMasteryState.CONFUSED

        _persist_profile(profile)
        return record

    @classmethod
    def record_mastery_check_result(
        cls,
        user_id: str,
        lesson_id: str,
        concept_id: str,
        is_correct: bool,
        evidence_tag: str = "concept_check",
    ) -> Tuple[ConceptMasteryRecord, str]:
        """
        Records results of an interactive mastery check (Decision #1):
        - Correct first answer -> UNDERSTOOD (1 evidence signal)
        - Correct second answer / transfer / resolution -> MASTERED (>= 2 independent signals)
        - Incorrect answer -> CONFUSED
        """
        profile = cls.get_or_create_profile(user_id, lesson_id)
        if concept_id not in profile.concepts:
            profile.concepts[concept_id] = ConceptMasteryRecord(
                concept_id=concept_id,
                concept_name=concept_id,
                state=LearnerMasteryState.INTRODUCED,
            )

        record = profile.concepts[concept_id]
        record.last_interaction = time.time()

        if is_correct:
            record.successful_checks += 1
            if evidence_tag not in record.evidence_for_mastery:
                record.evidence_for_mastery.append(evidence_tag)

            evidence_count = len(record.evidence_for_mastery)

            # Check if this resolved a prior confusion
            if record.state in (LearnerMasteryState.CONFUSED, LearnerMasteryState.PREREQUISITE_GAP):
                record.evidence_for_mastery.append("resolved_prior_confusion")
                evidence_count += 1

            if evidence_count >= 2:
                record.state = LearnerMasteryState.MASTERED
                msg = f"Mastery verified! Concept '{record.concept_name}' upgraded to MASTERED ({evidence_count} evidence signals)."
            else:
                record.state = LearnerMasteryState.UNDERSTOOD
                msg = f"Correct! Concept '{record.concept_name}' upgraded to UNDERSTOOD (1 positive signal; needs 2 for MASTERED)."
        else:
            record.failed_checks += 1
            record.state = LearnerMasteryState.CONFUSED
            msg = f"Mastery check incorrect. Concept '{record.concept_name}' marked as CONFUSED. Targeted remedy queued."

        _persist_profile(profile)
        return record, msg

    @classmethod
    def get_adaptive_explanation_guidance(
        cls,
        user_id: str,
        lesson_id: str,
        concept_id: str,
    ) -> Dict[str, Any]:
        """
        Inspects the learner's mastery profile to adapt future teaching (Decision #8):
        - Repeated confusion: reduce abstraction, slow down, add concrete second example.
        - Previous VISUAL failed: do NOT repeat VISUAL.
        - Prerequisite gap: inject PREREQUISITE_REPAIR.
        - Existing mastery: avoid reteaching basics.
        """
        profile = cls.get_or_create_profile(user_id, lesson_id)
        record = profile.concepts.get(concept_id)

        if not record:
            return {
                "reduce_abstraction": False,
                "avoid_strategies": [],
                "recommended_strategy": ExplanationStrategy.SIMPLE,
                "inject_prerequisite_repair": False,
                "skip_basics": False,
            }

        avoid = list(set(record.strategies_attempted))
        reduce_abs = record.confusion_count >= 2 or record.failed_checks >= 1
        has_gap = record.state == LearnerMasteryState.PREREQUISITE_GAP
        is_mastered = record.state == LearnerMasteryState.MASTERED

        recommended = ExplanationStrategy.SIMPLE
        if has_gap:
            recommended = ExplanationStrategy.PREREQUISITE_REPAIR
        elif reduce_abs:
            if ExplanationStrategy.REAL_WORLD_ANALOGY.value not in avoid:
                recommended = ExplanationStrategy.REAL_WORLD_ANALOGY
            elif ExplanationStrategy.STEP_BY_STEP.value not in avoid:
                recommended = ExplanationStrategy.STEP_BY_STEP
            else:
                recommended = ExplanationStrategy.SECOND_EXAMPLE

        return {
            "reduce_abstraction": reduce_abs,
            "avoid_strategies": avoid,
            "recommended_strategy": recommended,
            "inject_prerequisite_repair": has_gap,
            "skip_basics": is_mastered,
            "confusion_count": record.confusion_count,
            "successful_checks": record.successful_checks,
            "evidence_signals": record.evidence_for_mastery,
        }
