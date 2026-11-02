from datetime import datetime, timezone, date, timedelta
from typing import List, Optional
import uuid

from app.services.spaced_repetition.schemas import (
    SpacedCard,
    CardType,
    ReviewSubmissionRequest,
    ReviewFeedbackResponse,
    QueueSummaryResponse
)
from app.services.spaced_repetition.repository import SpacedRepetitionRepository
from app.services.gamification.service import GamificationService
from app.services.gamification.schemas import XPReasonCode


class SpacedRepetitionService:
    """
    Implements SuperMemo SM-2 Spaced Repetition Algorithm:
    - Ease Factor adjustment: EF' = max(1.3, EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))
    - Intervals:
        If q < 3 (failure): rep = 0, interval = 1 day
        If q >= 3 (success):
            rep == 0: interval = 1
            rep == 1: interval = 6
            rep >= 2: interval = round(previous_interval * EF')
            rep += 1
    """

    @classmethod
    def process_review(cls, user_id: str, request: ReviewSubmissionRequest) -> ReviewFeedbackResponse:
        card = SpacedRepetitionRepository.get_card(request.card_id)
        if not card or card.user_id != user_id:
            raise ValueError(f"Card {request.card_id} not found for user {user_id}")

        q = request.quality_rating
        prev_ef = card.ease_factor
        prev_interval = card.interval_days
        prev_rep = card.repetition_number

        # 1. Update Ease Factor
        # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        new_ef = prev_ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        new_ef = max(1.30, round(new_ef, 2))

        # 2. Update Repetition Number & Interval Days
        today = date.today()
        if q < 3:
            # Blackout / Failure: reset interval
            new_rep = 0
            new_interval = 1
        else:
            # Success
            if prev_rep == 0:
                new_interval = 1
            elif prev_rep == 1:
                new_interval = 6
            else:
                new_interval = max(1, round(prev_interval * new_ef))
            new_rep = prev_rep + 1

        next_date = today + timedelta(days=new_interval)

        # 3. Save updated card
        card.ease_factor = new_ef
        card.interval_days = new_interval
        card.repetition_number = new_rep
        card.next_review_date = next_date
        card.updated_at = datetime.now(timezone.utc)
        SpacedRepetitionRepository.save_card(card)

        # 4. Record review in ledger
        SpacedRepetitionRepository.record_review(
            card_id=card.id,
            user_id=user_id,
            quality_rating=q,
            prev_interval=prev_interval,
            new_interval=new_interval,
            prev_ef=prev_ef,
            new_ef=new_ef
        )

        # 5. Award XP based on quality
        xp_earned = 5 if q < 3 else (10 + (q - 3) * 5)
        GamificationService.award_xp(
            user_id=user_id,
            amount=xp_earned,
            reason_code=XPReasonCode.PRACTICE_STREAK,
            source_entity_type="spaced_card_review",
            source_entity_id=card.id,
            idempotency_key=f"sr_review_{card.id}_{today.isoformat()}_{prev_rep}"
        )

        return ReviewFeedbackResponse(
            card_id=card.id,
            quality_rating=q,
            previous_interval=prev_interval,
            new_interval=new_interval,
            previous_ease_factor=prev_ef,
            new_ease_factor=new_ef,
            next_review_date=next_date,
            xp_awarded=xp_earned
        )

    @classmethod
    def get_queue(cls, user_id: str) -> QueueSummaryResponse:
        """Returns cards currently due for review."""
        all_cards = SpacedRepetitionRepository.get_cards_for_user(user_id)
        if not all_cards:
            # Auto-seed foundational cards so user has content
            cls.seed_default_cards(user_id)
            all_cards = SpacedRepetitionRepository.get_cards_for_user(user_id)

        today = date.today()
        week_ahead = today + timedelta(days=7)

        due_today = [c for c in all_cards if c.next_review_date <= today]
        upcoming = [c for c in all_cards if today < c.next_review_date <= week_ahead]

        return QueueSummaryResponse(
            user_id=user_id,
            total_cards=len(all_cards),
            due_today_count=len(due_today),
            upcoming_this_week_count=len(upcoming),
            cards=due_today
        )

    @classmethod
    def seed_default_cards(cls, user_id: str) -> List[SpacedCard]:
        """Creates curated default revision cards for foundational concepts."""
        now = datetime.now(timezone.utc)
        today = date.today()
        curated_seeds = [
            {
                "skill_id": "MATH_LIN_EQ",
                "card_type": CardType.CONCEPT_CHECK,
                "prompt": "In linear equations, what sign rule applies when dividing both sides by a negative number?",
                "answer": "Dividing or multiplying an inequality by a negative reverses the inequality; in equations, division by -k changes the sign of both sides.",
                "explanation": "Remember to distribute the negative sign carefully: 9 / (-3) = -3."
            },
            {
                "skill_id": "MATH_QUAD_EQ",
                "card_type": CardType.FORMULA_RECALL,
                "prompt": "What is the discriminant of the quadratic equation ax^2 + bx + c = 0, and what do its signs indicate?",
                "answer": "D = b^2 - 4ac. If D > 0: two real roots; D = 0: one real root; D < 0: two complex roots.",
                "explanation": "The discriminant determines the nature of the roots without computing the full quadratic formula."
            },
            {
                "skill_id": "PHY_KINEMATICS",
                "card_type": CardType.FORMULA_RECALL,
                "prompt": "State the three equations of motion under uniform acceleration.",
                "answer": "1. v = u + at,  2. s = ut + 0.5*a*t^2,  3. v^2 = u^2 + 2as",
                "explanation": "Valid only when acceleration 'a' is constant along a straight line."
            },
            {
                "skill_id": "CHEM_STOICHIOMETRY",
                "card_type": CardType.CONCEPT_CHECK,
                "prompt": "How many particles are present in exactly 1 mole of any substance?",
                "answer": "6.022 x 10^23 particles (Avogadro's constant, N_A).",
                "explanation": "1 mole of carbon-12 has a mass of exactly 12 grams."
            }
        ]

        created: List[SpacedCard] = []
        for seed in curated_seeds:
            card = SpacedCard(
                id=str(uuid.uuid4()),
                user_id=user_id,
                skill_id=seed["skill_id"],
                card_type=seed["card_type"],
                prompt=seed["prompt"],
                answer=seed["answer"],
                explanation=seed["explanation"],
                ease_factor=2.50,
                interval_days=1,
                repetition_number=0,
                next_review_date=today,
                created_at=now,
                updated_at=now
            )
            SpacedRepetitionRepository.save_card(card)
            created.append(card)

        return created

