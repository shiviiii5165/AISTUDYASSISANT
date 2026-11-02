from datetime import datetime, timezone, date, timedelta
from typing import Dict, Any, Optional, List, Tuple
import threading
import uuid
import copy

from app.db.supabase_client import supabase
from app.core.logging import logger
from app.services.gamification.schemas import (
    XPTransaction,
    XPReasonCode,
    StreakSummary,
    BadgeItem
)


class GamificationRepository:
    """Thread-safe, idempotent persistence layer for XP transactions, streaks, and badges."""
    _LOCK = threading.Lock()
    _XP_LEDGER: Dict[str, XPTransaction] = {}
    _IDEMPOTENCY_INDEX: Dict[str, str] = {}  # idempotency_key -> transaction_id
    _STREAKS: Dict[str, Dict[str, Any]] = {}  # user_id -> streak record
    _BADGES: Dict[str, List[BadgeItem]] = {}  # user_id -> badges list

    @classmethod
    def clear_memory_cache(cls):
        with cls._LOCK:
            cls._XP_LEDGER.clear()
            cls._IDEMPOTENCY_INDEX.clear()
            cls._STREAKS.clear()
            cls._BADGES.clear()

    @classmethod
    def record_xp_transaction(
        cls,
        user_id: str,
        amount: int,
        reason_code: XPReasonCode,
        source_entity_type: str,
        idempotency_key: str,
        source_entity_id: Optional[str] = None
    ) -> Tuple[XPTransaction, bool]:
        """
        Appends an XP transaction to the ledger with strict idempotency.
        Returns (transaction, is_new). If idempotency_key was previously processed,
        returns existing transaction and False without altering balance.
        """
        with cls._LOCK:
            # 1. Check local index
            if idempotency_key in cls._IDEMPOTENCY_INDEX:
                tx_id = cls._IDEMPOTENCY_INDEX[idempotency_key]
                return copy.deepcopy(cls._XP_LEDGER[tx_id]), False

            # 2. Check remote Supabase if connected
            if supabase is not None:
                try:
                    res = supabase.table("xp_ledger").select("*").eq("idempotency_key", idempotency_key).limit(1).execute()
                    if res.data and len(res.data) > 0:
                        tx_data = res.data[0]
                        tx = XPTransaction(
                            id=tx_data["id"],
                            user_id=tx_data["user_id"],
                            amount=tx_data["amount"],
                            reason_code=XPReasonCode(tx_data["reason_code"]),
                            source_entity_type=tx_data["source_entity_type"],
                            source_entity_id=tx_data.get("source_entity_id"),
                            idempotency_key=tx_data["idempotency_key"],
                            created_at=datetime.fromisoformat(tx_data["created_at"])
                        )
                        cls._XP_LEDGER[tx.id] = tx
                        cls._IDEMPOTENCY_INDEX[idempotency_key] = tx.id
                        return tx, False
                except Exception as e:
                    logger.debug(f"[GamificationRepo] Supabase idempotency check notice: {e}")

            # 3. Create new transaction
            tx_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            tx = XPTransaction(
                id=tx_id,
                user_id=user_id,
                amount=amount,
                reason_code=reason_code,
                source_entity_type=source_entity_type,
                source_entity_id=source_entity_id,
                idempotency_key=idempotency_key,
                created_at=now
            )

            # Persist to remote Supabase if available
            if supabase is not None:
                try:
                    supabase.table("xp_ledger").insert({
                        "id": tx.id,
                        "user_id": tx.user_id,
                        "amount": tx.amount,
                        "reason_code": tx.reason_code.value,
                        "source_entity_type": tx.source_entity_type,
                        "source_entity_id": tx.source_entity_id,
                        "idempotency_key": tx.idempotency_key,
                        "created_at": tx.created_at.isoformat()
                    }).execute()
                except Exception as e:
                    err_str = str(e).lower()
                    if "duplicate" in err_str or "23505" in err_str or "unique" in err_str or "idempotency_key" in err_str:
                        try:
                            res_re = supabase.table("xp_ledger").select("*").eq("idempotency_key", idempotency_key).limit(1).execute()
                            if res_re.data and len(res_re.data) > 0:
                                tx_data = res_re.data[0]
                                existing_tx = XPTransaction(
                                    id=tx_data["id"],
                                    user_id=tx_data["user_id"],
                                    amount=tx_data["amount"],
                                    reason_code=XPReasonCode(tx_data["reason_code"]),
                                    source_entity_type=tx_data["source_entity_type"],
                                    source_entity_id=tx_data.get("source_entity_id"),
                                    idempotency_key=tx_data["idempotency_key"],
                                    created_at=datetime.fromisoformat(tx_data["created_at"])
                                )
                                cls._XP_LEDGER[existing_tx.id] = existing_tx
                                cls._IDEMPOTENCY_INDEX[idempotency_key] = existing_tx.id
                                return existing_tx, False
                        except Exception:
                            pass
                    from app.core.dependencies import _is_dev_environment
                    if not _is_dev_environment():
                        raise RuntimeError(f"Authoritative XP ledger persistence failed: {e}")
                    logger.warning(f"[GamificationRepo] Remote XP ledger insert notice: {e}")

            cls._XP_LEDGER[tx.id] = tx
            cls._IDEMPOTENCY_INDEX[idempotency_key] = tx.id
            return copy.deepcopy(tx), True

    @classmethod
    def get_user_transactions(cls, user_id: str, limit: int = 20) -> List[XPTransaction]:
        if supabase is not None:
            try:
                res = supabase.table("xp_ledger").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
                if res.data:
                    txs = []
                    for tx_data in res.data:
                        txs.append(XPTransaction(
                            id=tx_data["id"],
                            user_id=tx_data["user_id"],
                            amount=tx_data["amount"],
                            reason_code=XPReasonCode(tx_data["reason_code"]),
                            source_entity_type=tx_data["source_entity_type"],
                            source_entity_id=tx_data.get("source_entity_id"),
                            idempotency_key=tx_data["idempotency_key"],
                            created_at=datetime.fromisoformat(tx_data["created_at"])
                        ))
                    return txs
            except Exception as e:
                logger.debug(f"[GamificationRepo] Database get_user_transactions notice: {e}")

        with cls._LOCK:
            user_txs = [tx for tx in cls._XP_LEDGER.values() if tx.user_id == user_id]
            user_txs.sort(key=lambda x: x.created_at, reverse=True)
            return copy.deepcopy(user_txs[:limit])

    @classmethod
    def get_total_xp(cls, user_id: str) -> int:
        if supabase is not None:
            try:
                res = supabase.table("xp_ledger").select("amount").eq("user_id", user_id).execute()
                if res.data:
                    return sum(r["amount"] for r in res.data)
            except Exception as e:
                logger.debug(f"[GamificationRepo] Database get_total_xp notice: {e}")

        with cls._LOCK:
            return sum(tx.amount for tx in cls._XP_LEDGER.values() if tx.user_id == user_id)

    @classmethod
    def get_or_create_streak(cls, user_id: str) -> StreakSummary:
        today = date.today()
        with cls._LOCK:
            record = cls._STREAKS.get(user_id)
            if not record:
                record = {
                    "user_id": user_id,
                    "current_streak_days": 1,
                    "longest_streak_days": 1,
                    "last_activity_date": today,
                    "freeze_credits_remaining": 2
                }
                cls._STREAKS[user_id] = record
            
            is_active_today = (record["last_activity_date"] == today)
            return StreakSummary(
                user_id=user_id,
                current_streak_days=record["current_streak_days"],
                longest_streak_days=record["longest_streak_days"],
                last_activity_date=record["last_activity_date"],
                freeze_credits_remaining=record["freeze_credits_remaining"],
                is_active_today=is_active_today
            )

    @classmethod
    def update_streak(cls, user_id: str) -> StreakSummary:
        today = date.today()
        with cls._LOCK:
            record = cls._STREAKS.get(user_id)
            if not record:
                record = {
                    "user_id": user_id,
                    "current_streak_days": 1,
                    "longest_streak_days": 1,
                    "last_activity_date": today,
                    "freeze_credits_remaining": 2
                }
                cls._STREAKS[user_id] = record
                return StreakSummary(**record, is_active_today=True)

            last_date = record["last_activity_date"]
            if last_date == today:
                # Already active today
                return StreakSummary(**record, is_active_today=True)
            elif last_date == today - timedelta(days=1):
                # Consecutive day: increment streak
                record["current_streak_days"] += 1
                if record["current_streak_days"] > record["longest_streak_days"]:
                    record["longest_streak_days"] = record["current_streak_days"]
                record["last_activity_date"] = today
            else:
                # Gap detected: check freeze credits
                gap_days = (today - last_date).days
                if gap_days == 2 and record["freeze_credits_remaining"] > 0:
                    record["freeze_credits_remaining"] -= 1
                    record["current_streak_days"] += 1
                    record["last_activity_date"] = today
                else:
                    # Streak broken: reset to 1
                    record["current_streak_days"] = 1
                    record["last_activity_date"] = today

            return StreakSummary(**record, is_active_today=True)

    @classmethod
    def award_badge(cls, user_id: str, badge_key: str, title: str, description: str, tier: str = "bronze") -> Optional[BadgeItem]:
        with cls._LOCK:
            user_badges = cls._BADGES.setdefault(user_id, [])
            if any(b.badge_key == badge_key for b in user_badges):
                return None
            badge = BadgeItem(
                id=str(uuid.uuid4()),
                user_id=user_id,
                badge_key=badge_key,
                title=title,
                description=description,
                tier=tier,
                awarded_at=datetime.now(timezone.utc)
            )
            user_badges.append(badge)
            return copy.deepcopy(badge)

    @classmethod
    def get_badges(cls, user_id: str) -> List[BadgeItem]:
        with cls._LOCK:
            return copy.deepcopy(cls._BADGES.get(user_id, []))

