"""
Quiz Engine — Cache Key Design (§36)
====================================
Deterministic cache key for GENERATED quiz content.

The key intentionally accounts for every input that changes the questions:
source id(s) + source version, lesson/stage version, config, difficulty, count,
types, and language (§36).

CORRECTNESS GUARD (§36): personalized/adaptive quizzes must NEVER be cached
across users. `compute_cache_key` returns None whenever the quiz is adaptive or
draws on per-user signals (mastery, misconceptions, attempt history, a teach
session). A None key means "do not read or write the shared cache" — the caller
must treat caching as disabled for that quiz. This makes cross-user leakage of a
personalized quiz structurally impossible rather than dependent on remembering
to salt the key.
"""
from __future__ import annotations
import hashlib
import json
from typing import Optional, Dict, Any, List

from .schemas import QuizConfig


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def compute_cache_key(
    *,
    config: QuizConfig,
    source_type: str,
    source_ids: List[str],
    source_versions: Dict[str, int],       # source_id -> content version
    stage_id: Optional[str] = None,
    stage_version: Optional[int] = None,
    lesson_id: Optional[str] = None,
    lesson_version: Optional[int] = None,
    personalized: bool = False,            # mastery/misconception/history-driven
) -> Optional[str]:
    """
    Return a stable cache key, or None if the quiz must not be shared-cached.

    `personalized=True` OR `config.adaptive` forces None — an adaptive/personal
    quiz is unique to the user and its inputs are not captured here on purpose.
    """
    if personalized or config.adaptive:
        return None

    payload = {
        "v": 1,
        "source_type": source_type,
        "source_ids": sorted(source_ids),
        "source_versions": {k: source_versions.get(k, 1) for k in sorted(source_ids)},
        "stage_id": stage_id,
        "stage_version": stage_version,
        "lesson_id": lesson_id,
        "lesson_version": lesson_version,
        "config": {
            "question_count": config.question_count,
            "difficulty": config.difficulty.value,
            "types": sorted(t.value for t in config.types),
            "language": config.language,
        },
    }
    digest = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return f"quiz:{digest}"
