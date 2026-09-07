"""
Image Service — Image Ranker
==============================
Scores and ranks candidate images from provider search results.
Criteria: keyword relevance, aspect ratio fit, resolution preference (≥1200px width).
"""
import re
from typing import List, Optional

from .models import CandidateImage


# Words that don't contribute to relevance scoring
_STOP_WORDS = {
    "with", "from", "that", "this", "into", "over", "under", "about",
    "scene", "showing", "system", "real", "photography", "professional",
    "image", "photo", "demonstration", "stock", "free", "download",
    "view", "background", "wallpaper", "abstract", "texture",
    "the", "and", "for", "are", "but", "not", "you", "all",
}

# Preferred minimum width for slide images
MIN_QUALITY_WIDTH = 1200


class ImageRanker:
    """
    Ranks candidate images by composite score:
      - Keyword relevance (0.0-1.0): how well description matches query
      - Aspect ratio fit (0.0-1.0): landscape bonus
      - Resolution (0.0-1.0): preference for ≥1200px width
    """

    @staticmethod
    def rank(
        candidates: List[CandidateImage],
        query: str,
        aspect_ratio: str = "landscape",
    ) -> Optional[CandidateImage]:
        """
        Score and return the best candidate, or None if no candidates.
        """
        if not candidates:
            return None

        scored = []
        for c in candidates:
            score = ImageRanker._score(c, query, aspect_ratio)
            c.relevance_score = score
            scored.append((score, c))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        best_score, best = scored[0]
        # Reject if score is very low (likely irrelevant)
        if best_score < 0.1:
            return None

        return best

    @staticmethod
    def rank_top_n(
        candidates: List[CandidateImage],
        query: str,
        n: int = 3,
        aspect_ratio: str = "landscape",
    ) -> List[CandidateImage]:
        """Return the top N candidates sorted by relevance score."""
        if not candidates:
            return []

        for c in candidates:
            c.relevance_score = ImageRanker._score(c, query, aspect_ratio)

        candidates.sort(key=lambda c: c.relevance_score, reverse=True)
        return candidates[:n]

    @staticmethod
    def _score(candidate: CandidateImage, query: str, aspect_ratio: str) -> float:
        """Compute composite score for a single candidate."""
        relevance = ImageRanker._keyword_relevance(query, candidate.description)
        aspect_fit = ImageRanker._aspect_ratio_score(candidate, aspect_ratio)
        resolution = ImageRanker._resolution_score(candidate)

        # Weighted composite: relevance is most important
        return 0.55 * relevance + 0.25 * aspect_fit + 0.20 * resolution

    @staticmethod
    def _keyword_relevance(query: str, description: str) -> float:
        """
        Compute keyword overlap ratio between query and image description.
        Returns ratio of matched meaningful query terms (0.0 to 1.0).
        """
        q_words = [re.sub(r"[^\w]", "", w.lower()) for w in query.split()]
        meaningful = [w for w in q_words if len(w) > 2 and w not in _STOP_WORDS]
        if not meaningful:
            return 0.5  # neutral if query has no meaningful terms

        desc_lower = description.lower()
        matches = sum(1 for w in meaningful if w in desc_lower)
        return matches / len(meaningful)

    @staticmethod
    def _aspect_ratio_score(candidate: CandidateImage, target: str) -> float:
        """Score how well the image's aspect ratio matches the target."""
        w, h = candidate.width, candidate.height
        if w == 0 or h == 0:
            return 0.5  # unknown dimensions → neutral

        ratio = w / h

        if target == "landscape":
            # Ideal: 16:9 ≈ 1.78, acceptable: 1.2-2.5
            if 1.5 <= ratio <= 2.0:
                return 1.0
            elif 1.2 <= ratio <= 2.5:
                return 0.7
            elif ratio > 1.0:
                return 0.4
            return 0.2  # portrait
        elif target == "portrait":
            if ratio < 0.8:
                return 1.0
            elif ratio < 1.0:
                return 0.7
            return 0.3
        else:  # square
            if 0.9 <= ratio <= 1.1:
                return 1.0
            return 0.5

    @staticmethod
    def _resolution_score(candidate: CandidateImage) -> float:
        """Score based on image resolution. Prefer ≥1200px width."""
        w = candidate.width
        if w == 0:
            return 0.5  # unknown → neutral
        if w >= MIN_QUALITY_WIDTH:
            return 1.0
        if w >= 800:
            return 0.7
        if w >= 400:
            return 0.4
        return 0.2
