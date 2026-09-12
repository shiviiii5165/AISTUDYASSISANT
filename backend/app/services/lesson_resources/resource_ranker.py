"""
TeachGenie Lesson Planner — Resource Ranker & Pedagogical Scorer
================================================================
Two-phase ranker implementing:
1. Hard Negative Filtering & Minimum Concept Relevance Rejection.
2. 6-Factor Pedagogical Weighting (Concept 40%, Objective 20%, Intent 15%, Level 10%, Authority 10%, Engagement 5%).
3. Dynamic, evidence-grounded 'Why Recommended' synthesis.
"""

import re
import math
from typing import List, Tuple
from .schemas import ResourceCandidate, ResourceIntentProfile, StageIntent

import logging

logger = logging.getLogger("teachgenie.lesson_resources.ranker")

# Educational authority boosts for known high-reputation channels/publishers
AUTHORITY_BOOST_CHANNELS = {
    "nptel", "mit opencourseware", "stanford", "gate smashers", "neso academy",
    "freecodecamp", "abdul bari", "jenny's lectures", "khan academy", "3blue1brown",
    "krish naik", "corey schafer", "traversy media", "fireship", "academind"
}


class ResourceRanker:
    """
    Two-phase ranker: eliminates false positives, then scores by pedagogical fit.
    """

    @classmethod
    def rank_candidates(
        cls,
        candidates: List[ResourceCandidate],
        profile: ResourceIntentProfile,
        min_relevance_threshold: float = 0.50,
        max_results: int = 5
    ) -> List[ResourceCandidate]:
        """
        Filters out negative matches and ranks remaining candidates with admin/debug diagnostics.
        """
        survivors: List[ResourceCandidate] = []

        # ============================================================
        # PHASE 1: HARD REJECTION (Negative Filter + Minimum Concept Overlap)
        # ============================================================
        for c in candidates:
            text_corpus = f"{c.title} {c.description} {c.author_or_channel}".lower()

            # 1. Reject if matching negative terms (unless explicitly part of stage objectives)
            is_negative = False
            matched_neg = None
            for neg in profile.negative_terms:
                if neg.lower() in text_corpus:
                    # Verify it's not actually desired in stage objectives
                    if not any(neg.lower() in obj.lower() for obj in profile.learning_objectives):
                        is_negative = True
                        matched_neg = neg
                        break
            if is_negative:
                logger.info(
                    f"[RankingDiagnostic] REJECTED | title='{c.title[:45]}' | "
                    f"negative_filter_result='REJECTED: matched negative term \"{matched_neg}\"' | "
                    f"concept_relevance=0.0 | objective_coverage=0.0 | stage_intent=0.0 | "
                    f"learner_level=0.0 | authority=0.0 | engagement=0.0 | final_score=0.0"
                )
                continue

            # 2. Check concept overlap (Must contain canonical topic or at least 1 core concept)
            topic_words = [w for w in re.split(r"[\s\-—:]+", profile.canonical_topic.lower()) if len(w) > 3]
            has_topic_match = any(tw in text_corpus for tw in topic_words)
            has_concept_match = any(c_name.lower() in text_corpus for c_name in profile.concept_names)

            if not has_topic_match and not has_concept_match:
                logger.info(
                    f"[RankingDiagnostic] REJECTED | title='{c.title[:45]}' | "
                    f"negative_filter_result='REJECTED: no topic or concept overlap' | "
                    f"concept_relevance=0.0 | objective_coverage=0.0 | stage_intent=0.0 | "
                    f"learner_level=0.0 | authority=0.0 | engagement=0.0 | final_score=0.0"
                )
                continue

            survivors.append(c)

        # ============================================================
        # PHASE 2: 6-FACTOR PEDAGOGICAL RANKING
        # ============================================================
        scored: List[Tuple[float, ResourceCandidate]] = []

        for c in survivors:
            text_corpus = f"{c.title} {c.description}".lower()

            # 1. Concept Relevance (40%)
            matched_concepts = [c_name for c_name in profile.concept_names if c_name.lower() in text_corpus]
            topic_matches = sum(1 for tw in [w for w in re.split(r"\s+", profile.canonical_topic.lower()) if len(w) > 3] if tw in text_corpus)
            concept_score = min(1.0, 0.4 * (topic_matches > 0) + 0.6 * (len(matched_concepts) / max(1, len(profile.concept_names[:4]))))

            # 2. Objective Coverage (20%)
            matched_objs = [obj for obj in profile.learning_objectives if any(w in text_corpus for w in obj.lower().split() if len(w) > 4)]
            objective_score = min(1.0, len(matched_objs) / max(1, len(profile.learning_objectives)))

            # 3. Stage Intent Match (15%)
            intent_score = 0.70  # baseline
            if profile.stage_intent == StageIntent.REMEDIAL:
                # Boost worked examples, solved problems, step-by-step
                if any(k in text_corpus for k in ["example", "solved", "practice", "step by step", "explanation", "recap"]):
                    intent_score = 1.0
                elif any(k in text_corpus for k in ["advanced", "research", "survey"]):
                    intent_score = 0.50
            elif profile.stage_intent == StageIntent.PRACTICE:
                if any(k in text_corpus for k in ["practice", "problem", "leetcode", "exercise", "question", "quiz"]):
                    intent_score = 1.0
            elif profile.stage_intent == StageIntent.CONCEPT_LEARNING:
                if any(k in text_corpus for k in ["introduction", "concept", "explained", "tutorial", "foundation"]):
                    intent_score = 0.95

            # 4. Learner Level Match (10%)
            level_score = 0.85
            if "beginner" in profile.learner_level.lower() or "class" in profile.learner_level.lower():
                if any(k in text_corpus for k in ["advanced", "complex", "formal proof", "asymptotic"]):
                    level_score = 0.60
                elif any(k in text_corpus for k in ["basic", "introduction", "beginner", "simple"]):
                    level_score = 1.0

            # 5. Authority Score (10%)
            authority_score = 0.75
            author_lower = c.author_or_channel.lower()
            if any(ab in author_lower for ab in AUTHORITY_BOOST_CHANNELS):
                authority_score = 1.0
            elif c.peer_review_status == "Peer-reviewed":
                authority_score = 0.95
            elif c.resource_type.value == "OFFICIAL_DOCUMENTATION":
                authority_score = 1.0

            # 6. Engagement / Citations (5%)
            engagement_score = 0.50
            if c.citation_count:
                engagement_score = min(1.0, 0.5 + (math.log10(max(1, c.citation_count)) / 6.0))
            elif c.view_count:
                engagement_score = min(1.0, 0.5 + (math.log10(max(1, c.view_count)) / 12.0))

            # Final Weighted Score
            final_score = (
                0.40 * concept_score +
                0.20 * objective_score +
                0.15 * intent_score +
                0.10 * level_score +
                0.10 * authority_score +
                0.05 * engagement_score
            )

            # Assign score breakdown to candidate
            c.concept_relevance = round(concept_score, 2)
            c.objective_coverage = round(objective_score, 2)
            c.stage_intent_match = round(intent_score, 2)
            c.learner_level_match = round(level_score, 2)
            c.authority_score = round(authority_score, 2)
            c.engagement_score = round(engagement_score, 2)
            c.final_score = round(final_score, 2)

            # Fit label
            if final_score >= 0.82:
                c.fit_label = "Excellent fit"
            elif final_score >= 0.68:
                c.fit_label = "Strong fit"
            else:
                c.fit_label = "Useful supplement"

            # Dynamic Why Recommended explanation
            c.why_recommended = cls._generate_why_recommended(c, profile, matched_concepts)

            # Log ranking diagnostics in admin/debug mode
            logger.info(
                f"[RankingDiagnostic] SCORED | title='{c.title[:45]}' | "
                f"negative_filter_result='PASSED' | "
                f"concept_relevance={c.concept_relevance} | "
                f"objective_coverage={c.objective_coverage} | "
                f"stage_intent={c.stage_intent_match} | "
                f"learner_level={c.learner_level_match} | "
                f"authority={c.authority_score} | "
                f"engagement={c.engagement_score} | "
                f"final_score={c.final_score} | "
                f"fit_label='{c.fit_label}'"
            )

            if final_score >= min_relevance_threshold:
                scored.append((final_score, c))

        # Sort descending by final score
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:max_results]]

    @classmethod
    def _generate_why_recommended(
        cls,
        candidate: ResourceCandidate,
        profile: ResourceIntentProfile,
        matched_concepts: List[str]
    ) -> str:
        """
        Produces a crisp, honest pedagogical justification tied to real concepts.
        """
        concepts_str = ", ".join(matched_concepts[:3]) if matched_concepts else profile.canonical_topic

        if profile.stage_intent == StageIntent.REMEDIAL:
            if profile.learner_weaknesses:
                return (
                    f"Directly addresses your remedial focus on {profile.learner_weaknesses[0]} "
                    f"with concrete walkthroughs of {concepts_str}."
                )
            return f"Provides step-by-step solved examples of {concepts_str} to reinforce foundational understanding."

        if candidate.resource_type.value == "OFFICIAL_DOCUMENTATION":
            return f"Official authoritative standard documentation and syntax reference for {concepts_str}."

        if candidate.resource_type.value == "CODING_PROBLEM":
            return f"Hands-on interactive practice problem to reinforce implementation of {concepts_str}."

        if candidate.resource_type.value == "RESEARCH_PAPER":
            if candidate.peer_review_status == "Peer-reviewed":
                return f"Peer-reviewed publication ({candidate.venue or 'Journal'}) providing foundational theoretical analysis of {concepts_str}."
            return f"Scholarly research literature analyzing principles and formal models of {concepts_str}."

        return f"Clear pedagogical explanation covering {concepts_str} aligned with your {profile.learner_level} learning objectives."
