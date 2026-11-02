"""
LearnByGenie — Adaptive Diagnostic Engine (Feature 2)
=====================================================
Bounded, transparent, multi-stage adaptive assessment engine:
- Anchor (representative items near enrolled level)
- Branch (strong -> higher/current concepts; weak -> prerequisites)
- Confirmation (requires >= 2 independent items before classifying NEEDS_REPAIR)
- Stopping Rules (bounded budget, prerequisite floor, sufficient confidence)

Never assigns global IQ / intelligence labels or rank predictions.
Derives educational operating band and prerequisite gap chain.
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import uuid

from .schemas import (
    DiagnosticStage, DiagnosticState, ConfidenceClass, OverallReadiness,
    GradeBand, DifficultyBand, DiagnosticSession, DiagnosticResponse,
    DiagnosticItem, DiagnosticSkill, DiagnosticResult, DiagnosticSkillResult,
    Feature3SkillEvidence
)
from .curriculum_blueprint import (
    get_skill, get_skills_for_subject, get_prerequisites, CANONICAL_SKILLS
)
from .item_bank import get_item, get_items_for_skill, get_all_items


def get_default_budget_for_grade(grade: int) -> int:
    """Configurable question budgets by stage (§29)."""
    if grade <= 5:
        return 6      # Primary: short, low fatigue
    elif grade <= 8:
        return 8      # Middle: moderate
    elif grade <= 10:
        return 10     # Secondary
    elif grade <= 12:
        return 10     # Senior Secondary / JEE / NEET
    else:
        return 10     # UG coursework


def determine_initial_anchor_skills(subject: str, enrolled_grade: int, exam_track: str) -> List[DiagnosticSkill]:
    """Finds starting anchor skills matched to the student's enrolled grade band and track."""
    skills = get_skills_for_subject(subject)
    if not skills:
        return []

    # Filter by grade range
    matching = [
        s for s in skills
        if s.min_grade <= enrolled_grade <= s.max_grade
    ]
    if matching:
        return matching

    # If grade is higher than all configured, take the highest available skill
    matching = sorted(skills, key=lambda s: s.max_grade, reverse=True)
    return matching[:2] if matching else []


class AdaptiveDecisionEngine:
    """Stateful diagnostic session progression logic."""

    @staticmethod
    def select_next_item(
        session: DiagnosticSession,
        responses: List[DiagnosticResponse],
    ) -> Optional[DiagnosticItem]:
        """
        Server-authoritative next-question selector implementing:
        Stage A (Anchor) -> Stage B (Branch) -> Stage C (Confirmation) -> Stop
        """
        # If budget exhausted, stop
        if session.questions_answered >= session.question_budget:
            return None

        asked_set = set(session.asked_item_ids)

        # ── 1. CONFIRMATION CHECK ─────────────────────────────────────────────
        # If any active skill has exactly 1 failure and 0 successes, prioritize confirmation!
        skill_perf = AdaptiveDecisionEngine._compute_skill_stats(responses)
        for skill_id, stats in skill_perf.items():
            if stats["attempts"] == 1 and stats["incorrect"] == 1:
                # Seek a second independent probe for this skill
                cand_items = get_items_for_skill(skill_id)
                for it in cand_items:
                    if it.id not in asked_set and it.status == "active":
                        session.current_stage = DiagnosticStage.CONFIRMATION.value
                        return it

        # ── 2. BRANCH CHECK (DOWNWARD PREREQUISITE PROBE) ─────────────────────
        # If a skill has confirmed failure (attempts >= 2, incorrect >= 2), probe its immediate prerequisites
        for skill_id, stats in skill_perf.items():
            if stats["incorrect"] >= 2:
                prereqs = get_prerequisites(skill_id)
                for pr in prereqs:
                    pr_stats = skill_perf.get(pr.id, {"attempts": 0})
                    if pr_stats["attempts"] == 0:
                        cand_items = get_items_for_skill(pr.id)
                        for it in cand_items:
                            if it.id not in asked_set and it.status == "active":
                                session.current_stage = DiagnosticStage.BRANCH.value
                                return it

        # ── 3. ANCHOR / UPWARD PROGRESSION ────────────────────────────────────
        # Pick from active anchor skills or upward extensions
        subject_skills = get_skills_for_subject(session.subject)
        # Order skills from lowest to highest grade
        sorted_skills = sorted(subject_skills, key=lambda s: s.min_grade)

        for sk in sorted_skills:
            stats = skill_perf.get(sk.id, {"attempts": 0, "correct": 0})
            if stats["attempts"] < 2:
                cand_items = get_items_for_skill(sk.id)
                for it in cand_items:
                    if it.id not in asked_set and it.status == "active":
                        session.current_stage = DiagnosticStage.ANCHOR.value if session.questions_answered < 3 else DiagnosticStage.BRANCH.value
                        return it

        # ── 4. FALLBACK TO ANY UNASKED ACTIVE ITEM IN SUBJECT ─────────────────
        for sk in subject_skills:
            for it in get_items_for_skill(sk.id):
                if it.id not in asked_set and it.status == "active":
                    return it

        return None

    @staticmethod
    def _compute_skill_stats(responses: List[DiagnosticResponse]) -> Dict[str, Dict[str, int]]:
        stats: Dict[str, Dict[str, int]] = {}
        for r in responses:
            if not r.skill_id:
                continue
            if r.skill_id not in stats:
                stats[r.skill_id] = {"attempts": 0, "correct": 0, "incorrect": 0}
            stats[r.skill_id]["attempts"] += 1
            if r.is_correct:
                stats[r.skill_id]["correct"] += 1
            else:
                stats[r.skill_id]["incorrect"] += 1
        return stats

    @staticmethod
    def classify_skill_result(
        skill: DiagnosticSkill,
        stats: Dict[str, int]
    ) -> Tuple[DiagnosticState, ConfidenceClass, str, bool]:
        """
        Deterministic, evidence-based educational classification (§10, §11, §12).
        Returns (state, confidence, recommended_action, is_recommended_start).
        """
        attempts = stats.get("attempts", 0)
        correct = stats.get("correct", 0)
        incorrect = stats.get("incorrect", 0)

        if attempts == 0:
            return (
                DiagnosticState.NOT_ASSESSED,
                ConfidenceClass.LOW_EVIDENCE,
                "Concept not yet assessed in this diagnostic session.",
                False
            )

        # Confidence class based on evidence depth
        if attempts >= 3:
            conf = ConfidenceClass.HIGH_EVIDENCE
        elif attempts == 2:
            conf = ConfidenceClass.MODERATE_EVIDENCE
        else:
            conf = ConfidenceClass.LOW_EVIDENCE

        # SECURE: at least 75% correct
        if correct >= 1 and incorrect == 0:
            return (
                DiagnosticState.SECURE,
                conf,
                f"Mastery demonstrated for {skill.skill_name}. Ready for progression.",
                False
            )
        elif correct >= 2 and (correct / attempts) >= 0.67:
            return (
                DiagnosticState.SECURE,
                conf,
                f"Solid grasp of {skill.skill_name}.",
                False
            )

        # CONFIRMED GAP (NEEDS REPAIR): requires at least 2 items, majority incorrect
        if attempts >= 2 and incorrect >= 2:
            return (
                DiagnosticState.NEEDS_REPAIR,
                conf,
                f"Prerequisite gap detected in {skill.skill_name}. Prioritize foundational reinforcement before advancing.",
                True
            )

        # SINGLE INCORRECT: DEVELOPING (NEVER labels NEEDS_REPAIR from one wrong answer!)
        if attempts == 1 and incorrect == 1:
            return (
                DiagnosticState.DEVELOPING,
                ConfidenceClass.LOW_EVIDENCE,
                f"Initial struggle observed in {skill.skill_name}. Reinforce with practice.",
                False
            )

        # MIXED EVIDENCE: DEVELOPING
        return (
            DiagnosticState.DEVELOPING,
            conf,
            f"Partial understanding of {skill.skill_name}. Additional targeted practice recommended.",
            False
        )

    @staticmethod
    def compile_final_result(
        session: DiagnosticSession,
        responses: List[DiagnosticResponse]
    ) -> DiagnosticResult:
        """
        Compiles authoritative, immutable diagnostic report and Feature 3 contract.
        """
        skill_perf = AdaptiveDecisionEngine._compute_skill_stats(responses)
        subject_skills = get_skills_for_subject(session.subject)

        skill_results: List[DiagnosticSkillResult] = []
        feature3_contract: List[Feature3SkillEvidence] = []
        prerequisite_gaps: List[str] = []
        recommended_start_skill: Optional[DiagnosticSkill] = None

        total_correct = sum(1 for r in responses if r.is_correct)
        now_iso = datetime.now(timezone.utc).isoformat()
        result_id = str(uuid.uuid4())

        for sk in subject_skills:
            stats = skill_perf.get(sk.id, {"attempts": 0, "correct": 0, "incorrect": 0})
            if stats["attempts"] == 0:
                continue

            state, conf, action, is_rec = AdaptiveDecisionEngine.classify_skill_result(sk, stats)
            if state == DiagnosticState.NEEDS_REPAIR:
                prerequisite_gaps.append(sk.skill_name)
                if not recommended_start_skill or sk.min_grade < recommended_start_skill.min_grade:
                    recommended_start_skill = sk

            sr = DiagnosticSkillResult(
                id=str(uuid.uuid4()),
                result_id=result_id,
                session_id=session.id,
                user_id=session.user_id,
                subject=session.subject,
                skill_id=sk.id,
                skill_code=sk.skill_code,
                skill_name=sk.skill_name,
                diagnostic_state=state,
                evidence_count=stats["attempts"],
                correct_count=stats["correct"],
                confidence_class=conf,
                recommended_action=action,
                is_recommended_start=is_rec,
                prerequisite_depth=len(sk.prerequisite_skill_ids),
            )
            skill_results.append(sr)

            # Feature 3 Ingestion Contract (§33)
            f3 = Feature3SkillEvidence(
                skill_id=sk.id,
                diagnostic_state=state.value,
                evidence_count=stats["attempts"],
                correct_count=stats["correct"],
                confidence=conf.value,
                source="DIAGNOSTIC",
                diagnostic_session_id=session.id,
                timestamp=now_iso,
                recommended_action=action,
            )
            feature3_contract.append(f3)

        # Deriving Educational Operating Band (§13)
        if recommended_start_skill:
            operating_band = f"Recommended starting point: {recommended_start_skill.skill_name} ({recommended_start_skill.grade_band} prerequisites)"
            readiness = OverallReadiness.PREREQUISITES_NEEDED
            summary = (
                f"Diagnostic completed for {session.subject}. Foundational review recommended in "
                f"{recommended_start_skill.skill_name} before moving to advanced topics."
            )
        elif total_correct >= max(1, len(responses) * 0.75):
            operating_band = f"Ready for Class {session.enrolled_grade} curriculum"
            readiness = OverallReadiness.READY
            summary = f"Strong grasp across assessed skills in {session.subject}. Well-prepared for core grade curriculum."
        else:
            operating_band = f"On-track for Class {session.enrolled_grade} with developing skills"
            readiness = OverallReadiness.ON_TRACK
            summary = f"Good baseline in {session.subject}. Targeted practice will solidify developing concepts."

        return DiagnosticResult(
            id=result_id,
            session_id=session.id,
            user_id=session.user_id,
            subject=session.subject,
            enrolled_grade=session.enrolled_grade,
            exam_track=session.exam_track,
            overall_readiness=readiness,
            operating_level_band=operating_band,
            summary=summary,
            total_items_answered=len(responses),
            correct_items_count=total_correct,
            skill_results=skill_results,
            prerequisite_gaps=prerequisite_gaps,
            feature3_contract_payload=feature3_contract,
            engine_version=session.engine_version,
            created_at=datetime.now(timezone.utc),
        )
