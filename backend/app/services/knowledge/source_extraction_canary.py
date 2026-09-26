"""
Source Reading Internal Canary Telemetry & Metrics Tracker
===========================================================
Tracks, validates, and logs telemetry for canary requests.
Does NOT log credentials or sensitive user content.
Maintains granular counters:
- EXTRACTION_ADMITTED
- EXTRACTION_REJECTED
- SNIPPET_FALLBACK
- ACCESS_DENIED
- BUDGET_EXCEEDED
- NO_RELEVANT_PASSAGE
"""

import logging
import json
import urllib.parse
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

logger = logging.getLogger("learnbygenie.source_reading.canary")


class CanaryTelemetryEvent(BaseModel):
    source_domain: str
    extraction_method: str
    is_cached: bool
    quality_gate_decision: str  # "admitted" or "rejected_<reason>"
    passage_relevance_score: float
    snippet_fallback_retained: bool
    claim_support_score: float
    citation_validation: str  # "valid" or "invalid"
    extraction_latency_ms: float
    total_latency_ms: float
    credits_consumed: float
    failure_classification: Optional[str] = None


class SourceReadingCanaryMetrics:
    def __init__(self):
        self.total_requests: int = 0
        self.extraction_attempted: int = 0
        self.extraction_admitted: int = 0
        self.extraction_rejected: int = 0
        self.snippet_fallback: int = 0
        self.access_denied: int = 0
        self.budget_exceeded: int = 0
        self.no_relevant_passage: int = 0
        self.unsupported_claims: int = 0
        self.citation_failures: int = 0
        self.answer_degradations: int = 0
        self.provider_failures: int = 0
        self.tavily_credits_consumed: float = 0.0
        self.extraction_latencies: List[float] = []
        self.total_latencies: List[float] = []
        self.events: List[Dict[str, Any]] = []

    def record_event(
        self,
        url: str,
        extraction_method: str,
        is_cached: bool,
        admitted: bool,
        gate_reason: str,
        passage_relevance: float,
        snippet_fallback_retained: bool,
        claim_support: float,
        citation_valid: bool,
        extraction_latency_ms: float,
        total_latency_ms: float,
        credits_consumed: float,
        failure_classification: Optional[str] = None,
        is_provider_failure: bool = False
    ):
        self.total_requests += 1
        self.extraction_attempted += 1
        self.tavily_credits_consumed += credits_consumed
        self.extraction_latencies.append(extraction_latency_ms)
        self.total_latencies.append(total_latency_ms)

        if is_provider_failure:
            self.provider_failures += 1

        # Separate category tracking
        if admitted:
            self.extraction_admitted += 1
        else:
            self.extraction_rejected += 1

        if snippet_fallback_retained:
            self.snippet_fallback += 1

        reason_lower = gate_reason.lower()
        if failure_classification == "access_denied" or "403" in reason_lower or "denied" in reason_lower:
            self.access_denied += 1
        elif failure_classification == "budget_exceeded" or "budget" in reason_lower:
            self.budget_exceeded += 1
        elif failure_classification == "no_relevant_passage" or "no_passages" in reason_lower or "low_relevance" in reason_lower or "short" in reason_lower:
            self.no_relevant_passage += 1

        if claim_support < 0.70 and not snippet_fallback_retained:
            self.unsupported_claims += 1

        if not citation_valid:
            self.citation_failures += 1

        # Safe domain sanitization (strip credentials/query parameters)
        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc or "unknown_domain"
        except Exception:
            domain = "unknown_domain"

        event = CanaryTelemetryEvent(
            source_domain=domain,
            extraction_method=extraction_method,
            is_cached=is_cached,
            quality_gate_decision="admitted" if admitted else f"rejected_{gate_reason}",
            passage_relevance_score=round(passage_relevance, 2),
            snippet_fallback_retained=snippet_fallback_retained,
            claim_support_score=round(claim_support, 2),
            citation_validation="valid" if citation_valid else "invalid",
            extraction_latency_ms=round(extraction_latency_ms, 2),
            total_latency_ms=round(total_latency_ms, 2),
            credits_consumed=round(credits_consumed, 3),
            failure_classification=failure_classification
        )
        self.events.append(event.model_dump())

        # Structured log entry (zero credentials or sensitive user content)
        logger.info(f"[SOURCE_READING_CANARY] {json.dumps(event.model_dump())}")

    def get_summary(self) -> Dict[str, Any]:
        def _calc_p(vals: List[float], p: float) -> float:
            if not vals:
                return 0.0
            s = sorted(vals)
            idx = int(len(s) * (p / 100.0))
            return round(s[min(idx, len(s) - 1)], 2)

        return {
            "total_requests": self.total_requests,
            "extraction_attempted": self.extraction_attempted,
            "extraction_admitted": self.extraction_admitted,
            "extraction_rejected": self.extraction_rejected,
            "snippet_fallback_count": self.snippet_fallback,
            "access_denied_count": self.access_denied,
            "budget_exceeded_count": self.budget_exceeded,
            "no_relevant_passage_count": self.no_relevant_passage,
            "unsupported_claim_count": self.unsupported_claims,
            "citation_accuracy": 1.0 if self.citation_failures == 0 else round(1.0 - (self.citation_failures / max(1, self.total_requests)), 2),
            "answer_degradation_incidents": self.answer_degradations,
            "median_extraction_latency_ms": _calc_p(self.extraction_latencies, 50),
            "p95_extraction_latency_ms": _calc_p(self.extraction_latencies, 95),
            "median_total_latency_ms": _calc_p(self.total_latencies, 50),
            "p95_total_latency_ms": _calc_p(self.total_latencies, 95),
            "tavily_credits_consumed": round(self.tavily_credits_consumed, 2),
            "provider_failures": self.provider_failures,
        }

canary_tracker = SourceReadingCanaryMetrics()
