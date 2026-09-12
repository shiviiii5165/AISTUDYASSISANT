"""
Resource Redundancy Detector & Minimum Effective Resource Set Optimizer
========================================================================
Implements Sections 17 & 18:
- Redundancy Detector: Computes semantic and surface similarity between candidate
  resources; prunes duplicates and keeps highest quality/authority item.
- Minimum Effective Resource Set: Enforces pedagogical limits to avoid learner
  cognitive overload:
  Default max per stage:
  - 1 Primary Explanation
  - 1 Alternative Representation / Explanation
  - 1 Practice / Implementation Resource
  - 1 Authoritative Reference (Standard / Course / Official Doc)
  - 1 Optional Deep Dive / Advanced Paper
"""

import re
from typing import List, Tuple, Set, Dict, Any
from ...schemas import UniversalResourceCard
from .contracts import ResourcePurpose


class RedundancyDetector:
    """
    Identifies redundant resources and enforces the minimum effective set.
    """

    SIMILARITY_THRESHOLD = 0.65  # Threshold for considering two resources redundant

    @classmethod
    def optimize_resource_set(
        cls,
        cards: List[UniversalResourceCard],
        stage_title: str = "",
        max_total: int = 5
    ) -> Tuple[List[UniversalResourceCard], int]:
        """
        Deduplicates candidate cards and selects the minimum effective set.
        Returns: (selected_cards, pruned_count)
        """
        if not cards:
            return [], 0

        # Sort incoming cards by quality score descending
        sorted_cards = sorted(cards, key=lambda c: c.quality_score, reverse=True)
        pruned_count = 0
        deduped: List[UniversalResourceCard] = []

        # 1. Redundancy Filtering (Section 18)
        for cand in sorted_cards:
            is_redundant = False
            for existing in deduped:
                sim = cls.compute_similarity(cand, existing)
                if sim >= cls.SIMILARITY_THRESHOLD:
                    # Same pedagogical niche & high semantic overlap -> prune lower quality candidate
                    is_redundant = True
                    pruned_count += 1
                    break

            if not is_redundant:
                deduped.append(cand)

        # 2. Minimum Effective Resource Set Selection (Section 17)
        # Partition into roles:
        # - Primary Explanation (video or course)
        # - Alternative Explanation / Representation (different provider/author)
        # - Practice (LeetCode, GFG, interactive)
        # - Authoritative Reference (Official docs, NPTEL course, standard)
        # - Deep Dive / Research (Paper, graduate lecture)
        selected: List[UniversalResourceCard] = []
        role_counts: Dict[str, int] = {
            "primary": 0,
            "alternative": 0,
            "practice": 0,
            "authoritative": 0,
            "deep_dive": 0
        }

        for card in deduped:
            role = cls._classify_card_role(card)

            # Cap each role
            if role == "primary" and role_counts["primary"] < 1:
                selected.append(card)
                role_counts["primary"] += 1
            elif role == "alternative" and role_counts["alternative"] < 1:
                selected.append(card)
                role_counts["alternative"] += 1
            elif role == "practice" and role_counts["practice"] < 1:
                selected.append(card)
                role_counts["practice"] += 1
            elif role == "authoritative" and role_counts["authoritative"] < 1:
                selected.append(card)
                role_counts["authoritative"] += 1
            elif role == "deep_dive" and role_counts["deep_dive"] < 1:
                selected.append(card)
                role_counts["deep_dive"] += 1
            elif len(selected) < max_total:
                # If room remains and card is sufficiently high quality, include it
                if card.quality_score >= 88:
                    selected.append(card)
            else:
                pruned_count += 1

        return selected[:max_total], pruned_count

    @classmethod
    def compute_similarity(cls, card_a: UniversalResourceCard, card_b: UniversalResourceCard) -> float:
        """
        Computes hybrid similarity between two resource cards based on:
        - URL domain / identifier
        - Title Jaccard token overlap
        - Resource type matching
        """
        # Exact URL or ID match
        if card_a.url and card_b.url and card_a.url.split("?")[0] == card_b.url.split("?")[0]:
            return 1.0

        if card_a.id == card_b.id:
            return 1.0

        # Token overlap of titles
        tokens_a = set(re.findall(r"\w{3,}", card_a.title.lower()))
        tokens_b = set(re.findall(r"\w{3,}", card_b.title.lower()))

        if not tokens_a or not tokens_b:
            return 0.0

        intersection = len(tokens_a.intersection(tokens_b))
        union = len(tokens_a.union(tokens_b))
        jaccard = intersection / float(union) if union > 0 else 0.0

        # If same resource type and same primary channel/provider, boost similarity
        type_match = 1.0 if card_a.type == card_b.type else 0.0
        auth_match = 1.0 if card_a.source_authority == card_b.source_authority else 0.0

        sim = (jaccard * 0.6) + (type_match * 0.2) + (auth_match * 0.2)
        return round(sim, 3)

    @classmethod
    def _classify_card_role(cls, card: UniversalResourceCard) -> str:
        """Assigns card into one of the 5 canonical minimum-effective set slots."""
        t = card.type.lower()
        purpose = getattr(card, "resource_purpose", "") or ""

        if "practice" in t or "problem" in t or purpose == ResourcePurpose.PRACTICE.value:
            return "practice"
        elif "docs" in t or "standard" in t or purpose == ResourcePurpose.AUTHORITATIVE_REFERENCE.value:
            return "authoritative"
        elif "course" in t or purpose == ResourcePurpose.COURSE_LECTURE.value:
            return "authoritative"
        elif "paper" in t or purpose in [ResourcePurpose.RESEARCH_OVERVIEW.value, ResourcePurpose.SEMINAL_RESEARCH.value, ResourcePurpose.DEEP_DIVE.value]:
            return "deep_dive"
        elif "alt" in card.why_recommended.lower() or purpose == ResourcePurpose.ALTERNATIVE_EXPLANATION.value:
            return "alternative"
        else:
            return "primary"
