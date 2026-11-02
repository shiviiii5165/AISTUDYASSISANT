"""Deterministic parts of Tutor Gates 1 and 2.

Gate 1 scrubs PII and blocks prompt injection. Gate 2 applies the grade pre-filter,
Reciprocal Rank Fusion and the relevance threshold. The retrievers and cross-encoder
are supplied by the caller as ranked ids and scores.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

TAU_REL = 0.72
RRF_K = 60

_PII_PATTERNS = (
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), "[PAN]"),
    (re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b"), "[AADHAAR]"),
    (re.compile(r"(?<!\d)(?:\+?91[ -]?)?[6-9]\d{9}(?!\d)"), "[PHONE]"),
)
_INJECTION_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(ignore|disregard|forget)\b.{0,30}\b(previous|prior|above|system|your)\b.{0,20}\b(instructions?|prompts?|rules?)\b",
        r"\b(reveal|show|print|repeat)\b.{0,30}\b(system prompt|instructions|answer key)\b",
        r"\byou are now\b|\bdeveloper mode\b|\bjailbreak\b",
        r"\b(give|tell|send|share)\b.{0,20}\b(me|us)?\b.{0,20}\b(exam|test|paper)\b.{0,20}\b(answers?|solutions?|leak)\b",
        r"\b(write|do|finish)\b.{0,20}\b(my|meri)\b.{0,20}\b(essay|assignment|homework)\b",
        r"\b(leaked?|cheat(ing)?)\b.{0,30}\b(paper|exam|test)\b",
    )
)


@dataclass(frozen=True)
class InputScreen:
    allowed: bool
    scrubbed_text: str
    reason: Optional[str] = None


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    class_level: int
    citation_id: str
    text: str


def screen_input(text: str) -> InputScreen:
    scrubbed = text
    for pattern, label in _PII_PATTERNS:
        scrubbed = pattern.sub(label, scrubbed)
    if any(pattern.search(scrubbed) for pattern in _INJECTION_PATTERNS):
        return InputScreen(False, scrubbed, "prompt_injection")
    return InputScreen(True, scrubbed)


def filter_by_class(chunks: Sequence[Chunk], student_class: int) -> list[Chunk]:
    return [chunk for chunk in chunks if chunk.class_level <= student_class]


def reciprocal_rank_fusion(rankings: Sequence[Sequence[str]], k: int = RRF_K) -> list[str]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda chunk_id: (-scores[chunk_id], chunk_id))


def select_grounding(
    fused_ids: Sequence[str],
    rerank_scores: Mapping[str, float],
    allowed: Sequence[Chunk],
    top_k: int = 3,
) -> list[Chunk]:
    """Return chunks that passed the filter and threshold; empty means safe fallback.

    A fused id missing from `allowed` is dropped, so a retriever that ignores the
    pre-filter cannot leak above-grade content.
    """
    by_id = {chunk.chunk_id: chunk for chunk in allowed}
    passing = [
        chunk_id
        for chunk_id in fused_ids
        if chunk_id in by_id and rerank_scores.get(chunk_id, 0.0) >= TAU_REL
    ]
    passing.sort(key=lambda chunk_id: -rerank_scores[chunk_id])
    return [by_id[chunk_id] for chunk_id in passing[:top_k]]


def citations_valid(cited_ids: Sequence[str], grounding: Sequence[Chunk]) -> bool:
    """Require at least one citation, and that every citation is from the grounding."""
    known = {chunk.citation_id for chunk in grounding}
    return bool(cited_ids) and all(citation in known for citation in cited_ids)
