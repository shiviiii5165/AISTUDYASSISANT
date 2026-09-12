"""
TeachGenie Lesson Planner — Stage Resource Intelligence Service
===============================================================
Master orchestrator unifying intent profiling, deterministic query planning,
multi-provider retrieval (YouTube Data API, Semantic Scholar, Crossref, arXiv,
Tavily, Wikipedia), URL verification, pedagogical two-phase ranking, and
durable multi-tier caching.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List

from .schemas import (
    ResourceIntentProfile,
    ResourceCandidate,
    ResourceType,
    YouTubeResponseOutput,
    YouTubeItemOutput,
    LearningMaterialsResponseOutput,
    LearningMaterialsCategoriesOutput,
    MaterialItemOutput,
    StageActionRecommendation
)
from .intent_profile import IntentProfileBuilder
from .query_planner import ResourceQueryPlanner
from .verification import ResourceVerificationEngine
from .resource_ranker import ResourceRanker
from .action_recommender import StageActionRecommender
from .cache import DurableResourceCache

# Import providers
from .providers.youtube_provider import YouTubeProvider
from .providers.semantic_scholar_provider import SemanticScholarProvider
from .providers.crossref_provider import CrossrefProvider
from .providers.arxiv_provider import ArxivProvider
from .providers.tavily_provider import TavilyProvider
from .providers.wikipedia_provider import WikipediaProvider
from .providers.trusted_domains import OFFICIAL_DOCS_DOMAINS, CODING_PRACTICE_DOMAINS, TUTORIAL_GUIDE_DOMAINS

logger = logging.getLogger("teachgenie.lesson_resources.service")


def _extract_stage_field(stage: Any, field: str, default: Any = None) -> Any:
    if stage is None:
        return default
    if isinstance(stage, dict):
        val = stage.get(field)
        return val if val is not None else default
    val = getattr(stage, field, None)
    return val if val is not None else default


class StageResourceIntelligenceService:
    """
    Unified intelligence service delivering teacher-calibrated learning resources.
    """

    @classmethod
    async def get_youtube_recommendations(
        cls,
        topic: str,
        stage: Any = None,
        learner_level: str = "B.Tech",
        language: str = "english",
        refresh: bool = False
    ) -> YouTubeResponseOutput:
        """
        Retrieves top-ranked, verified educational YouTube video recommendations.
        """
        stage_title = _extract_stage_field(stage, "title", topic)
        stage_id = _extract_stage_field(stage, "id", "default_stage")
        stage_desc = _extract_stage_field(stage, "description", "")
        archetype = _extract_stage_field(stage, "archetype", None)
        is_remedial = _extract_stage_field(stage, "is_remedial", False)
        concept_id = _extract_stage_field(stage, "concept_id", None)
        objectives = _extract_stage_field(stage, "learning_objectives", [])
        weaknesses = _extract_stage_field(stage, "weaknesses", [])

        # 1. Build rich intent profile
        profile = IntentProfileBuilder.build(
            roadmap_id="live_roadmap",
            stage_id=stage_id,
            topic=topic,
            stage_title=stage_title,
            stage_description=stage_desc,
            archetype=archetype,
            learner_level=learner_level,
            language=language,
            is_remedial=is_remedial,
            concept_id=concept_id,
            objectives=objectives,
            weaknesses=weaknesses
        )

        # 2. Check durable cache first (unless explicit refresh requested)
        cached_data = DurableResourceCache.get(profile, "youtube", bypass=refresh)
        if cached_data:
            logger.info(f"[ResourceService] Returning cached YouTube results for {profile.canonical_topic}")
            return YouTubeResponseOutput(**cached_data)

        # 3. Query planning & provider retrieval
        queries = ResourceQueryPlanner.plan_youtube_queries(profile)
        logger.info(f"[ResourceService] YouTube search queries for '{profile.canonical_topic}': {queries}")

        raw_candidates = await YouTubeProvider.fetch_candidates(queries, min_candidates=4, target_results=12)

        # 4. URL & metadata verification
        verified_candidates = ResourceVerificationEngine.filter_and_verify(raw_candidates)

        # 5. Two-phase pedagogical ranking with negative term rejection
        ranked = ResourceRanker.rank_candidates(
            verified_candidates,
            profile,
            min_relevance_threshold=0.50,
            max_results=4
        )

        # 6. Format items for output
        items: List[YouTubeItemOutput] = []
        for r in ranked:
            match_pct = int(round(r.final_score * 100)) if (r.final_score is not None and 0.0 <= r.final_score <= 1.0) else None
            items.append(YouTubeItemOutput(
                title=r.title,
                channel=r.author_or_channel,
                thumbnail=r.thumbnail_url,
                thumbnail_fallbacks=r.thumbnail_fallbacks,
                duration=r.duration_formatted or "12:00",
                url=r.canonical_url,
                relevance=r.final_score,
                match_percentage=match_pct,
                fit_label=r.fit_label,
                difficulty=r.difficulty,
                source="YouTube",
                reason=r.why_recommended,
                why_recommended=r.why_recommended,
                verification_level="PROVIDER_VERIFIED"
            ))

        diagnostic = {
            "canonical_topic": profile.canonical_topic,
            "stage_intent": profile.stage_intent.value,
            "queries_executed": queries,
            "raw_candidates_count": len(raw_candidates),
            "rejected_or_filtered_count": len(raw_candidates) - len(ranked),
            "top_returned_count": len(items),
            "cache_status": "bypass" if refresh else "miss"
        }
        logger.info(f"[ResourceService] YouTube diagnostic: {diagnostic}")

        response = YouTubeResponseOutput(
            enabled=True,
            status="active",
            canonical_topic=profile.canonical_topic,
            items=items,
            stage_intent=profile.stage_intent.value,
            diagnostic_info=diagnostic
        )

        # 7. Persist in durable cache
        if items:
            DurableResourceCache.set(profile, "youtube", response.dict())

        return response

    @classmethod
    async def get_learning_materials(
        cls,
        topic: str,
        stage: Any = None,
        learner_level: str = "B.Tech",
        language: str = "english",
        refresh: bool = False
    ) -> LearningMaterialsResponseOutput:
        """
        Retrieves verified academic references, research papers, coding practice, and official docs.
        """
        stage_title = _extract_stage_field(stage, "title", topic)
        stage_id = _extract_stage_field(stage, "id", "default_stage")
        stage_desc = _extract_stage_field(stage, "description", "")
        archetype = _extract_stage_field(stage, "archetype", None)
        is_remedial = _extract_stage_field(stage, "is_remedial", False)
        concept_id = _extract_stage_field(stage, "concept_id", None)
        objectives = _extract_stage_field(stage, "learning_objectives", [])
        weaknesses = _extract_stage_field(stage, "weaknesses", [])

        # 1. Build rich intent profile
        profile = IntentProfileBuilder.build(
            roadmap_id="live_roadmap",
            stage_id=stage_id,
            topic=topic,
            stage_title=stage_title,
            stage_description=stage_desc,
            archetype=archetype,
            learner_level=learner_level,
            language=language,
            is_remedial=is_remedial,
            concept_id=concept_id,
            objectives=objectives,
            weaknesses=weaknesses
        )

        # 2. Check durable cache
        cached_data = DurableResourceCache.get(profile, "learning_materials", bypass=refresh)
        if cached_data:
            logger.info(f"[ResourceService] Returning cached Learning Materials for {profile.canonical_topic}")
            return LearningMaterialsResponseOutput(**cached_data)

        # 3. Plan provider queries
        wiki_queries = ResourceQueryPlanner.plan_wikipedia_queries(profile)
        paper_queries = ResourceQueryPlanner.plan_paper_queries(profile)
        practice_queries = ResourceQueryPlanner.plan_practice_queries(profile)
        docs_queries = ResourceQueryPlanner.plan_docs_queries(profile)

        # 4. Concurrently fetch candidates from specialized providers
        tasks = [
            WikipediaProvider.fetch_references(wiki_queries, max_results=3),
            SemanticScholarProvider.fetch_papers(paper_queries, limit_per_query=4),
            ArxivProvider.fetch_preprints(paper_queries, max_results=3),
            TavilyProvider.fetch_domain_resources(
                query=docs_queries[0],
                include_domains=list(OFFICIAL_DOCS_DOMAINS.keys()),
                category_hint=ResourceType.OFFICIAL_DOCUMENTATION,
                max_results=3
            ),
            TavilyProvider.fetch_domain_resources(
                query=f"{profile.canonical_topic} tutorial guide",
                include_domains=list(TUTORIAL_GUIDE_DOMAINS.keys()),
                category_hint=ResourceType.GUIDE,
                max_results=3
            )
        ]

        # Fetch coding problems ONLY if topic is programming
        if profile.is_programming_topic and practice_queries:
            tasks.append(
                TavilyProvider.fetch_domain_resources(
                    query=practice_queries[0],
                    include_domains=list(CODING_PRACTICE_DOMAINS.keys()),
                    category_hint=ResourceType.CODING_PROBLEM,
                    max_results=3
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        wiki_candidates = results[0] if isinstance(results[0], list) else []
        s2_candidates = results[1] if isinstance(results[1], list) else []
        arxiv_candidates = results[2] if isinstance(results[2], list) else []
        docs_candidates = results[3] if isinstance(results[3], list) else []
        guide_candidates = results[4] if isinstance(results[4], list) else []
        coding_candidates = results[5] if len(results) > 5 and isinstance(results[5], list) else []

        all_candidates = (
            wiki_candidates + s2_candidates + arxiv_candidates +
            docs_candidates + guide_candidates + coding_candidates
        )

        # 5. Verify URLs and integrity
        verified = ResourceVerificationEngine.filter_and_verify(all_candidates)

        # 6. Rank candidates
        ranked = ResourceRanker.rank_candidates(verified, profile, min_relevance_threshold=0.45, max_results=18)

        # 7. Group into dynamic categories (strictly evidence-based)
        academic_refs: List[MaterialItemOutput] = []
        research_papers: List[MaterialItemOutput] = []
        practice_coding: List[MaterialItemOutput] = []
        documentation: List[MaterialItemOutput] = []
        guides_tutorials: List[MaterialItemOutput] = []

        def to_output(r: ResourceCandidate, cat_type: str) -> MaterialItemOutput:
            return MaterialItemOutput(
                id=r.id,
                title=r.title,
                url=r.canonical_url,
                description=r.description,
                source=r.source_name,
                type=cat_type,
                relevance=r.final_score,
                match_percentage=int(round(r.final_score * 100)) if (r.final_score is not None and 0.0 <= r.final_score <= 1.0) else None,
                fit_label=r.fit_label,
                difficulty=r.difficulty,
                publication_type=r.publication_type,
                peer_review_status=r.peer_review_status,
                venue=r.venue,
                year=r.year,
                citation_count=r.citation_count,
                open_access=r.open_access,
                doi=r.doi,
                arxiv_id=r.arxiv_id,
                why_recommended=r.why_recommended,
                verification_level=r.verification_levels[0].value if r.verification_levels else "PROVIDER_VERIFIED"
            )

        for r in ranked:
            if r.resource_type == ResourceType.ACADEMIC_REFERENCE:
                academic_refs.append(to_output(r, "academic_references"))
            elif r.resource_type == ResourceType.RESEARCH_PAPER:
                research_papers.append(to_output(r, "research_papers"))
            elif r.resource_type in (ResourceType.CODING_PROBLEM, ResourceType.PRACTICE_PROBLEM):
                if profile.is_programming_topic:
                    practice_coding.append(to_output(r, "practice_coding"))
            elif r.resource_type == ResourceType.OFFICIAL_DOCUMENTATION:
                documentation.append(to_output(r, "documentation"))
            else:
                guides_tutorials.append(to_output(r, "guides_tutorials"))

        # 8. Dynamic Visible Tabs: only display categories with verified results!
        visible_tabs: List[str] = []
        if academic_refs:
            visible_tabs.append("academic_references")
        if research_papers:
            visible_tabs.append("research_papers")
        if practice_coding and profile.is_programming_topic:
            visible_tabs.append("practice_coding")
        if documentation:
            visible_tabs.append("documentation")
        if guides_tutorials:
            visible_tabs.append("guides_tutorials")

        categories = LearningMaterialsCategoriesOutput(
            academic_references=academic_refs[:3],
            research_papers=research_papers[:3],
            practice_coding=practice_coding[:3],
            documentation=documentation[:3],
            guides_tutorials=guides_tutorials[:3],
            extra_learning_material=guides_tutorials[:3]  # backward compat alias
        )

        diagnostic = {
            "canonical_topic": profile.canonical_topic,
            "is_programming": profile.is_programming_topic,
            "visible_tabs": visible_tabs,
            "raw_count": len(all_candidates),
            "ranked_count": len(ranked),
            "cache_status": "bypass" if refresh else "miss"
        }
        logger.info(f"[ResourceService] Learning materials diagnostic: {diagnostic}")

        response = LearningMaterialsResponseOutput(
            enabled=True,
            status="active",
            canonical_topic=profile.canonical_topic,
            categories=categories,
            visible_tabs=visible_tabs,
            diagnostic_info=diagnostic
        )

        # Cache response
        if visible_tabs:
            DurableResourceCache.set(profile, "learning_materials", response.dict())

        return response

    @classmethod
    def get_action_recommendations(
        cls,
        topic: str,
        stage: Any = None,
        learner_level: str = "B.Tech"
    ) -> List[StageActionRecommendation]:
        stage_title = getattr(stage, "title", "") if stage else topic
        stage_id = getattr(stage, "id", "default_stage") if stage else "default_stage"
        stage_desc = getattr(stage, "description", "") if stage else ""
        archetype = getattr(stage, "archetype", None) if stage else None
        is_remedial = getattr(stage, "is_remedial", False) if stage else False
        objectives = getattr(stage, "learning_objectives", []) if stage else []
        weaknesses = getattr(stage, "weaknesses", []) if stage else []

        profile = IntentProfileBuilder.build(
            roadmap_id="live_roadmap",
            stage_id=stage_id,
            topic=topic,
            stage_title=stage_title,
            stage_description=stage_desc,
            archetype=archetype,
            learner_level=learner_level,
            is_remedial=is_remedial,
            objectives=objectives,
            weaknesses=weaknesses
        )

        return StageActionRecommender.evaluate_actions(profile)
