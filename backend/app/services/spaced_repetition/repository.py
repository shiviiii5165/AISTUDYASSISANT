from datetime import datetime, timezone, date, timedelta
from typing import Dict, Any, Optional, List
import threading
import uuid
import copy

from app.db.supabase_client import supabase
from app.core.logging import logger
from app.services.spaced_repetition.schemas import SpacedCard, CardType


class SpacedRepetitionRepository:
    """Thread-safe persistence layer for spaced repetition flashcards and reviews."""
    _LOCK = threading.Lock()
    _CARDS: Dict[str, SpacedCard] = {}  # card_id -> SpacedCard
    _REVIEWS: List[Dict[str, Any]] = []

    @classmethod
    def clear_memory_cache(cls):
        with cls._LOCK:
            cls._CARDS.clear()
            cls._REVIEWS.clear()

    @classmethod
    def save_card(cls, card: SpacedCard) -> SpacedCard:
        with cls._LOCK:
            cls._CARDS[card.id] = copy.deepcopy(card)
            if supabase is not None:
                try:
                    supabase.table("spaced_repetition_cards").upsert({
                        "id": card.id,
                        "user_id": card.user_id,
                        "skill_id": card.skill_id,
                        "card_type": card.card_type.value,
                        "prompt": card.prompt,
                        "answer": card.answer,
                        "explanation": card.explanation,
                        "ease_factor": card.ease_factor,
                        "interval_days": card.interval_days,
                        "repetition_number": card.repetition_number,
                        "next_review_date": card.next_review_date.isoformat(),
                        "created_at": card.created_at.isoformat(),
                        "updated_at": card.updated_at.isoformat(),
                    }).execute()
                except Exception as e:
                    logger.debug(f"[SpacedRepRepo] Supabase save card note: {e}")
            return copy.deepcopy(card)

    @classmethod
    def get_card(cls, card_id: str) -> Optional[SpacedCard]:
        with cls._LOCK:
            card = cls._CARDS.get(card_id)
            return copy.deepcopy(card) if card else None

    @classmethod
    def get_cards_for_user(cls, user_id: str) -> List[SpacedCard]:
        with cls._LOCK:
            user_cards = [c for c in cls._CARDS.values() if c.user_id == user_id]
            return copy.deepcopy(user_cards)

    @classmethod
    def get_due_cards_for_user(cls, user_id: str, target_date: Optional[date] = None) -> List[SpacedCard]:
        ref_date = target_date or date.today()
        with cls._LOCK:
            due = [
                c for c in cls._CARDS.values()
                if c.user_id == user_id and c.next_review_date <= ref_date
            ]
            due.sort(key=lambda c: c.next_review_date)
            return copy.deepcopy(due)

    @classmethod
    def record_review(
        cls,
        card_id: str,
        user_id: str,
        quality_rating: int,
        prev_interval: int,
        new_interval: int,
        prev_ef: float,
        new_ef: float
    ) -> None:
        rec = {
            "id": str(uuid.uuid4()),
            "card_id": card_id,
            "user_id": user_id,
            "quality_rating": quality_rating,
            "previous_interval": prev_interval,
            "new_interval": new_interval,
            "previous_ease_factor": prev_ef,
            "new_ease_factor": new_ef,
            "reviewed_at": datetime.now(timezone.utc).isoformat()
        }
        with cls._LOCK:
            cls._REVIEWS.append(rec)
            if supabase is not None:
                try:
                    supabase.table("spaced_repetition_reviews").insert(rec).execute()
                except Exception as e:
                    logger.debug(f"[SpacedRepRepo] Supabase record review note: {e}")

