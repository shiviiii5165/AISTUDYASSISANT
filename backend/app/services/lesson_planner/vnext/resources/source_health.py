"""
Source Health & Circuit Breaker Tracking for External Resource Providers
========================================================================
Implements Section 20:
- Tracks provider latency percentiles (P50/P95), success rate, and rate limits.
- Enforces graceful degradation: if an external provider fails or slows down,
  the circuit trips and lesson planning continues with zero failure propagation.
"""

import time
import math
from typing import Dict, List, Optional
from datetime import datetime, timezone
from .contracts import ProviderHealthRecord


class SourceHealthTracker:
    """
    In-memory operational telemetry tracker for all resource providers.
    """

    _records: Dict[str, ProviderHealthRecord] = {}

    @classmethod
    def get_or_create(cls, provider: str) -> ProviderHealthRecord:
        if provider not in cls._records:
            cls._records[provider] = ProviderHealthRecord(
                provider=provider,
                total_calls=0,
                success_count=0,
                failure_count=0,
                success_rate=1.0,
                latencies_ms=[],
                latency_p50=0.0,
                latency_p95=0.0,
                rate_limit_status="healthy"
            )
        return cls._records[provider]

    @classmethod
    def start_call(cls, provider: str) -> float:
        cls.get_or_create(provider)
        return time.perf_counter()

    @classmethod
    def record_success(cls, provider: str, start_time: float) -> None:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        rec = cls.get_or_create(provider)
        rec.total_calls += 1
        rec.success_count += 1
        rec.latencies_ms.append(duration_ms)
        # Keep window of last 100 calls
        if len(rec.latencies_ms) > 100:
            rec.latencies_ms.pop(0)

        rec.success_rate = round(rec.success_count / rec.total_calls, 4)
        rec.last_success = datetime.now(timezone.utc).isoformat()

        # Update percentiles
        cls._update_percentiles(rec)

        # Reset rate limit / circuit breaker status if healthy
        if rec.success_rate >= 0.8:
            rec.rate_limit_status = "healthy"

    @classmethod
    def record_failure(cls, provider: str, start_time: float, error_msg: str) -> None:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        rec = cls.get_or_create(provider)
        rec.total_calls += 1
        rec.failure_count += 1
        rec.latencies_ms.append(duration_ms)
        if len(rec.latencies_ms) > 100:
            rec.latencies_ms.pop(0)

        rec.success_rate = round(rec.success_count / rec.total_calls, 4)
        rec.last_failure = f"{datetime.now(timezone.utc).isoformat()} ({error_msg[:80]})"

        cls._update_percentiles(rec)

        # Trip circuit breaker if consecutive failures drop success rate below 50% after at least 5 calls
        if rec.total_calls >= 5 and rec.success_rate < 0.5:
            rec.rate_limit_status = "circuit_broken"

    @classmethod
    def is_healthy(cls, provider: str) -> bool:
        """Returns False if circuit is broken."""
        rec = cls.get_or_create(provider)
        return rec.rate_limit_status != "circuit_broken"

    @classmethod
    def get_health(cls, provider: str) -> ProviderHealthRecord:
        return cls.get_or_create(provider)

    @classmethod
    def get_all_health(cls) -> Dict[str, ProviderHealthRecord]:
        return dict(cls._records)

    @classmethod
    def _update_percentiles(cls, rec: ProviderHealthRecord) -> None:
        if not rec.latencies_ms:
            rec.latency_p50 = 0.0
            rec.latency_p95 = 0.0
            return

        sorted_lat = sorted(rec.latencies_ms)
        n = len(sorted_lat)

        def pct(p: float) -> float:
            idx = int(math.ceil(p * n)) - 1
            idx = max(0, min(idx, n - 1))
            return sorted_lat[idx]

        rec.latency_p50 = round(pct(0.50), 2)
        rec.latency_p95 = round(pct(0.95), 2)
