"""Gate 2: class pre-filter, dense + BM25 retrieval, RRF and reranking.

The default embedder and reranker are deterministic and need no key or download.
TUTOR_RERANKER=cross-encoder switches to a sentence-transformers cross-encoder when that
package is installed; its threshold should be re-checked on real queries when enabled.
Dense retrieval uses LSA trained on the curriculum, plus the term map in language.py.
embed() is the 1536-d hashing vector used only for the tutor's reply cache.
"""
from __future__ import annotations

import math
import os
import re
import zlib
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional, Protocol, Sequence

import numpy as np

from app.core.logging import logger
from app.modules import store
from app.modules.curriculum.ncert_seed import build_chunks
from app.modules.learning_core import tutor_gates
from app.modules.rag_tutor.language import STOPWORDS_HI, normalize_terms

EMBEDDING_DIMENSIONS = 1536
STOPWORDS = frozenset("""
a an and are as at be but by can do does for from how i if in into is it its me my of on or
please so tell that the their them then this to was we what when where which who why will with
you your explain help understand solve find about mujhe kya hai kaise samjhao kyu kyun aur ka
ke ki ko se mein me nahi batao
""".split()) | STOPWORDS_HI


@dataclass(frozen=True)
class IndexedChunk:
    chunk_id: str
    concept_id: str
    class_level: int
    subject: str
    citation_id: str
    title: str
    block: str
    text: str
    search_terms: str

    @property
    def searchable(self) -> str:
        return f"{self.title} {self.search_terms} {self.text}"


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in normalize_terms(re.findall(r"[a-z0-9\u0900-\u097f]+", text.lower())):
        if raw not in STOPWORDS:
            tokens.append(raw[:-1] if len(raw) > 4 and raw.endswith("s") and raw.isascii() else raw)
    return tokens


def embed(text: str) -> tuple[float, ...]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    for token in tokenize(text):
        hashed = zlib.crc32(token.encode())
        vector[hashed % EMBEDDING_DIMENSIONS] += 1.0 if hashed & 1 << 31 else -1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return tuple(v / norm for v in vector)


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class BM25:
    def __init__(self, documents: dict[str, str], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.docs = {key: tokenize(text) for key, text in documents.items()}
        self.avg_length = sum(map(len, self.docs.values())) / max(1, len(self.docs))
        self.doc_freq: dict[str, int] = {}
        for tokens in self.docs.values():
            for token in set(tokens):
                self.doc_freq[token] = self.doc_freq.get(token, 0) + 1

    def idf(self, token: str) -> float:
        n = self.doc_freq.get(token, 0)
        return math.log(1 + (len(self.docs) - n + 0.5) / (n + 0.5))

    def score(self, query_tokens: Sequence[str], key: str) -> float:
        tokens = self.docs[key]
        total = 0.0
        for term in query_tokens:
            frequency = tokens.count(term)
            if frequency:
                norm = 1 - self.b + self.b * len(tokens) / self.avg_length
                total += self.idf(term) * frequency * (self.k1 + 1) / (frequency + self.k1 * norm)
        return total

    def rank(self, query: str, keys: Sequence[str]) -> list[str]:
        terms = tokenize(query)
        scored = [(self.score(terms, key), key) for key in keys]
        return [key for score, key in sorted(scored, key=lambda s: (-s[0], s[1])) if score > 0]


class LatentSemanticIndex:
    """Corpus-trained LSA embeddings: no model download and no PyTorch.

    Terms that appear in similar chunks land close together, so a query can match a chunk
    without sharing its words. It only knows this corpus's vocabulary, so unknown words
    give a zero vector rather than a guess.
    """

    def __init__(self, documents: dict[str, str], dimensions: int = 40) -> None:
        self.keys = list(documents)
        tokenized = [tokenize(documents[key]) for key in self.keys]
        self.vocabulary = {t: i for i, t in enumerate(sorted({t for doc in tokenized for t in doc}))}
        matrix = np.zeros((len(self.vocabulary), len(self.keys)))
        for column, doc in enumerate(tokenized):
            for token in doc:
                matrix[self.vocabulary[token], column] += 1
        frequency = (matrix > 0).sum(axis=1)
        self.idf = np.log(1 + len(self.keys) / np.maximum(frequency, 1))
        u, s, vt = np.linalg.svd(matrix * self.idf[:, None], full_matrices=False)
        k = min(dimensions, len(s))
        self.projection = u[:, :k] / np.maximum(s[:k], 1e-9)
        self.vectors = {key: self._unit(vt[:k, i]) for i, key in enumerate(self.keys)}

    @staticmethod
    def _unit(vector: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(vector)
        return vector / norm if norm else vector

    def embed(self, query: str) -> np.ndarray:
        counts = np.zeros(len(self.vocabulary))
        for token in tokenize(query):
            if token in self.vocabulary:
                counts[self.vocabulary[token]] += 1
        return self._unit(self.projection.T @ (counts * self.idf))

    def similarity(self, query: str, key: str) -> float:
        return float(self.embed(query) @ self.vectors[key])


class Reranker(Protocol):
    def score(self, query: str, chunks: Sequence[IndexedChunk]) -> dict[str, float]: ...


class CoverageReranker:
    """Scores 0-1 by the IDF-weighted share of query terms a chunk's concept covers."""

    SEMANTIC_MIN_COVERAGE = 0.34

    def __init__(self, bm25: BM25, lsa: Optional["LatentSemanticIndex"] = None) -> None:
        self.bm25 = bm25
        self.lsa = lsa

    def score(self, query: str, chunks: Sequence[IndexedChunk]) -> dict[str, float]:
        terms = set(tokenize(query))
        weights = {term: max(self.bm25.idf(term), 0.1) for term in terms}
        total = sum(weights.values())
        if not total:
            return {chunk.chunk_id: 0.0 for chunk in chunks}
        scores: dict[str, float] = {}
        for chunk in chunks:
            coverage = sum(w for t, w in weights.items() if t in set(tokenize(chunk.searchable))) / total
            # Semantics may lift a partial match, but can't rescue a mostly off-topic query.
            if self.lsa is not None and coverage >= self.SEMANTIC_MIN_COVERAGE:
                coverage = max(coverage, self.lsa.similarity(query, chunk.chunk_id))
            scores[chunk.chunk_id] = coverage
        return scores


class CrossEncoderReranker:
    MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def __init__(self) -> None:
        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(self.MODEL)

    def score(self, query: str, chunks: Sequence[IndexedChunk]) -> dict[str, float]:
        logits = self.model.predict([(query, chunk.searchable) for chunk in chunks])
        return {c.chunk_id: 1 / (1 + math.exp(-float(s))) for c, s in zip(chunks, logits)}


@dataclass(frozen=True)
class RetrievalResult:
    grounding: list[IndexedChunk]
    best_score: float
    candidates: int


class Index:
    def __init__(self, rows: Sequence[dict]) -> None:
        self.chunks = {row["chunk_id"]: IndexedChunk(**row) for row in rows}
        documents = {key: chunk.searchable for key, chunk in self.chunks.items()}
        self.bm25 = BM25(documents)
        self.lsa = LatentSemanticIndex(documents)
        self.reranker: Reranker = _build_reranker(self.bm25, self.lsa)

    def retrieve(self, query: str, student_class: int, subject: str | None = None) -> RetrievalResult:
        # Stage 1: hard metadata filter, applied before any search can see the chunk.
        allowed = [
            c for c in self.chunks.values()
            if c.class_level <= student_class and (subject is None or c.subject == subject)
        ]
        keys = [c.chunk_id for c in allowed]
        # Stage 2: dense + BM25 fused by RRF.
        query_vector = self.lsa.embed(query)
        similarity = {k: float(query_vector @ self.lsa.vectors[k]) for k in keys}
        dense = sorted((k for k in keys if similarity[k] > 0), key=lambda k: (-similarity[k], k))
        fused = tutor_gates.reciprocal_rank_fusion([dense[:30], self.bm25.rank(query, keys)[:30]])
        # Stage 3: rerank, then the strict threshold.
        by_id = {c.chunk_id: c for c in allowed}
        candidates = [by_id[k] for k in fused[:20]]
        scores = self.reranker.score(query, candidates) if candidates else {}
        passing = sorted(
            (c for c in candidates if scores[c.chunk_id] >= tutor_gates.TAU_REL),
            key=lambda c: (-scores[c.chunk_id], fused.index(c.chunk_id)),
        )[:3]
        return RetrievalResult(passing, max(scores.values(), default=0.0), len(candidates))


def _build_reranker(bm25: BM25, lsa: LatentSemanticIndex) -> Reranker:
    if os.environ.get("TUTOR_RERANKER", "").lower() == "cross-encoder":
        try:
            return CrossEncoderReranker()
        except Exception as exc:
            logger.error(f"[Tutor] Cross-encoder unavailable, using coverage reranker: {exc}")
    return CoverageReranker(bm25, lsa)


@lru_cache(maxsize=1)
def get_index() -> Index:
    rows = store.select("ncert_chunks")
    return Index(rows or build_chunks())
