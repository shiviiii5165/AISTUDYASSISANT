"""
Teach Me Telemetry & Cost Observability Engine
==============================================
Tracks granular per-turn token expenditures, latency, cache hits, grounding scores,
and computes aggregate session benchmarks.
"""
from typing import Dict, Any, List, Optional
from .schemas import TurnTelemetry, LearningState


SESSION_TELEMETRY_LOGS: Dict[str, List[TurnTelemetry]] = {}


def record_turn_telemetry(
    session_id: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    latency_ms: float = 0.0,
    retrieved_chunks: int = 0,
    grounding_score: float = 1.0,
    model: str = "gemini-3.6-flash",
    provider: str = "gemini",
    cache_hit: bool = False,
) -> TurnTelemetry:
    """Logs a single turn's token expenditure and performance metrics."""
    total = input_tokens + output_tokens
    entry = TurnTelemetry(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total,
        latency_ms=round(latency_ms, 1),
        retrieved_chunks=retrieved_chunks,
        grounding_score=grounding_score,
        model=model,
        provider=provider,
        cache_hit=cache_hit,
    )

    if session_id not in SESSION_TELEMETRY_LOGS:
        SESSION_TELEMETRY_LOGS[session_id] = []
    SESSION_TELEMETRY_LOGS[session_id].append(entry)

    return entry


def get_session_aggregate_metrics(session_id: str) -> Dict[str, Any]:
    """
    Computes aggregate metrics:
    - total_turns
    - total_tokens
    - average_tokens_per_turn
    - average_latency_ms
    - cache_hit_rate
    - average_grounding_score
    """
    logs = SESSION_TELEMETRY_LOGS.get(session_id, [])
    if not logs:
        return {
            "total_turns": 0,
            "total_tokens": 0,
            "avg_tokens_per_turn": 0,
            "avg_latency_ms": 0.0,
            "cache_hit_rate": 0.0,
            "avg_grounding_score": 1.0,
        }

    total_turns = len(logs)
    total_tokens = sum(l.total_tokens for l in logs)
    total_latency = sum(l.latency_ms for l in logs)
    cache_hits = sum(1 for l in logs if l.cache_hit)
    avg_grounding = sum(l.grounding_score for l in logs) / total_turns

    return {
        "total_turns": total_turns,
        "total_tokens": total_tokens,
        "avg_tokens_per_turn": round(total_tokens / total_turns, 1),
        "avg_latency_ms": round(total_latency / total_turns, 1),
        "cache_hit_rate": round(cache_hits / total_turns, 2),
        "avg_grounding_score": round(avg_grounding, 2),
    }
