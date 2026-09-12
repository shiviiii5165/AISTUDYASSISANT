"""
Resource Trust & Unified Aggregator Engine for Lesson Planner VNext
===================================================================
Implements Sections 2, 17–20, 26, & 28:
- Orchestrates the Unified Resource Intelligence Layer
- Queries specialized domain engines (YouTube, Courses, Coding, Docs, Academic)
- Deduplicates via RedundancyDetector and enforces Minimum Effective Resource Set
- Incorporates historical Outcome Signals where statistically significant
- Exposes complete Explainability (Why this resource? Why now? What objective? Why trusted? How long? What next?)
- Operates at ≈ $0 incremental LLM cost using deterministic provenance & metadata
"""

import logging
from typing import List, Dict, Any, Optional
from ...schemas import (
    RoadmapStage, UniversalResourceCard, CanonicalDomain,
    TeachingIntent, ProductMode, TopicVolatility
)
from .registry import ResourceNeedDetector
from .youtube_router import YouTubeSegmentRouter
from .course_engine import CourseIntelligenceEngine
from .academic_engine import AcademicEvidenceEngine
from .coding_engine import CodingResourceEngine
from .docs_engine import OfficialDocsEngine
from .redundancy_detector import RedundancyDetector
from .outcome_engine import ResourceOutcomeEngine
from .contracts import (
    ResourceIntent, ResourcePurpose, NormalizedResource,
    ResourceProvenance, ResourceQualityScore, ResourceSegment
)

logger = logging.getLogger("teachgenie.lesson_planner.trust_engine")


class ResourceTrustEngine:
    """
    Coordinates, deduplicates, and validates all stage resources into diverse,
    trusted Universal Resource Cards adhering to the Minimum Effective Resource Set.
    """

    @classmethod
    async def aggregate_stage_resources(
        cls,
        topic: str,
        stage: RoadmapStage,
        domain: CanonicalDomain,
        intent: TeachingIntent,
        learner_level: str = "B.Tech",
        mode: ProductMode = ProductMode.TEACHER_CLASSROOM,
        volatility: TopicVolatility = TopicVolatility.LOW
    ) -> List[UniversalResourceCard]:
        """
        Gathers, ranks, deduplicates, and validates stage resources.
        """
        # 1. Determine resource needs
        needed_types = ResourceNeedDetector.evaluate_stage_needs(
            stage=stage,
            domain=domain,
            intent=intent,
            learner_level=learner_level,
            mode=mode
        )

        raw_candidates: List[UniversalResourceCard] = []

        # 2. YouTube Segment Intelligence Engine
        if "youtube" in needed_types:
            try:
                yt_cards = await YouTubeSegmentRouter.route_segments(
                    topic=topic,
                    stage=stage,
                    learner_level=learner_level,
                    volatility=volatility
                )
                raw_candidates.extend(yt_cards)
            except Exception as e:
                logger.warning(f"[ResourceTrustEngine] YouTube routing error: {e}")

        # 3. Course Intelligence Engine (NPTEL / MIT OCW / SWAYAM)
        if "course" in needed_types:
            try:
                course_cards = CourseIntelligenceEngine.get_course_recommendations(
                    topic=topic,
                    stage=stage,
                    learner_level=learner_level,
                    domain=domain,
                    limit=2
                )
                raw_candidates.extend(course_cards)
            except Exception as e:
                logger.warning(f"[ResourceTrustEngine] Course intelligence error: {e}")

        # 4. Coding Practice & Reference Engine (GFG + LeetCode)
        if "coding" in needed_types:
            try:
                coding_cards = CodingResourceEngine.get_coding_resources(
                    topic=topic,
                    stage=stage,
                    learner_proficiency="developing"
                )
                raw_candidates.extend(coding_cards)
            except Exception as e:
                logger.warning(f"[ResourceTrustEngine] Coding resource error: {e}")

        # 5. Official Documentation Engine
        if "docs" in needed_types:
            try:
                docs_cards = OfficialDocsEngine.get_official_docs(
                    topic=topic,
                    stage=stage,
                    learner_level=learner_level
                )
                raw_candidates.extend(docs_cards)
            except Exception as e:
                logger.warning(f"[ResourceTrustEngine] Docs resource error: {e}")

        # 6. Academic Literature Engine
        if "research" in needed_types:
            try:
                paper_cards = await AcademicEvidenceEngine.get_scholarly_evidence(
                    topic=topic,
                    stage=stage,
                    learner_level=learner_level,
                    mode=mode
                )
                raw_candidates.extend(paper_cards)
            except Exception as e:
                logger.warning(f"[ResourceTrustEngine] Scholarly evidence error: {e}")

        # 7. Apply Outcome-Aware Ranking (Section 26)
        ranked_cards = ResourceOutcomeEngine.apply_outcome_aware_ranking(raw_candidates)

        # 8. Redundancy Filtering & Minimum Effective Resource Set (Sections 17 & 18)
        optimal_cards, pruned_count = RedundancyDetector.optimize_resource_set(
            cards=ranked_cards,
            stage_title=stage.title,
            max_total=5
        )

        # 9. Verify and enrich Explainability fields on every card (Section 28)
        for card in optimal_cards:
            cls._ensure_explainability(card, stage, topic)

        # Attach to stage for downstream consumption
        stage.universal_resources = optimal_cards
        return optimal_cards

    @classmethod
    def _ensure_explainability(
        cls,
        card: UniversalResourceCard,
        stage: RoadmapStage,
        topic: str
    ) -> None:
        """
        Enforces Section 28:
        Every resource must answer:
        - Why this resource?
        - Why now?
        - What exact objective does it cover?
        - Why is it trusted?
        - How long should the learner spend on it?
        - What should the learner do after it?
        """
        if not getattr(card, "why_now", None):
            card.why_now = f"Addresses the core concepts of {stage.title} during Stage {stage.sequence + 1}."

        if not getattr(card, "what_to_do_after", None):
            card.what_to_do_after = f"Attempt the Stage {stage.sequence + 1} checkpoint assessment."

        if not getattr(card, "resource_purpose", None):
            t = card.type.lower()
            if "video" in t:
                card.resource_purpose = ResourcePurpose.PRIMARY_EXPLANATION.value
            elif "course" in t:
                card.resource_purpose = ResourcePurpose.COURSE_LECTURE.value
            elif "problem" in t or "practice" in t:
                card.resource_purpose = ResourcePurpose.PRACTICE.value
            elif "docs" in t or "reference" in t:
                card.resource_purpose = ResourcePurpose.AUTHORITATIVE_REFERENCE.value
            elif "paper" in t:
                card.resource_purpose = ResourcePurpose.DEEP_DIVE.value
            else:
                card.resource_purpose = ResourcePurpose.PRIMARY_EXPLANATION.value
