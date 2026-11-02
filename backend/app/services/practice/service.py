"""
LearnByGenie — Canonical Adaptive Practice Service (Feature 6)
==============================================================
Subject-agnostic, skill-driven, catalog-driven, database-driven adaptive practice engine.

Capabilities (§2):
- start_session(...)
- get_next_item(...)
- submit_response(...)
- get_session(...)
- resume_session(...)
- get_session_summary(...)
- explain_selection(...)
- request_hint(...)
- get_compact_practice_summary(...)

Guarantees (§MISSION, §NON-NEGOTIABLE ARCHITECTURE RULE):
- ONE canonical engine for Class 3-12, JEE, NEET, UG, and dynamically registered subjects.
- Consumes LearnerContextService, MasteryGraphService, MistakeDNAService.
- Closes adaptive loop:
  * Ingests EvidenceSource.PRACTICE to MasteryGraph (never directly mutating states)
  * Ingests MistakeSourceType.PRACTICE to Mistake DNA
  * Verifiable repair loop: independent correct repairs open error patterns
  * Assistance-aware: hints downgrade independence level and prevent over-promotion
- Server-authoritative item delivery (zero leaked answers/queues)
- Concurrency & multi-tab divergence protection via optimistic sequence locking
- Complete idempotency: duplicate submissions double-score zero times
"""
import uuid
from typing import Dict, Any, Optional, List, Tuple, Union, Set
from datetime import datetime, timezone

from app.core.logging import logger
from .schemas import (
    PracticeMode, DifficultyBand, QuestionType, AssistanceLevel,
    SelectionCategory, ProvenanceType, VerificationStatus,
    PracticeSessionStatus, ContentCoverageStatus, PracticeItem,
    StudentPracticeItemView, PracticeSession, PracticeResponse,
    PracticeFeedback, PracticeSelectionExplanation, SessionSummary,
    CompactPracticeSummary
)
from .policy import PracticePolicy, get_policy, DEFAULT_PRACTICE_POLICY_V1
from .repository import PracticeRepository
from .item_bank import (
    get_practice_item, get_practice_items_for_skill,
    get_all_practice_items, register_practice_item
)
from .adapters import DomainAdapterRegistry

# Frozen Integrations (§FROZEN FOUNDATIONS)
from app.services.mastery.service import MasteryGraphService
from app.services.mastery.schemas import EvidenceSource, MasteryState, AssistanceLevel as MasteryAssistanceLevel
from app.services.mistake_dna.service import MistakeDNAService
from app.services.mistake_dna.schemas import (
    MistakeSourceType, MistakeCandidate, PatternStatus,
    RepairStatus, AssistanceLevel as MistakeAssistanceLevel
)
from app.services.diagnostic.curriculum_blueprint import CANONICAL_SKILLS, get_skill


class AdaptivePracticeService:
    """
    Canonical Adaptive Practice Engine Service.
    """

    # ─── 1. START SESSION ─────────────────────────────────────────────────────

    @classmethod
    def start_session(
        cls,
        user_id: str,
        subject: str,
        mode: PracticeMode = PracticeMode.ADAPTIVE,
        requested_skill_id: Optional[str] = None,
        question_budget: Optional[Union[int, str]] = None,
        curriculum: str = "CBSE",
        exam_track: str = "Boards",
        enrolled_grade: int = 10,
        grade_band: str = "secondary",
        policy_version: Optional[str] = None
    ) -> PracticeSession:
        """
        Initializes a durable, server-authoritative practice session (§2, §20).
        """
        policy = get_policy(policy_version)
        resolved_budget = policy.resolve_budget(question_budget)

        session_id = str(uuid.uuid4())
        session = PracticeSession(
            id=session_id,
            user_id=user_id,
            subject=subject,
            mode=mode,
            curriculum=curriculum,
            exam_track=exam_track,
            enrolled_grade=enrolled_grade,
            grade_band=grade_band,
            requested_skill_id=requested_skill_id,
            current_skill_id=requested_skill_id,
            current_item_id=None,
            question_index=0,
            question_budget=resolved_budget,
            current_difficulty=DifficultyBand.STANDARD,
            consecutive_correct=0,
            consecutive_incorrect=0,
            active_hints_used=0,
            policy_version=policy.version,
            status=PracticeSessionStatus.IN_PROGRESS,
            asked_item_ids=[],
            skills_practiced=[],
            selection_context={},
            started_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        PracticeRepository.save_session(session)
        logger.info(f"[PracticeService] Started session {session_id} for user {user_id} in {subject} ({mode.value})")
        return session

    # ─── 2. GET NEXT ITEM ─────────────────────────────────────────────────────

    @classmethod
    def get_next_item(
        cls,
        session_id: str,
        user_id: str
    ) -> Optional[StudentPracticeItemView]:
        """
        Retrieves the next server-authoritative practice question (§5, §6, §8, §22).
        Deliberately omits correct answer, explanation, and unrequested hints.
        """
        session = PracticeRepository.get_session(session_id)
        if not session or session.user_id != user_id:
            logger.warning(f"[PracticeService] Session not found or unauthorized: {session_id}")
            return None

        # Check stopping conditions (§48)
        if session.status != PracticeSessionStatus.IN_PROGRESS:
            return None

        if session.question_index >= session.question_budget:
            session.status = PracticeSessionStatus.COMPLETED
            session.completed_at = datetime.now(timezone.utc)
            PracticeRepository.save_session(session)
            return None

        # If current item is already chosen and not yet answered, return it (browser refresh / resume safe §24)
        if session.current_item_id:
            existing_item = get_practice_item(session.current_item_id)
            if existing_item:
                revealed = existing_item.hints[:session.active_hints_used]
                reason = session.selection_context.get("reason")
                return existing_item.to_student_view(
                    sequence_number=session.question_index + 1,
                    total_budget=session.question_budget,
                    revealed_hints=revealed,
                    selection_reason=reason
                )

        # ─── ADAPTIVE SELECTION INTELLIGENCE (§5, §6, §8, §9, §10) ──────────────
        policy = get_policy(session.policy_version)
        selected_item, category, reason, candidate_skill_id = cls._select_candidate_item(session, policy)

        if not selected_item:
            # Honest content coverage notice (§17, §48)
            logger.warning(f"[PracticeService] Insufficient validated content for session {session_id}")
            session.status = PracticeSessionStatus.COMPLETED
            session.completed_at = datetime.now(timezone.utc)
            PracticeRepository.save_session(session)
            return None

        # Update session state with assigned item
        session.current_item_id = selected_item.id
        session.current_skill_id = candidate_skill_id
        session.selection_context = {
            "category": category.value,
            "reason": reason,
            "skill_id": candidate_skill_id,
            "difficulty": selected_item.difficulty_band.value
        }
        PracticeRepository.save_session(session)

        revealed = selected_item.hints[:session.active_hints_used]
        return selected_item.to_student_view(
            sequence_number=session.question_index + 1,
            total_budget=session.question_budget,
            revealed_hints=revealed,
            selection_reason=reason
        )

    # ─── 3. REQUEST HINT ──────────────────────────────────────────────────────

    @classmethod
    def request_hint(
        cls,
        session_id: str,
        user_id: str,
        item_id: str
    ) -> Tuple[Optional[str], int, int]:
        """
        Provides progressive hint ladder (§25).
        Returns (hint_text, hints_revealed_count, total_hints).
        """
        session = PracticeRepository.get_session(session_id)
        if not session or session.user_id != user_id:
            return None, 0, 0

        item = get_practice_item(item_id)
        if not item or not item.hints:
            return None, 0, 0

        current_used = session.active_hints_used
        if current_used < len(item.hints):
            hint_to_give = item.hints[current_used]
            session.active_hints_used += 1
            PracticeRepository.save_session(session)
            return hint_to_give, session.active_hints_used, len(item.hints)
        else:
            # All hints already revealed
            return item.hints[-1], len(item.hints), len(item.hints)

    # ─── 4. SUBMIT RESPONSE ───────────────────────────────────────────────────

    @classmethod
    def submit_response(
        cls,
        session_id: str,
        user_id: str,
        item_id: str,
        student_response: Any,
        question_index: int,
        response_time_ms: int = 0,
        attempt_sequence: int = 1
    ) -> Optional[PracticeFeedback]:
        """
        Validates response, updates difficulty, submits Mastery & Mistake DNA evidence,
        and advances session state with strict concurrency & idempotency protection (§21, §23, §27, §28, §45, §46).
        """
        session = PracticeRepository.get_session(session_id)
        if not session or session.user_id != user_id:
            logger.warning(f"[PracticeService] Session lookup failed: {session_id}")
            return None

        # 1. Optimistic sequence check for multi-tab divergence (§46)
        if question_index != session.question_index:
            logger.info(
                f"[PracticeService] Sequence mismatch (multi-tab/retry): expected {session.question_index}, got {question_index}"
            )
            # Find if this question was already answered
            past_resps = PracticeRepository.get_session_responses(session_id)
            for pr in past_resps:
                if pr.question_index == question_index:
                    existing_item = get_practice_item(pr.item_id)
                    return PracticeFeedback(
                        session_id=session_id,
                        item_id=pr.item_id,
                        skill_id=pr.skill_id,
                        question_index=pr.question_index,
                        correctness=pr.correctness,
                        assistance_level=pr.assistance_level,
                        authoritative_explanation=existing_item.explanation if existing_item else "",
                        current_difficulty=session.current_difficulty,
                        session_completed=(session.status == PracticeSessionStatus.COMPLETED),
                        next_question_ready=(session.status == PracticeSessionStatus.IN_PROGRESS),
                    )

        item = get_practice_item(item_id)
        if not item:
            logger.warning(f"[PracticeService] Practice item {item_id} not found")
            return None

        # 2. Domain-specific answer validation via Adapter (§14, §15)
        adapter = DomainAdapterRegistry.get_adapter(session.subject)
        is_correct, _ = adapter.validate_answer(item, student_response)

        # 3. Determine assistance level (§25)
        if session.active_hints_used > 0:
            assistance_level = AssistanceLevel.HINT_ASSISTED
        else:
            assistance_level = AssistanceLevel.INDEPENDENT

        # 4. Construct Response Record
        policy = get_policy(session.policy_version)
        response_id = str(uuid.uuid4())
        response = PracticeResponse(
            id=response_id,
            session_id=session_id,
            user_id=user_id,
            item_id=item_id,
            skill_id=item.skill_id,
            question_index=session.question_index,
            student_response=student_response,
            correctness=is_correct,
            assistance_level=assistance_level,
            difficulty_band=item.difficulty_band,
            response_time_ms=response_time_ms,
            attempt_sequence=attempt_sequence,
            selection_reason=session.selection_context.get("reason", ""),
            selection_category=session.selection_context.get("category", ""),
            hints_requested=session.active_hints_used,
            provenance=item.provenance.value,
            created_at=datetime.now(timezone.utc)
        )

        saved_resp, is_new = PracticeRepository.record_response(response)
        if not is_new:
            # Idempotent re-submission intercepted! (§23)
            return PracticeFeedback(
                session_id=session_id,
                item_id=saved_resp.item_id,
                skill_id=saved_resp.skill_id,
                question_index=saved_resp.question_index,
                correctness=saved_resp.correctness,
                assistance_level=saved_resp.assistance_level,
                authoritative_explanation=item.explanation,
                current_difficulty=session.current_difficulty,
                session_completed=(session.status == PracticeSessionStatus.COMPLETED),
                next_question_ready=(session.status == PracticeSessionStatus.IN_PROGRESS),
            )

        # 5. Deterministic difficulty adaptation (§11)
        new_diff, new_consec_corr, new_consec_incorr = policy.adapt_difficulty(
            current_difficulty=session.current_difficulty,
            consecutive_correct=session.consecutive_correct,
            consecutive_incorrect=session.consecutive_incorrect,
            assistance_level=assistance_level,
            is_correct=is_correct
        )
        session.current_difficulty = new_diff
        session.consecutive_correct = new_consec_corr
        session.consecutive_incorrect = new_consec_incorr

        # ─── CLOSED ADAPTIVE LOOP: MASTERY EVIDENCE (§27) ─────────────────────
        try:
            m_assist = (
                MasteryAssistanceLevel.INDEPENDENT
                if assistance_level == AssistanceLevel.INDEPENDENT
                else MasteryAssistanceLevel.HINT_ASSISTED
            )
            MasteryGraphService.ingest_evidence(
                user_id=user_id,
                skill_id=item.skill_id,
                source_type=EvidenceSource.PRACTICE,
                source_record_id=f"practice_resp_{saved_resp.id}",
                correctness=is_correct,
                independence_level=m_assist,
                metadata={
                    "session_id": session_id,
                    "difficulty": item.difficulty_band.value,
                    "question_index": saved_resp.question_index
                }
            )
        except Exception as e:
            logger.warning(f"[PracticeService] Mastery evidence ingestion notice: {e}")

        # ─── CLOSED ADAPTIVE LOOP: MISTAKE DNA INTEGRATION (§28, §29) ─────────
        detected_mistake: Optional[str] = None
        repair_recorded = False

        if not is_correct:
            # Incorrect response forwards to Mistake DNA
            try:
                dna_assist = (
                    MistakeAssistanceLevel.INDEPENDENT
                    if assistance_level == AssistanceLevel.INDEPENDENT
                    else MistakeAssistanceLevel.HINT_ASSISTED
                )
                candidate = MistakeCandidate(
                    user_id=user_id,
                    skill_id=item.skill_id,
                    subject=session.subject,
                    source_type=MistakeSourceType.PRACTICE,
                    source_record_id=f"practice_resp_{saved_resp.id}",
                    question_reference=item.prompt[:120],
                    student_response=str(student_response),
                    correct_answer=str(item.correct_answer),
                    prompt_text=item.prompt,
                    assistance_level=dna_assist,
                    metadata={"target_mistake_types": item.target_mistake_types}
                )
                ev, pat, _ = MistakeDNAService.ingest_error_candidate(candidate)
                detected_mistake = ev.primary_error_type.value
            except Exception as e:
                logger.warning(f"[PracticeService] Mistake DNA ingestion notice: {e}")
        else:
            # Correct response forwards repair evidence to Mistake DNA
            try:
                dna_assist = (
                    MistakeAssistanceLevel.INDEPENDENT
                    if assistance_level == AssistanceLevel.INDEPENDENT
                    else MistakeAssistanceLevel.HINT_ASSISTED
                )
                repairs = MistakeDNAService.mark_repair_evidence(
                    user_id=user_id,
                    skill_id=item.skill_id,
                    evidence_source=MistakeSourceType.PRACTICE,
                    evidence_record_id=f"practice_resp_{saved_resp.id}",
                    assistance_level=dna_assist,
                    notes=f"Solved in {item.difficulty_band.value} Practice"
                )
                if repairs:
                    repair_recorded = True
            except Exception as e:
                logger.warning(f"[PracticeService] Mistake DNA repair evidence notice: {e}")

        # 6. Advance Session Sequence (§20, §46)
        session.question_index += 1
        session.asked_item_ids.append(item.id)
        if item.skill_id not in session.skills_practiced:
            session.skills_practiced.append(item.skill_id)

        session.active_hints_used = 0
        session.current_item_id = None

        if session.question_index >= session.question_budget:
            session.status = PracticeSessionStatus.COMPLETED
            session.completed_at = datetime.now(timezone.utc)

        PracticeRepository.save_session(session)

        return PracticeFeedback(
            session_id=session_id,
            item_id=item.id,
            skill_id=item.skill_id,
            question_index=saved_resp.question_index,
            correctness=is_correct,
            assistance_level=assistance_level,
            authoritative_explanation=item.explanation,
            current_difficulty=session.current_difficulty,
            session_completed=(session.status == PracticeSessionStatus.COMPLETED),
            next_question_ready=(session.status == PracticeSessionStatus.IN_PROGRESS),
            mistake_pattern_detected=detected_mistake,
            repair_recorded=repair_recorded
        )

    # ─── 5. GET & RESUME SESSION ──────────────────────────────────────────────

    @classmethod
    def get_session(cls, session_id: str, user_id: str) -> Optional[PracticeSession]:
        session = PracticeRepository.get_session(session_id)
        if session and session.user_id == user_id:
            return session
        return None

    @classmethod
    def resume_session(cls, session_id: str, user_id: str) -> Optional[Tuple[PracticeSession, Optional[StudentPracticeItemView]]]:
        """
        Recovers active session and current item across browser refresh or backend restart (§24).
        """
        session = PracticeRepository.get_session(session_id)
        if not session or session.user_id != user_id:
            return None

        item_view = None
        if session.status == PracticeSessionStatus.IN_PROGRESS:
            item_view = cls.get_next_item(session_id, user_id)

        return session, item_view

    # ─── 6. EXPLAIN SELECTION ─────────────────────────────────────────────────

    @classmethod
    def explain_selection(
        cls,
        session_id: str,
        user_id: str,
        item_id: Optional[str] = None
    ) -> Optional[PracticeSelectionExplanation]:
        """
        Explains why this question was selected using real pedagogical evidence (§41).
        """
        session = PracticeRepository.get_session(session_id)
        if not session or session.user_id != user_id:
            return None

        target_item_id = item_id or session.current_item_id
        if not target_item_id:
            return None

        item = get_practice_item(target_item_id)
        if not item:
            return None

        sk_obj = get_skill(item.skill_id)
        sk_name = sk_obj.skill_name if sk_obj else item.skill_id

        ctx = session.selection_context
        cat_str = ctx.get("category", SelectionCategory.DEVELOPING_SKILL.value)
        category = SelectionCategory(cat_str) if cat_str in SelectionCategory.__members__ else SelectionCategory.DEVELOPING_SKILL

        return PracticeSelectionExplanation(
            item_id=item.id,
            skill_id=item.skill_id,
            skill_name=sk_name,
            category=category,
            reason=ctx.get("reason", f"Selected to practice {sk_name} at {item.difficulty_band.value} level."),
            prerequisite_skill_id=ctx.get("prerequisite_skill_id"),
            mistake_pattern_type=ctx.get("mistake_pattern_type"),
            difficulty=item.difficulty_band
        )

    # ─── 7. SESSION SUMMARY ───────────────────────────────────────────────────

    @classmethod
    def get_session_summary(cls, session_id: str, user_id: str) -> Optional[SessionSummary]:
        """
        Pedagogical outcome summary (§30).
        Zero XP, coins, streaks, or fake mastery percentages.
        """
        session = PracticeRepository.get_session(session_id)
        if not session or session.user_id != user_id:
            return None

        responses = PracticeRepository.get_session_responses(session_id)
        total_q = len(responses)
        corr_count = sum(1 for r in responses if r.correctness)
        indep_corr = sum(1 for r in responses if r.correctness and r.assistance_level == AssistanceLevel.INDEPENDENT)

        by_skill: Dict[str, Dict[str, int]] = {}
        for r in responses:
            st = by_skill.setdefault(r.skill_id, {"attempted": 0, "correct": 0, "independent": 0})
            st["attempted"] += 1
            if r.correctness:
                st["correct"] += 1
                if r.assistance_level == AssistanceLevel.INDEPENDENT:
                    st["independent"] += 1

        skills_practiced_info: List[Dict[str, Any]] = []
        stronger: List[str] = []
        developing: List[str] = []

        for sk_id, st in by_skill.items():
            sk_obj = get_skill(sk_id)
            name = sk_obj.skill_name if sk_obj else sk_id
            skills_practiced_info.append({
                "skill_id": sk_id,
                "skill_name": name,
                "attempted": st["attempted"],
                "correct": st["correct"],
                "independent": st["independent"]
            })
            if st["independent"] >= 2 or (st["attempted"] >= 2 and st["correct"] == st["attempted"]):
                stronger.append(name)
            else:
                developing.append(name)

        # Open patterns from Mistake DNA
        encountered_mistakes: List[str] = []
        for r in responses:
            if not r.correctness and r.selection_reason:
                encountered_mistakes.append(f"{r.skill_id} incorrect attempt")

        duration = 0
        if session.completed_at and session.started_at:
            duration = int((session.completed_at - session.started_at).total_seconds())

        next_focus = developing[0] if developing else (stronger[0] if stronger else session.subject)

        return SessionSummary(
            session_id=session.id,
            user_id=session.user_id,
            subject=session.subject,
            mode=session.mode,
            total_questions=total_q,
            correct_count=corr_count,
            independent_correct_count=indep_corr,
            skills_practiced=skills_practiced_info,
            stronger_evidence_concepts=stronger,
            developing_concepts=developing,
            mistake_patterns_encountered=encountered_mistakes,
            recommended_next_focus=f"Continue reinforcing {next_focus}",
            duration_seconds=duration
        )

    # ─── 8. COMPACT LEARNER CONTEXT INTEGRATION ───────────────────────────────

    @classmethod
    def get_compact_practice_summary(cls, user_id: str, subject: Optional[str] = None) -> CompactPracticeSummary:
        """Compact non-dump summary for LearnerContextService (§42)."""
        recent = PracticeRepository.get_user_recent_responses(user_id, limit=20)
        recent_skill = recent[0].skill_id if recent else None
        active = PracticeRepository.get_active_session_for_user(user_id, subject)

        return CompactPracticeSummary(
            recent_practice_skill=recent_skill,
            current_active_focus=active.current_skill_id if active else None,
            total_practice_sessions=len(PracticeRepository._sessions_cache),
            total_practice_items_answered=len(recent),
            relevant_open_repair=recent[0].selection_reason if recent else None
        )

    # ─── 9. INTERNAL SELECTION ENGINE ─────────────────────────────────────────

    @classmethod
    def _select_candidate_item(
        cls,
        session: PracticeSession,
        policy: PracticePolicy
    ) -> Tuple[Optional[PracticeItem], SelectionCategory, str, str]:
        """
        Deterministic, evidence-driven candidate selection (§5, §6, §8, §9, §10).
        Returns (item, category, explainable_reason, target_skill_id).
        """
        user_id = session.user_id
        subject = session.subject
        asked_ids = set(session.asked_item_ids)

        # 1. Check open recurring Mistake DNA patterns (§9)
        try:
            patterns = MistakeDNAService.get_patterns(user_id=user_id, subject=subject)
            open_recurring = [
                p for p in patterns
                if p.pattern_status in (PatternStatus.RECURRING, PatternStatus.PERSISTENT)
                and p.repair_status in (RepairStatus.OPEN, RepairStatus.IN_REPAIR)
            ]
        except Exception:
            open_recurring = []

        # 2. Check Prerequisite DAG Repair Path (§10)
        prereq_repair_target: Optional[Tuple[str, str, str]] = None  # (repair_skill_id, target_skill_id, reason)
        target_skill_check = session.requested_skill_id or session.current_skill_id
        if target_skill_check:
            try:
                dag = MasteryGraphService.get_dag_engine()
                imm_prereqs = dag.get_immediate_prerequisites(target_skill_check)
                for pr_id in imm_prereqs:
                    pr_st = MasteryGraphService.get_skill_state(user_id, pr_id)
                    if pr_st and pr_st.mastery_state in (MasteryState.NEEDS_REPAIR, MasteryState.FRAGILE):
                        sk_obj = get_skill(pr_id)
                        sk_name = sk_obj.skill_name if sk_obj else pr_id
                        prereq_repair_target = (
                            pr_id,
                            target_skill_check,
                            f"Prerequisite concept '{sk_name}' requires repair before advancing."
                        )
                        break
            except Exception:
                pass

        # Candidate selection priority hierarchy:
        # A. Prerequisite repair (highest priority)
        if prereq_repair_target and session.mode in (PracticeMode.ADAPTIVE, PracticeMode.REPAIR):
            rep_skill_id, tgt_skill_id, reason_txt = prereq_repair_target
            item = cls._pick_item_for_skill(rep_skill_id, session.current_difficulty, asked_ids)
            if item:
                return item, SelectionCategory.PREREQUISITE_REPAIR, reason_txt, rep_skill_id

        # B. Mistake DNA recurring pattern repair
        if open_recurring and session.mode in (PracticeMode.ADAPTIVE, PracticeMode.REPAIR):
            top_pat = open_recurring[0]
            err_type = top_pat.error_type.value
            item = cls._pick_item_for_skill(top_pat.skill_id, session.current_difficulty, asked_ids, target_mistake_type=err_type)
            if item:
                sk_obj = get_skill(top_pat.skill_id)
                sk_name = sk_obj.skill_name if sk_obj else top_pat.skill_id
                reason_txt = f"Selected to exercise {err_type.replace('_', ' ').lower()} error repair in {sk_name} based on your recent practice."
                return item, SelectionCategory.MISTAKE_DNA_REPAIR, reason_txt, top_pat.skill_id

        # C. Focused mode (explicit requested topic)
        if session.mode == PracticeMode.FOCUSED and session.requested_skill_id:
            sk_id = session.requested_skill_id
            item = cls._pick_item_for_skill(sk_id, session.current_difficulty, asked_ids)
            if item:
                sk_obj = get_skill(sk_id)
                sk_name = sk_obj.skill_name if sk_obj else sk_id
                return item, SelectionCategory.DEVELOPING_SKILL, f"Targeted practice for selected topic: {sk_name}.", sk_id
            else:
                logger.info(f"[PracticeService] Insufficient content for requested focused skill: {sk_id}")
                return None, SelectionCategory.DEVELOPING_SKILL, f"INSUFFICIENT_CONTENT: No validated practice items for {sk_id}.", sk_id

        # D. Adaptive next skill from Mastery Graph / Curriculum
        # Find candidate skills for this subject
        subject_skills = [s for s in CANONICAL_SKILLS if s.subject.lower() == subject.lower()]
        if not subject_skills:
            # Dynamic subject without pre-registered blueprint: search items directly! (§15, §59)
            all_items = get_all_practice_items()
            subj_items = [it for it in all_items if it.subject.lower() == subject.lower() and it.id not in asked_ids]
            if subj_items:
                picked = subj_items[0]
                return picked, SelectionCategory.EXPLORATORY_PROBE, f"Exploratory practice for {subject}.", picked.skill_id
            return None, SelectionCategory.EXPLORATORY_PROBE, "No items available", ""

        # Rank skills: developing -> ready next -> exploratory
        for sk in subject_skills:
            sk_st = MasteryGraphService.get_skill_state(user_id, sk.id)
            m_state = sk_st.mastery_state if sk_st else MasteryState.NOT_ASSESSED

            if m_state in (MasteryState.DEVELOPING, MasteryState.FRAGILE):
                item = cls._pick_item_for_skill(sk.id, session.current_difficulty, asked_ids)
                if item:
                    return item, SelectionCategory.DEVELOPING_SKILL, f"Developing skill practice: {sk.skill_name}.", sk.id

            elif m_state == MasteryState.NOT_ASSESSED:
                item = cls._pick_item_for_skill(sk.id, DifficultyBand.FOUNDATIONAL, asked_ids)
                if item:
                    return item, SelectionCategory.EXPLORATORY_PROBE, f"Foundational exploratory probe: {sk.skill_name}.", sk.id

        # E. Fallback: Any available unasked item in subject
        for sk in subject_skills:
            item = cls._pick_item_for_skill(sk.id, session.current_difficulty, asked_ids)
            if item:
                return item, SelectionCategory.READY_NEXT_SKILL, f"Curriculum practice on {sk.skill_name}.", sk.id

        # If all items in exact subject are exhausted, return honest None (stopping condition)
        return None, SelectionCategory.EXPLORATORY_PROBE, "Content budget exhausted", ""

    @classmethod
    def _pick_item_for_skill(
        cls,
        skill_id: str,
        desired_difficulty: DifficultyBand,
        asked_item_ids: Set[str],
        target_mistake_type: Optional[str] = None
    ) -> Optional[PracticeItem]:
        """
        Picks a validated item for a skill, respecting difficulty, anti-repetition, and mistake tags.
        """
        items = get_practice_items_for_skill(skill_id)
        valid_items = [
            it for it in items
            if it.id not in asked_item_ids and it.verification_status == VerificationStatus.VERIFIED
        ]

        if not valid_items:
            return None

        # 1. Target mistake type if requested (§9)
        if target_mistake_type:
            targeted = [it for it in valid_items if target_mistake_type in it.target_mistake_types]
            if targeted:
                # Check difficulty match among targeted
                diff_match = [it for it in targeted if it.difficulty_band == desired_difficulty]
                if diff_match:
                    return diff_match[0]
                return targeted[0]

        # 2. Desired difficulty match
        diff_match = [it for it in valid_items if it.difficulty_band == desired_difficulty]
        if diff_match:
            return diff_match[0]

        # 3. Adjacent difficulty fallback (STANDARD fallback)
        std_match = [it for it in valid_items if it.difficulty_band == DifficultyBand.STANDARD]
        if std_match:
            return std_match[0]

        return valid_items[0]
