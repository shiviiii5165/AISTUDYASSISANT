"""
LearnByGenie — Canonical AI-Off Transfer Check Service (Feature 7)
===================================================================
Subject-agnostic, database-driven independent verification engine.

Core Responsibilities:
- Verifies whether learning survives after AI support is removed (§MISSION, §1)
- Strict AI-off boundary during attempt (assistance_level = INDEPENDENT) (§1, §4, §28)
- Server-side support lock enforcing no Tutor/Hint bypass (§29)
- Near-transfer vs. Far-transfer resolution with novelty protection (§5, §6)
- Closed-loop evidence flows:
  * Emits EvidenceSource.TRANSFER_CHECK to MasteryGraphService (§17)
  * Emits MistakeSourceType.TRANSFER_CHECK on failure to MistakeDNAService (§19)
  * Provides strong independent repair confirmation on success to Mistake DNA (§20)
- Reuses Feature 6 verified item bank and domain validator adapters (§8, §25)
- Server-authoritative PostgreSQL persistence and idempotency (§12, §14, §16)
"""
from typing import Dict, Any, Optional, List, Tuple, Set
from datetime import datetime, timezone
import uuid

from app.core.logging import logger
from .schemas import (
    TransferTrigger, TransferLevel, TransferSessionStatus,
    TransferOutcome, TransferEligibilityResult, TransferSession,
    TransferResponse, StudentTransferItemView, TransferFeedback,
    TransferSummary
)
from .policy import TransferPolicy, get_transfer_policy
from .repository import TransferRepository

# Reusable Feature 6 components (§8, §25)
from app.services.practice.schemas import (
    PracticeItem, VerificationStatus, QuestionType
)
from app.services.practice.item_bank import (
    get_practice_item, get_practice_items_for_skill,
    get_all_practice_items
)
from app.services.practice.adapters import DomainAdapterRegistry

# Frozen Integrations (§FROZEN FOUNDATIONS)
from app.services.mastery.service import MasteryGraphService
from app.services.mastery.schemas import (
    EvidenceSource, AssistanceLevel as MasteryAssistanceLevel
)
from app.services.mistake_dna.service import MistakeDNAService
from app.services.mistake_dna.schemas import (
    MistakeSourceType, MistakeCandidate, AssistanceLevel as MistakeAssistanceLevel
)
from app.services.diagnostic.curriculum_blueprint import get_skill, CANONICAL_SKILLS


class AIOffTransferCheckService:
    """Canonical AI-Off Transfer Check Engine."""

    # ─── 1. ELIGIBILITY CHECK ─────────────────────────────────────────────────

    @classmethod
    def check_eligibility(
        cls,
        user_id: str,
        skill_id: str,
        trigger: TransferTrigger,
        trigger_id: str = "",
        policy_version: Optional[str] = None
    ) -> TransferEligibilityResult:
        """
        Determines if a student qualifies for an independent transfer verification (§2, §42).
        Casual chat or single passive explanation views are strictly rejected.
        """
        policy = get_transfer_policy(policy_version)

        # 1. Trigger validity check
        if not policy.is_eligible_trigger(trigger):
            return TransferEligibilityResult(
                is_eligible=False,
                skill_id=skill_id,
                trigger=trigger,
                reason="Trigger does not qualify for independent transfer verification.",
                cooldown_remaining_seconds=0,
                available_items_count=0
            )

        # 2. Cooldown check after prior failure
        last_failed = TransferRepository.get_user_last_failed_attempt(user_id, skill_id)
        cooldown = policy.check_cooldown(last_failed)
        if cooldown > 0:
            return TransferEligibilityResult(
                is_eligible=False,
                skill_id=skill_id,
                trigger=trigger,
                reason=f"Transfer check cooldown active. Please practice or review first ({cooldown}s remaining).",
                cooldown_remaining_seconds=cooldown,
                available_items_count=0
            )

        # 3. Item availability check
        items = get_practice_items_for_skill(skill_id)
        verified_items = [it for it in items if it.verification_status == VerificationStatus.VERIFIED]
        if not verified_items:
            return TransferEligibilityResult(
                is_eligible=False,
                skill_id=skill_id,
                trigger=trigger,
                reason="INSUFFICIENT_TRANSFER_CONTENT: No verified items available for skill.",
                cooldown_remaining_seconds=0,
                available_items_count=0
            )

        return TransferEligibilityResult(
            is_eligible=True,
            skill_id=skill_id,
            trigger=trigger,
            reason="Qualified for independent transfer verification.",
            cooldown_remaining_seconds=0,
            available_items_count=len(verified_items)
        )

    # ─── 2. START SESSION ─────────────────────────────────────────────────────

    @classmethod
    def start_session(
        cls,
        user_id: str,
        skill_id: str,
        subject: str,
        source_trigger: TransferTrigger = TransferTrigger.PRACTICE_REPAIR,
        source_trigger_id: str = "",
        transfer_level: TransferLevel = TransferLevel.NEAR_TRANSFER,
        excluded_item_ids: Optional[List[str]] = None,
        policy_version: Optional[str] = None
    ) -> Optional[TransferSession]:
        """
        Initializes an independent transfer verification session (§12).
        Strictly enforces item novelty and disables AI support.
        """
        policy = get_transfer_policy(policy_version)
        excluded_set: Set[str] = set(excluded_item_ids or [])

        # Fetch candidate verified items
        items = get_practice_items_for_skill(skill_id)
        if not items:
            # Fallback for dynamic synthetic subjects without pre-seeded list (§24)
            all_items = get_all_practice_items()
            items = [it for it in all_items if it.skill_id == skill_id]

        eligible = policy.select_eligible_items(items, excluded_set, transfer_level)

        if not eligible:
            logger.warning(
                f"[TransferService] Insufficient novel transfer content for user {user_id} on skill {skill_id}"
            )
            return None

        # Select first novel verified item
        chosen_item = eligible[0]

        sk_obj = get_skill(skill_id)
        skill_name = sk_obj.skill_name if sk_obj else skill_id
        trigger_expl = f"You recently worked on {skill_name}. Let's verify whether you can solve a similar problem completely on your own!"

        session = TransferSession(
            user_id=user_id,
            skill_id=skill_id,
            subject=subject,
            source_trigger=source_trigger,
            source_trigger_id=source_trigger_id,
            transfer_level=transfer_level,
            policy_version=policy.version,
            current_item_id=chosen_item.id,
            status=TransferSessionStatus.IN_PROGRESS,
            question_index=0,
            question_budget=policy.config.question_budget,
            support_lock_active=True,
            trigger_explanation=trigger_expl,
            started_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        TransferRepository.save_session(session)
        logger.info(
            f"[TransferService] Started transfer session {session.id} for user {user_id} on {skill_id} ({transfer_level.value})"
        )
        return session

    # ─── 3. GET CURRENT ITEM ──────────────────────────────────────────────────

    @classmethod
    def get_current_item(
        cls,
        session_id: str,
        user_id: str
    ) -> Optional[StudentTransferItemView]:
        """
        Delivers the active transfer question (§1, §38).
        Strictly omits correct answers, explanations, and unrevealed hints.
        """
        session = TransferRepository.get_session(session_id)
        if not session or session.user_id != user_id:
            logger.warning(f"[TransferService] Session lookup failed or unauthorized: {session_id}")
            return None

        if session.status != TransferSessionStatus.IN_PROGRESS:
            return None

        if not session.current_item_id:
            return None

        item = get_practice_item(session.current_item_id)
        if not item:
            return None

        policy = get_transfer_policy(session.policy_version)
        badge = policy.format_badge_text(item.grade_band)

        return StudentTransferItemView(
            session_id=session.id,
            item_id=item.id,
            skill_id=session.skill_id,
            subject=session.subject,
            grade_band=item.grade_band,
            prompt=item.prompt,
            options=item.options,
            question_type=item.question_type.value if hasattr(item.question_type, "value") else str(item.question_type),
            transfer_level=session.transfer_level,
            transfer_badge_text=badge,
            why_explanation=session.trigger_explanation,
            support_disabled=True
        )

    # ─── 4. SUBMIT RESPONSE ───────────────────────────────────────────────────

    @classmethod
    def submit_response(
        cls,
        session_id: str,
        user_id: str,
        item_id: Optional[str] = None,
        student_response: Any = None,
        response_time_ms: int = 0,
        question_index: int = 0
    ) -> Optional[TransferFeedback]:
        """
        Processes an independent transfer attempt (§10, §13, §14, §17, §19, §20).
        Closes loops with Mastery Graph and Mistake DNA.
        """
        session = TransferRepository.get_session(session_id)
        if not session or session.user_id != user_id:
            logger.warning(f"[TransferService] Unauthorized or missing session: {session_id}")
            return None

        if not item_id:
            item_id = session.current_item_id

        # 1. Optimistic sequence check for multi-tab divergence (§15)
        if question_index != session.question_index:
            logger.info(
                f"[TransferService] Sequence mismatch in transfer session {session_id}: expected {session.question_index}, got {question_index}"
            )
            past_resps = TransferRepository.get_session_responses(session_id)
            for pr in past_resps:
                if pr.question_index == question_index:
                    raw_item = get_practice_item(pr.item_id)
                    policy = get_transfer_policy(session.policy_version)
                    headline = "You solved this independently." if pr.correctness else "This concept still needs a little more practice."
                    return TransferFeedback(
                        session_id=session_id,
                        item_id=pr.item_id,
                        skill_id=pr.skill_id,
                        correctness=pr.correctness,
                        outcome=pr.transfer_outcome,
                        feedback_headline=headline,
                        educational_explanation=raw_item.explanation if raw_item else "",
                        recommended_next_action="Review summary",
                        is_session_complete=True
                    )

        item = get_practice_item(item_id)
        if not item:
            logger.warning(f"[TransferService] Transfer item {item_id} not found")
            return None

        # 2. Domain answer validation via Feature 6 adapter (§25)
        adapter = DomainAdapterRegistry.get_adapter(session.subject)
        is_correct, _ = adapter.validate_answer(item, student_response)

        # 3. Policy outcome mapping (§10)
        policy = get_transfer_policy(session.policy_version)
        outcome, sess_status, headline, next_step = policy.evaluate_attempt(
            is_correct=is_correct,
            assistance_level="INDEPENDENT"
        )

        # 4. Construct Response Record
        response = TransferResponse(
            session_id=session_id,
            user_id=user_id,
            item_id=item_id,
            skill_id=session.skill_id,
            question_index=session.question_index,
            student_response=student_response,
            correctness=is_correct,
            assistance_level="INDEPENDENT",
            attempt_sequence=1,
            response_time_ms=response_time_ms,
            validator_result={"validated_by": type(adapter).__name__, "is_correct": is_correct},
            transfer_outcome=outcome,
            created_at=datetime.now(timezone.utc)
        )

        saved_resp, is_new = TransferRepository.record_response(response)
        if not is_new:
            # Idempotent re-submission (§14)
            return TransferFeedback(
                session_id=session_id,
                item_id=saved_resp.item_id,
                skill_id=saved_resp.skill_id,
                correctness=saved_resp.correctness,
                outcome=saved_resp.transfer_outcome,
                feedback_headline=headline,
                educational_explanation=item.explanation,
                recommended_next_action=next_step,
                is_session_complete=True
            )

        # 5. Complete session
        session.status = sess_status
        session.question_index += 1
        session.completed_at = datetime.now(timezone.utc)
        session.support_lock_active = False
        TransferRepository.save_session(session)

        # ─── CLOSED LOOP: MASTERY GRAPH EVIDENCE (§3, §17) ────────────────────
        try:
            MasteryGraphService.ingest_evidence(
                user_id=user_id,
                skill_id=session.skill_id,
                source_type=EvidenceSource.TRANSFER_CHECK,
                source_record_id=f"transfer_resp_{saved_resp.id}",
                correctness=is_correct,
                independence_level=MasteryAssistanceLevel.INDEPENDENT,
                metadata={
                    "session_id": session_id,
                    "transfer_level": session.transfer_level.value,
                    "source_trigger": session.source_trigger.value
                }
            )
        except Exception as e:
            logger.warning(f"[TransferService] Mastery evidence ingestion notice: {e}")

        # ─── CLOSED LOOP: MISTAKE DNA INTEGRATION (§18, §19, §20) ─────────────
        if not is_correct:
            # Failed transfer attempt forwards to Mistake DNA
            try:
                candidate = MistakeCandidate(
                    user_id=user_id,
                    skill_id=session.skill_id,
                    subject=session.subject,
                    source_type=MistakeSourceType.TRANSFER_CHECK,
                    source_record_id=f"transfer_resp_{saved_resp.id}",
                    question_reference=item.prompt[:120],
                    student_response=str(student_response),
                    correct_answer=str(item.correct_answer),
                    prompt_text=item.prompt,
                    assistance_level=MistakeAssistanceLevel.INDEPENDENT,
                    metadata={"transfer_level": session.transfer_level.value}
                )
                MistakeDNAService.ingest_error_candidate(candidate)
            except Exception as e:
                logger.warning(f"[TransferService] Mistake DNA ingestion notice: {e}")
        else:
            # Independent success confirms repair in Mistake DNA (§20)
            try:
                MistakeDNAService.mark_repair_evidence(
                    user_id=user_id,
                    skill_id=session.skill_id,
                    evidence_source=MistakeSourceType.TRANSFER_CHECK,
                    evidence_record_id=f"transfer_resp_{saved_resp.id}",
                    assistance_level=MistakeAssistanceLevel.INDEPENDENT,
                    notes="Independent transfer check passed"
                )
            except Exception as e:
                logger.warning(f"[TransferService] Mistake DNA repair notice: {e}")

        return TransferFeedback(
            session_id=session_id,
            item_id=item_id,
            skill_id=session.skill_id,
            correctness=is_correct,
            outcome=outcome,
            feedback_headline=headline,
            educational_explanation=item.explanation,
            recommended_next_action=next_step,
            is_session_complete=True
        )

    # ─── 5. ABORT SESSION / SERVER SUPPORT LOCK (§4, §22, §28, §29) ───────────

    @classmethod
    def abort_session(
        cls,
        session_id: str,
        user_id: str,
        reason: str = "SUPPORT_REQUESTED_DURING_TRANSFER"
    ) -> Optional[TransferSession]:
        """
        Aborts an active transfer session (§4).
        Triggered if the student requests a hint, calls tutor, or exits.
        """
        session = TransferRepository.get_session(session_id)
        if not session or session.user_id != user_id:
            return None

        session.status = TransferSessionStatus.ABORTED
        session.abort_reason = reason
        session.support_lock_active = False
        session.completed_at = datetime.now(timezone.utc)
        TransferRepository.save_session(session)
        logger.info(f"[TransferService] Transfer session {session_id} aborted: {reason}")
        return session

    @classmethod
    def is_support_locked(cls, user_id: str, skill_id: Optional[str] = None) -> bool:
        """
        Checks whether active AI support is locked for this user on this skill (or any active transfer) (§29).
        """
        active = TransferRepository.get_active_session_for_user_skill(user_id, skill_id)
        return active is not None and active.status == TransferSessionStatus.IN_PROGRESS

    @classmethod
    def record_support_attempt(cls, user_id: str, skill_id: Optional[str] = None, support_channel: str = "TUTOR_OR_HINT") -> bool:
        """
        Intercepts attempts to call AI support during an active transfer session (§29).
        Aborts the transfer session and revokes independent validity.
        Returns True if an active session was found and invalidated.
        """
        active = TransferRepository.get_active_session_for_user_skill(user_id, skill_id)
        if active and active.status == TransferSessionStatus.IN_PROGRESS:
            cls.abort_session(active.id, user_id, reason=f"Support requested via {support_channel}")
            return True
        return False

    # ─── 6. RESUME & SUMMARY ──────────────────────────────────────────────────

    @classmethod
    def resume_session(
        cls,
        session_id: str,
        user_id: str
    ) -> Optional[Tuple[TransferSession, Optional[StudentTransferItemView]]]:
        """
        Cold restart recovery (§16). Reconstructs active state from PostgreSQL.
        """
        session = TransferRepository.get_session(session_id)
        if not session or session.user_id != user_id:
            return None

        item_view = cls.get_current_item(session_id, user_id)
        return session, item_view

    @classmethod
    def get_session_summary(
        cls,
        session_id: str,
        user_id: str
    ) -> Optional[TransferSummary]:
        """Returns post-attempt pedagogical outcome summary (§41)."""
        session = TransferRepository.get_session(session_id)
        if not session or session.user_id != user_id:
            return None

        resps = TransferRepository.get_session_responses(session_id)
        outcome = resps[0].transfer_outcome if resps else TransferOutcome.ABORTED

        policy = get_transfer_policy(session.policy_version)
        if outcome == TransferOutcome.PASSED:
            headline = "You solved this independently."
            expl = "Your independent solution confirmed that this skill is secure without support."
            next_s = "Great job! You are ready to move on to the next topic."
        elif outcome == TransferOutcome.NEEDS_MORE_EVIDENCE:
            headline = "This concept still needs a little more practice."
            expl = "The problem was attempted independently, but some parts need reinforcement."
            next_s = "We recommend practicing a targeted problem with hints or reviewing with the Socratic Tutor."
        else:
            headline = "Check was interrupted."
            expl = "Support was requested during the check, so it could not be counted as independent evidence."
            next_s = "Review the concept with Tutor and try again when you are ready."

        duration = 0
        if session.completed_at and session.started_at:
            duration = int((session.completed_at - session.started_at).total_seconds())

        return TransferSummary(
            session_id=session.id,
            user_id=session.user_id,
            skill_id=session.skill_id,
            subject=session.subject,
            source_trigger=session.source_trigger,
            transfer_level=session.transfer_level,
            outcome=outcome,
            status=session.status,
            duration_seconds=duration,
            headline=headline,
            explanation=expl,
            next_step=next_s
        )
