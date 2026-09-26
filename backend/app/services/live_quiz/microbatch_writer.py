"""
Live Quiz Engine — Bounded Response Micro-Batch Writer
======================================================
High-concurrency answer ingestion with bounded queue buffering, multi-row DB
batching, authoritative commit futures, and graceful backpressure rejection.
"""
from __future__ import annotations
import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.logging import logger
from app.core.config import settings
from . import repository as repo

# Configurable defaults
# Free-tier mode allows longer batch window to minimize database round trips
IS_FREE_TIER = getattr(settings, "LIVE_QUIZ_FREE_TIER_MODE", True)
DEFAULT_BATCH_WINDOW_MS = 150 if IS_FREE_TIER else 50
DEFAULT_MAX_BATCH_SIZE = 100
DEFAULT_MAX_QUEUE_DEPTH = 5000


class BackpressureError(RuntimeError):
    """Raised when the micro-batch queue is saturated; client must retry with backoff."""
    def __init__(self, retry_after: int = 1):
        super().__init__("Server is currently experiencing high load; retry with backoff.")
        self.retry_after = retry_after


@dataclass
class PendingSubmission:
    response_row: Dict[str, Any]
    participant_delta: Dict[str, Any]
    stats_delta: Dict[str, Any]
    commit_future: asyncio.Future = field(default_factory=lambda: asyncio.get_event_loop().create_future())
    enqueued_at: float = field(default_factory=time.time)


class BoundedResponseMicroBatchWriter:
    """
    Coordinates response micro-batching across incoming student answer requests.
    Prevents per-response PostgreSQL transaction thrashing under high concurrency.
    """

    def __init__(
        self,
        batch_window_ms: int = DEFAULT_BATCH_WINDOW_MS,
        max_batch_size: int = DEFAULT_MAX_BATCH_SIZE,
        max_queue_depth: int = DEFAULT_MAX_QUEUE_DEPTH,
    ):
        self.batch_window_seconds = batch_window_ms / 1000.0
        self.max_batch_size = max_batch_size
        self.max_queue_depth = max_queue_depth

        self._queue: List[PendingSubmission] = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._is_running = True

        # Metrics & High-Water Mark Instrumentation (§2)
        self.total_enqueued = 0
        self.total_committed = 0
        self.total_batches = 0
        self.total_rejected = 0
        self._queue_depth_samples: List[int] = []
        self._batch_size_samples: List[int] = []
        self.queue_depth_max = 0
        self.batch_size_max = 0

    async def enqueue(
        self,
        response_row: Dict[str, Any],
        participant_delta: Dict[str, Any],
        stats_delta: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Enqueues an answer submission and awaits authoritative DB commit.
        Raises BackpressureError if the queue exceeds max_queue_depth.
        Records instantaneous queue high-water mark before any flush.
        """
        async with self._lock:
            if len(self._queue) >= self.max_queue_depth:
                self.total_rejected += 1
                raise BackpressureError(retry_after=1)

            loop = asyncio.get_running_loop()
            future = loop.create_future()

            submission = PendingSubmission(
                response_row=response_row,
                participant_delta=participant_delta,
                stats_delta=stats_delta,
                commit_future=future,
                enqueued_at=time.time(),
            )
            self._queue.append(submission)
            self.total_enqueued += 1

            # High-water mark instrumentation: measure depth immediately at enqueue time
            cur_depth = len(self._queue)
            self._queue_depth_samples.append(cur_depth)
            if cur_depth > self.queue_depth_max:
                self.queue_depth_max = cur_depth

            # If this is the first item or batch size is reached, ensure consumer loop
            if len(self._queue) >= self.max_batch_size:
                # Trigger immediate flush if not already active
                if self._flush_task is None or self._flush_task.done():
                    self._flush_task = asyncio.create_task(self._flush_batch())
            elif self._flush_task is None or self._flush_task.done():
                self._flush_task = asyncio.create_task(self._scheduled_flush())

        # Authoritative: Do NOT return ACK before the batch commits!
        return await future

    async def _scheduled_flush(self):
        """Wait for batch window before flushing to group rapid concurrent submissions."""
        await asyncio.sleep(self.batch_window_seconds)
        await self._flush_batch()

    async def _flush_batch(self):
        """Extract queued items and write them in a single batch operation."""
        async with self._lock:
            if not self._queue:
                return
            batch = self._queue[:self.max_batch_size]
            self._queue = self._queue[self.max_batch_size:]

        if not batch:
            return

        batch_size = len(batch)
        self._batch_size_samples.append(batch_size)
        if batch_size > self.batch_size_max:
            self.batch_size_max = batch_size

        try:
            # Execute batch DB persist in repository
            responses_to_write = [item.response_row for item in batch]
            participant_updates = [item.participant_delta for item in batch]
            stats_updates = [item.stats_delta for item in batch]

            saved_results = repo.batch_record_responses(
                response_list=responses_to_write,
                participant_updates=participant_updates,
                stats_updates=stats_updates,
            )

            self.total_committed += len(batch)
            self.total_batches += 1

            # Authoritative ACK: Resolve each submission future with its saved response
            for item in batch:
                row = item.response_row
                key = (row["session_id"], row["participant_id"], row["question_id"])
                res = saved_results.get(key, row)
                if not item.commit_future.done():
                    item.commit_future.set_result(res)

        except Exception as exc:
            logger.error(f"[MicroBatchWriter] Batch commit failed: {exc}")
            # Reject all futures in the failed batch so client retains in IndexedDB
            for item in batch:
                if not item.commit_future.done():
                    item.commit_future.set_exception(exc)

        # Trigger immediate next flush if more items remain in queue
        async with self._lock:
            if self._queue:
                self._flush_task = asyncio.create_task(self._flush_batch())

    def reset_metrics(self):
        """Reset sampling buffers between test tiers."""
        self._queue_depth_samples.clear()
        self._batch_size_samples.clear()
        self.queue_depth_max = 0
        self.batch_size_max = 0

    def get_metrics(self) -> Dict[str, Any]:
        import statistics
        q_depths = sorted(self._queue_depth_samples) if self._queue_depth_samples else [0]
        q_p50 = int(statistics.median(q_depths))
        q_p95 = q_depths[int(len(q_depths) * 0.95)] if q_depths else 0

        b_sizes = sorted(self._batch_size_samples) if self._batch_size_samples else [0]
        b_p50 = int(statistics.median(b_sizes))
        b_p95 = b_sizes[int(len(b_sizes) * 0.95)] if b_sizes else 0

        return {
            "queue_depth": len(self._queue),
            "queue_depth_p50": q_p50,
            "queue_depth_p95": q_p95,
            "queue_depth_max": self.queue_depth_max,
            "microbatch_size_p50": b_p50,
            "microbatch_size_p95": b_p95,
            "microbatch_size_max": self.batch_size_max,
            "max_queue_depth": self.max_queue_depth,
            "total_enqueued": self.total_enqueued,
            "total_committed": self.total_committed,
            "total_batches": self.total_batches,
            "total_rejected": self.total_rejected,
            "avg_batch_size": round(self.total_committed / max(1, self.total_batches), 1),
        }

    async def flush_all(self):
        """Flush any remaining items in queue immediately (useful for shutdown / tests)."""
        while True:
            async with self._lock:
                if not self._queue:
                    break
            await self._flush_batch()


# Global singleton instance for the live quiz subsystem
batch_writer = BoundedResponseMicroBatchWriter()
