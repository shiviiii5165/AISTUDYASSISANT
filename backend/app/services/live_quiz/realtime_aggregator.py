"""
Live Quiz Engine — Realtime Aggregator
======================================
Aggregates high-frequency student answer events into bounded periodic summaries
(250ms–500ms) to prevent overwhelming host dashboards and WebSocket channels.
"""
from __future__ import annotations
import asyncio
import time
from typing import Dict, Any, Optional
from collections import defaultdict

from app.core.logging import logger
from app.core.config import settings
from .realtime import broadcast_session_event

IS_FREE_TIER = getattr(settings, "LIVE_QUIZ_FREE_TIER_MODE", True)
DEFAULT_AGGREGATE_INTERVAL_MS = 500 if IS_FREE_TIER else 250


class SessionAggregateBuffer:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.question_id: Optional[str] = None
        self.answered_delta = 0
        self.option_deltas: Dict[str, int] = defaultdict(int)
        self.response_time_sum = 0
        self.response_time_count = 0
        self.flagged_count = 0
        self.active_count = 0
        self.last_flush = time.time()


class RealtimeAggregator:
    """
    Buffers answer submissions per session over a small time window before
    emitting a consolidated summary update.
    """

    def __init__(self, interval_ms: int = DEFAULT_AGGREGATE_INTERVAL_MS):
        self.interval_seconds = interval_ms / 1000.0
        self._buffers: Dict[str, SessionAggregateBuffer] = {}
        self._lock = asyncio.Lock()
        self._flush_tasks: Dict[str, asyncio.Task] = {}

        # Metrics
        self.total_events_absorbed = 0
        self.total_broadcasts_emitted = 0

    async def record_answer_event(
        self,
        session_id: str,
        question_id: str,
        selected_option_id: Optional[str],
        response_time_ms: int,
        is_flagged: bool = False,
    ) -> None:
        """Accumulates an answer submission event into the session's active aggregate buffer."""
        async with self._lock:
            self.total_events_absorbed += 1
            buf = self._buffers.get(session_id)
            if buf is None or buf.question_id != question_id:
                buf = SessionAggregateBuffer(session_id)
                buf.question_id = question_id
                self._buffers[session_id] = buf

            buf.answered_delta += 1
            if selected_option_id:
                buf.option_deltas[selected_option_id] += 1
            buf.response_time_sum += max(0, response_time_ms)
            buf.response_time_count += 1
            if is_flagged:
                buf.flagged_count += 1

            if session_id not in self._flush_tasks or self._flush_tasks[session_id].done():
                self._flush_tasks[session_id] = asyncio.create_task(
                    self._scheduled_flush(session_id)
                )

    async def _scheduled_flush(self, session_id: str):
        await asyncio.sleep(self.interval_seconds)
        await self.flush_session(session_id)

    async def flush_session(self, session_id: str) -> None:
        """Flushes buffered updates for a given session and broadcasts aggregate state."""
        async with self._lock:
            buf = self._buffers.pop(session_id, None)
            self._flush_tasks.pop(session_id, None)

        if not buf or buf.answered_delta == 0:
            return

        avg_time = (
            round(buf.response_time_sum / buf.response_time_count)
            if buf.response_time_count > 0 else 0
        )

        payload = {
            "session_id": session_id,
            "question_id": buf.question_id,
            "answered_count_delta": buf.answered_delta,
            "option_counts": dict(buf.option_deltas),
            "average_response_time_ms": avg_time,
            "flagged_count": buf.flagged_count,
            "timestamp": time.time(),
        }

        self.total_broadcasts_emitted += 1
        await broadcast_session_event(session_id, "session:aggregated_update", payload)

    async def flush_all(self):
        """Immediately flush all pending session buffers."""
        async with self._lock:
            session_ids = list(self._buffers.keys())
        for sid in session_ids:
            await self.flush_session(sid)

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "total_events_absorbed": self.total_events_absorbed,
            "total_broadcasts_emitted": self.total_broadcasts_emitted,
            "compression_ratio": round(
                self.total_events_absorbed / max(1, self.total_broadcasts_emitted), 2
            ),
        }


# Global singleton instance for live quiz subsystem
realtime_aggregator = RealtimeAggregator()
