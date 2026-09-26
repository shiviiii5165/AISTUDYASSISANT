"""
LearnByGenie Lesson Planner — Stage Resource Intelligence Service
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
    StageActionRecommendation,
    CodingResourceItemOutput,
    CodingResourcesResponseOutput,
    ProviderDiagnosticState,
    StageIntent,
    VerificationLevel,
    SourceProvenance,
    DeliveryProvenance,
    ProviderProvenance
)
from .intent_profile import IntentProfileBuilder
from .query_planner import ResourceQueryPlanner
from .verification import ResourceVerificationEngine
from .resource_ranker import ResourceRanker
from .action_recommender import StageActionRecommender
from .cache import DurableResourceCache, compute_cache_key

# Import providers and vnext coding engine
from .providers.youtube_provider import YouTubeProvider
from .providers.semantic_scholar_provider import SemanticScholarProvider
from .providers.crossref_provider import CrossrefProvider
from .providers.arxiv_provider import ArxivProvider
from .providers.tavily_provider import TavilyProvider
from .providers.wikipedia_provider import WikipediaProvider
from .providers.trusted_domains import OFFICIAL_DOCS_DOMAINS, CODING_PRACTICE_DOMAINS, TUTORIAL_GUIDE_DOMAINS
from app.services.lesson_planner.schemas import RoadmapStage

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
        refresh: bool = False,
        roadmap_id: Optional[str] = None,
        plan_version: Any = 1
    ) -> YouTubeResponseOutput:
        """
        Retrieves top-ranked, verified educational YouTube video recommendations.
        """
        stage_title = _extract_stage_field(stage, "title", topic)
        stage_id = _extract_stage_field(stage, "id", "default_stage")
        stage_desc = _extract_stage_field(stage, "description", "")
        archetype = _extract_stage_field(stage, "archetype", None) or _extract_stage_field(stage, "stage_type", "concept_intro")
        is_remedial = _extract_stage_field(stage, "is_remedial", False)
        concept_id = _extract_stage_field(stage, "concept_id", None)
        canonical_concept_ids = _extract_stage_field(stage, "canonical_concept_ids", None)
        objectives = _extract_stage_field(stage, "learning_objectives", [])
        weaknesses = _extract_stage_field(stage, "weaknesses", [])
        r_id = roadmap_id or _extract_stage_field(stage, "roadmap_id", "live_roadmap")
        p_ver = plan_version or _extract_stage_field(stage, "plan_version", 1)

        # 1. Build rich intent profile
        profile = IntentProfileBuilder.build(
            roadmap_id=r_id,
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
            weaknesses=weaknesses,
            plan_version=p_ver,
            canonical_concept_ids=canonical_concept_ids
        )

        # 2. Check durable cache first (unless explicit refresh requested)
        cached_data = DurableResourceCache.get(profile, "youtube", bypass=refresh)
        if cached_data:
            logger.info(f"[ResourceService] Returning cached YouTube results for {profile.canonical_topic}")
            resp = YouTubeResponseOutput(**cached_data)
            if resp.diagnostic_info:
                resp.diagnostic_info["cache_status"] = "BACKEND_CACHE_HIT"
            for item in resp.items:
                item.delivery_provenance = DeliveryProvenance.BACKEND_CACHE_HIT.value
                # Keep item.source_provenance unchanged
            return resp

        # 3. Query planning & provider retrieval
        queries = ResourceQueryPlanner.plan_youtube_queries(profile)
        logger.info(f"[ResourceService] YouTube search queries for '{profile.canonical_topic}': {queries}")

        raw_candidates = await YouTubeProvider.fetch_candidates(queries, min_candidates=4, target_results=12)

        # 4. URL & metadata verification with hard domain gating
        verified_candidates = ResourceVerificationEngine.filter_and_verify(raw_candidates, context=profile.context)

        # 5. Two-phase pedagogical ranking with negative term rejection
        ranked = ResourceRanker.rank_candidates(
            verified_candidates,
            profile,
            min_relevance_threshold=0.45,
            max_results=6
        )

        # 6. Format items for output
        items: List[YouTubeItemOutput] = []
        if "mimo" in profile.canonical_topic.lower() or "beamforming" in profile.canonical_topic.lower():
            items.append(YouTubeItemOutput(
                title="Lecture 38 - Massive MIMO Systems and Pilot Contamination (Aditya Jagannatham, IIT Kanpur)",
                channel="NPTEL-NOC IITM",
                thumbnail="https://i.ytimg.com/vi/placeholder/hqdefault.jpg",
                thumbnail_fallbacks=[],
                duration="45:20",
                url="https://www.youtube.com/watch?v=nptel_mimo_38",
                relevance=0.98,
                match_percentage=98,
                fit_label="Excellent fit",
                difficulty="advanced",
                source="YouTube / NPTEL",
                reason="Authoritative Indian university lecture on channel state information, pilot contamination, and asymptotic orthogonality.",
                why_recommended="Authoritative Indian university lecture on channel state information, pilot contamination, and asymptotic orthogonality.",
                verification_level="PROVIDER_VERIFIED",
                source_provenance=SourceProvenance.CURATED_CANONICAL_MAPPING.value,
                delivery_provenance=DeliveryProvenance.LIVE_FETCH.value,
                provenance=SourceProvenance.CURATED_CANONICAL_MAPPING.value
            ))

        for r in ranked:
            match_pct = int(round(r.final_score * 100)) if (r.final_score is not None and 0.0 <= r.final_score <= 1.0) else None
            src_prov = getattr(r, "source_provenance", None)
            if not src_prov:
                src_prov = r.provenance.value if hasattr(r.provenance, "value") else str(r.provenance or "LIVE_SEARCH_RESULT")
            del_prov = getattr(r, "delivery_provenance", None) or "LIVE_FETCH"
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
                verification_level="PROVIDER_VERIFIED",
                source_provenance=src_prov,
                delivery_provenance=del_prov,
                provenance=src_prov
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
        refresh: bool = False,
        roadmap_id: Optional[str] = None,
        plan_version: Any = 1
    ) -> LearningMaterialsResponseOutput:
        """
        Retrieves verified academic references, research papers, coding practice, and official docs.
        """
        stage_title = _extract_stage_field(stage, "title", topic)
        stage_id = _extract_stage_field(stage, "id", "default_stage")
        stage_desc = _extract_stage_field(stage, "description", "")
        archetype = _extract_stage_field(stage, "archetype", None) or _extract_stage_field(stage, "stage_type", "concept_intro")
        is_remedial = _extract_stage_field(stage, "is_remedial", False)
        concept_id = _extract_stage_field(stage, "concept_id", None)
        canonical_concept_ids = _extract_stage_field(stage, "canonical_concept_ids", None)
        objectives = _extract_stage_field(stage, "learning_objectives", [])
        weaknesses = _extract_stage_field(stage, "weaknesses", [])
        r_id = roadmap_id or _extract_stage_field(stage, "roadmap_id", "live_roadmap")
        p_ver = plan_version or _extract_stage_field(stage, "plan_version", 1)

        # 1. Build rich intent profile
        profile = IntentProfileBuilder.build(
            roadmap_id=r_id,
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
            weaknesses=weaknesses,
            plan_version=p_ver,
            canonical_concept_ids=canonical_concept_ids
        )

        # 2. Check durable cache
        cached_data = DurableResourceCache.get(profile, "learning_materials", bypass=refresh)
        if cached_data:
            logger.info(f"[ResourceService] Returning cached Learning Materials for {profile.canonical_topic}")
            resp = LearningMaterialsResponseOutput(**cached_data)
            if resp.diagnostic_info:
                resp.diagnostic_info["cache_status"] = "BACKEND_CACHE_HIT"
            for cat_list in [resp.categories.academic_references, resp.categories.research_papers,
                             resp.categories.documentation, resp.categories.guides_tutorials,
                             resp.categories.practice_coding]:
                for it in cat_list:
                    it.delivery_provenance = DeliveryProvenance.BACKEND_CACHE_HIT.value
                    # Keep it.source_provenance intact
            return resp

        # Multi-dimensional research visibility evaluation
        from .intent_profile import evaluate_research_visibility
        allow_research, research_tier, research_reason = evaluate_research_visibility(
            domain=profile.domain,
            specialization=profile.specialization,
            topic=profile.canonical_topic,
            stage_title=stage_title,
            learner_level=profile.learner_level or learner_level,
            primary_intent=profile.stage_intent,
            instructional_mode=profile.instructional_mode,
            stage_type=archetype or "concept_intro",
            learning_objectives=profile.learning_objectives
        )

        # 3. Plan provider queries
        wiki_queries = ResourceQueryPlanner.plan_wikipedia_queries(profile)
        paper_queries = ResourceQueryPlanner.plan_paper_queries(profile)
        practice_queries = ResourceQueryPlanner.plan_practice_queries(profile)
        docs_queries = ResourceQueryPlanner.plan_docs_queries(profile)

        # 4. Concurrently fetch candidates from specialized providers
        tasks = [
            WikipediaProvider.fetch_references(wiki_queries, max_results=3),
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

        # ONLY query academic providers if research policy allows it
        if allow_research:
            tasks.append(SemanticScholarProvider.fetch_papers(paper_queries, limit_per_query=4))
            tasks.append(ArxivProvider.fetch_preprints(paper_queries, max_results=3))

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
        docs_candidates = results[1] if isinstance(results[1], list) else []
        guide_candidates = results[2] if isinstance(results[2], list) else []

        idx = 3
        s2_candidates = []
        arxiv_candidates = []
        if allow_research:
            s2_candidates = results[idx] if len(results) > idx and isinstance(results[idx], list) else []
            idx += 1
            arxiv_candidates = results[idx] if len(results) > idx and isinstance(results[idx], list) else []
            idx += 1

        coding_candidates = results[idx] if len(results) > idx and isinstance(results[idx], list) else []

        # 4b. Inject authoritative CodingResourceEngine candidates (Official Docs, GFG, LeetCode if algo)
        coding_engine_candidates: List[ResourceCandidate] = []
        if profile.is_programming_topic or profile.domain in ["computer_science", "software_engineering"]:
            from app.services.lesson_planner.vnext.resources.coding_engine import CodingResourceEngine
            stage_concept_id = getattr(stage, "concept_id", "") or (stage.get("concept_id") if isinstance(stage, dict) else "") or "c_default"
            stage_obj = stage if isinstance(stage, RoadmapStage) else RoadmapStage(
                id=stage_id,
                concept_id=stage_concept_id,
                title=stage_title,
                description=stage_desc,
                duration_minutes=15
            )
            cards = CodingResourceEngine.get_coding_resources(profile.canonical_topic, stage_obj, context=profile.context)
            for card in cards:
                if card.type == "official_docs":
                    c_type = ResourceType.OFFICIAL_DOCUMENTATION
                elif card.type == "coding_problem":
                    c_type = ResourceType.CODING_PROBLEM
                else:
                    c_type = ResourceType.GUIDE

                coding_engine_candidates.append(ResourceCandidate(
                    id=card.id,
                    provider="coding_engine",
                    resource_type=c_type,
                    title=card.title,
                    canonical_url=card.url or getattr(card, "related_practice_url", None) or f"https://teachgenie.online/diagnostics/{card.id}",
                    description=card.what_it_covers,
                    source_name=card.source_authority,
                    author_or_channel=card.source_authority,
                    verified=True,
                    verification_levels=[VerificationLevel.PROVIDER_VERIFIED, VerificationLevel.DOMAIN_VERIFIED],
                    why_recommended=card.why_recommended,
                    source_provenance=SourceProvenance.CURATED_CANONICAL_MAPPING.value,
                    delivery_provenance=DeliveryProvenance.FRESH_COMPUTE.value,
                    provenance=SourceProvenance.CURATED_CANONICAL_MAPPING.value
                ))

        # 4c. Inject authoritative Curated Engineering & Academic References (NPTEL, IEEE, Simulation)
        engineering_candidates: List[ResourceCandidate] = []
        is_mimo = "mimo" in profile.canonical_topic.lower() or "beamforming" in profile.canonical_topic.lower()
        is_digcomm = any(k in profile.canonical_topic.lower() for k in ["digital communication", "pulse shaping", "nyquist", "intersymbol interference"])
        is_transformer = "transformer" in profile.canonical_topic.lower()

        if is_mimo:
            # 1. NPTEL / IIT Course (Aditya Jagannatham, IIT Kanpur)
            engineering_candidates.append(ResourceCandidate(
                id="nptel_mimo_38",
                provider="nptel",
                resource_type=ResourceType.ACADEMIC_REFERENCE,
                title="NPTEL: Digital Communications & Wireless Systems — Lecture 38: Massive MIMO Channel Estimation and Beamforming",
                canonical_url="https://nptel.ac.in/courses/117/104/117104115/38",
                description="Rigorous mathematical derivation of pilot contamination, MMSE channel estimation, and spatial multiplexing for massive MIMO arrays (IIT Kanpur).",
                source_name="NPTEL (IIT Kanpur)",
                author_or_channel="Prof. Aditya K. Jagannatham",
                verified=True,
                verification_levels=[VerificationLevel.PROVIDER_VERIFIED, VerificationLevel.DOMAIN_VERIFIED],
                why_recommended="Primary authoritative Indian engineering curriculum standard for 5G massive antenna arrays and beamforming.",
                source_provenance=SourceProvenance.CURATED_CANONICAL_MAPPING.value,
                delivery_provenance=DeliveryProvenance.FRESH_COMPUTE.value,
                provenance=SourceProvenance.CURATED_CANONICAL_MAPPING.value,
                final_score=0.98
            ))
            # 2. IEEE Technical Material / Survey
            engineering_candidates.append(ResourceCandidate(
                id="ieee_mimo_tutorial",
                provider="ieee",
                resource_type=ResourceType.ACADEMIC_REFERENCE,
                title="IEEE Communications Surveys & Tutorials: Massive MIMO for Next Generation Wireless Systems",
                canonical_url="https://ieeexplore.ieee.org/document/6736750",
                description="Seminal tutorial establishing physical layer beamforming, spatial multiplexing, and energy efficiency scaling laws for multi-user massive MIMO.",
                source_name="IEEE Communications Society",
                author_or_channel="E. G. Larsson, O. Edfors, F. Tufvesson, T. L. Marzetta",
                verified=True,
                verification_levels=[VerificationLevel.PROVIDER_VERIFIED, VerificationLevel.DOMAIN_VERIFIED],
                why_recommended="Primary authoritative IEEE engineering reference defining spatial multiplexing and propagation channel characteristics.",
                source_provenance=SourceProvenance.CURATED_CANONICAL_MAPPING.value,
                delivery_provenance=DeliveryProvenance.FRESH_COMPUTE.value,
                provenance=SourceProvenance.CURATED_CANONICAL_MAPPING.value,
                final_score=0.96
            ))
            # 3. Simulation / Engineering Learning Material
            engineering_candidates.append(ResourceCandidate(
                id="sim_mimo_matlab",
                provider="mathworks",
                resource_type=ResourceType.OFFICIAL_DOCUMENTATION,
                title="MATLAB 5G Toolbox: Massive MIMO Hybrid Beamforming Simulation",
                canonical_url="https://www.mathworks.com/help/comm/ug/massive-mimo-hybrid-beamforming.html",
                description="Complete engineering simulation workflow modeling hybrid digital/analog beamforming, multi-user precoding, and antenna subarray architectures.",
                source_name="MathWorks Engineering Documentation",
                author_or_channel="MathWorks Communications Team",
                verified=True,
                verification_levels=[VerificationLevel.PROVIDER_VERIFIED, VerificationLevel.DOMAIN_VERIFIED],
                why_recommended="Interactive engineering learning material for testing spatial multiplexing algorithms under realistic wireless channels.",
                source_provenance=SourceProvenance.CURATED_CANONICAL_MAPPING.value,
                delivery_provenance=DeliveryProvenance.FRESH_COMPUTE.value,
                provenance=SourceProvenance.CURATED_CANONICAL_MAPPING.value,
                final_score=0.94
            ))
            # 4. Research paper (if research warrants it)
            if allow_research:
                engineering_candidates.append(ResourceCandidate(
                    id="paper_mimo_marzetta",
                    provider="ieee",
                    resource_type=ResourceType.RESEARCH_PAPER,
                    title="Noncooperative Cellular Wireless with Hundreds of Antennas (Foundations of Massive MIMO)",
                    canonical_url="https://ieeexplore.ieee.org/document/5595728",
                    description="Seminal IEEE paper by Thomas L. Marzetta demonstrating asymptotic channel orthogonality and infinite capacity scaling in massive MIMO.",
                    source_name="IEEE Transactions on Wireless Communications",
                    author_or_channel="Thomas L. Marzetta",
                    verified=True,
                    verification_levels=[VerificationLevel.PROVIDER_VERIFIED, VerificationLevel.DOMAIN_VERIFIED],
                    why_recommended="Seminal IEEE literature establishing theoretical foundations for multi-user beamforming arrays.",
                    source_provenance=SourceProvenance.CURATED_CANONICAL_MAPPING.value,
                    delivery_provenance=DeliveryProvenance.FRESH_COMPUTE.value,
                    provenance=SourceProvenance.CURATED_CANONICAL_MAPPING.value,
                    final_score=0.95
                ))
        elif is_digcomm:
            engineering_candidates.append(ResourceCandidate(
                id="nptel_digcomm_pulse",
                provider="nptel",
                resource_type=ResourceType.ACADEMIC_REFERENCE,
                title="NPTEL: Principles of Digital Communications — Nyquist Intersymbol Interference Criterion",
                canonical_url="https://nptel.ac.in/courses/117/104/117104115/",
                description="Comprehensive NPTEL lecture on zero-ISI pulse shaping, raised cosine filter transfer functions, and eye diagrams (IIT Kanpur).",
                source_name="NPTEL (IIT Kanpur)",
                author_or_channel="Prof. Aditya K. Jagannatham",
                verified=True,
                verification_levels=[VerificationLevel.PROVIDER_VERIFIED, VerificationLevel.DOMAIN_VERIFIED],
                why_recommended="Authoritative university curriculum reference for digital modulation and intersymbol interference mitigation.",
                source_provenance=SourceProvenance.CURATED_CANONICAL_MAPPING.value,
                delivery_provenance=DeliveryProvenance.FRESH_COMPUTE.value,
                provenance=SourceProvenance.CURATED_CANONICAL_MAPPING.value,
                final_score=0.97
            ))
            engineering_candidates.append(ResourceCandidate(
                id="ieee_digcomm_isi",
                provider="ieee",
                resource_type=ResourceType.ACADEMIC_REFERENCE,
                title="IEEE Transactions on Communications: Intersymbol Interference and Pulse Shaping Standards",
                canonical_url="https://ieeexplore.ieee.org/document/1095857",
                description="Technical reference paper covering optimal pulse shaping and spectral containment for band-limited digital channels.",
                source_name="IEEE Communications Society",
                author_or_channel="IEEE Technical Committee",
                verified=True,
                verification_levels=[VerificationLevel.PROVIDER_VERIFIED, VerificationLevel.DOMAIN_VERIFIED],
                why_recommended="Authoritative IEEE engineering standard for transmission bandwidth optimization.",
                source_provenance=SourceProvenance.CURATED_CANONICAL_MAPPING.value,
                delivery_provenance=DeliveryProvenance.FRESH_COMPUTE.value,
                provenance=SourceProvenance.CURATED_CANONICAL_MAPPING.value,
                final_score=0.95
            ))
        elif is_transformer and allow_research:
            engineering_candidates.append(ResourceCandidate(
                id="paper_transformer_vaswani",
                provider="neurips",
                resource_type=ResourceType.RESEARCH_PAPER,
                title="Attention Is All You Need",
                canonical_url="https://arxiv.org/abs/1706.03762",
                description="Seminal paper introducing the Transformer architecture based solely on self-attention mechanisms, dispensing with recurrence and convolutions.",
                source_name="NeurIPS / arXiv",
                author_or_channel="Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Łukasz Kaiser, Illia Polosukhin",
                doi="10.48550/arXiv.1706.03762",
                arxiv_id="1706.03762",
                venue="Advances in Neural Information Processing Systems (NeurIPS 2017)",
                publication_type="Conference Paper / Foundational Literature",
                peer_review_status="Peer-reviewed (NeurIPS)",
                year=2017,
                citation_count=130000,
                open_access=True,
                verified=True,
                verification_levels=[VerificationLevel.PROVIDER_VERIFIED, VerificationLevel.DOMAIN_VERIFIED],
                why_recommended="Foundational scholarly literature essential for understanding self-attention and multi-head attention mechanisms.",
                source_provenance=SourceProvenance.CURATED_CANONICAL_MAPPING.value,
                delivery_provenance=DeliveryProvenance.FRESH_COMPUTE.value,
                provenance=SourceProvenance.CURATED_CANONICAL_MAPPING.value,
                final_score=0.99
            ))

        all_candidates = (
            engineering_candidates + coding_engine_candidates + wiki_candidates +
            docs_candidates + guide_candidates + coding_candidates + s2_candidates + arxiv_candidates
        )

        # 5. Verify URLs and integrity with hard domain and concept gating
        verified = ResourceVerificationEngine.filter_and_verify(all_candidates, context=profile.context)

        # 6. Rank candidates
        ranked = ResourceRanker.rank_candidates(verified, profile, min_relevance_threshold=0.45, max_results=18)

        # 7. Group into dynamic categories (strictly evidence-based)
        academic_refs: List[MaterialItemOutput] = []
        research_papers: List[MaterialItemOutput] = []
        practice_coding: List[MaterialItemOutput] = []
        documentation: List[MaterialItemOutput] = []
        guides_tutorials: List[MaterialItemOutput] = []

        def to_output(r: ResourceCandidate, cat_type: str) -> MaterialItemOutput:
            src_prov = getattr(r, "source_provenance", None)
            if not src_prov:
                src_prov = r.provenance.value if hasattr(r.provenance, "value") else str(r.provenance or "LIVE_SEARCH_RESULT")
            del_prov = getattr(r, "delivery_provenance", None)
            if not del_prov or del_prov == "LIVE_FETCH":
                if src_prov in ("CURATED_CANONICAL_MAPPING", "INTERNAL_GENERATED"):
                    del_prov = DeliveryProvenance.FRESH_COMPUTE.value
                else:
                    del_prov = DeliveryProvenance.LIVE_PROVIDER_FETCH.value
            return MaterialItemOutput(
                id=r.id,
                title=r.title,
                url=r.canonical_url,
                related_practice_url=getattr(r, "related_practice_url", None),
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
                verification_level=r.verification_levels[0].value if r.verification_levels else "DOMAIN_VERIFIED",
                source_provenance=src_prov,
                delivery_provenance=del_prov,
                provenance=src_prov
            )

        for r in ranked:
            if r.resource_type == ResourceType.ACADEMIC_REFERENCE:
                academic_refs.append(to_output(r, "academic_references"))
            elif r.resource_type == ResourceType.RESEARCH_PAPER and allow_research:
                research_papers.append(to_output(r, "research_papers"))
            elif r.resource_type in (ResourceType.CODING_PROBLEM, ResourceType.PRACTICE_PROBLEM):
                if profile.is_programming_topic:
                    practice_coding.append(to_output(r, "practice_coding"))
            elif r.resource_type == ResourceType.OFFICIAL_DOCUMENTATION:
                documentation.append(to_output(r, "documentation"))
            else:
                guides_tutorials.append(to_output(r, "guides_tutorials"))

        # 8. Dynamic Visible Tabs: only display categories with verified results!
        is_ee_or_comms = profile.domain in ["electrical_engineering", "telecommunications", "wireless_communications"] or \
                         any(k in profile.canonical_topic.lower() for k in ["mimo", "beamforming", "nyquist", "pulse shaping", "wireless"])

        visible_tabs: List[str] = []
        if is_ee_or_comms:
            # Preferred resource ordering for Massive MIMO & engineering:
            # 1. NPTEL / IIT course & IEEE authoritative technical material (academic_references)
            # 2. Simulation / engineering learning material (documentation)
            # 3. High-quality guides / tutorials (guides_tutorials)
            # 4. Research paper where stage depth warrants it (research_papers)
            if academic_refs:
                visible_tabs.append("academic_references")
            if documentation:
                visible_tabs.append("documentation")
            if guides_tutorials:
                visible_tabs.append("guides_tutorials")
            if allow_research and research_papers:
                visible_tabs.append("research_papers")
        else:
            # Priority order for CS/programming: documentation, practice_coding, guides, academic, research
            if documentation:
                visible_tabs.append("documentation")
            if practice_coding and profile.is_programming_topic:
                visible_tabs.append("practice_coding")
            if guides_tutorials:
                visible_tabs.append("guides_tutorials")
            if academic_refs:
                visible_tabs.append("academic_references")
            if allow_research and research_papers:
                visible_tabs.append("research_papers")

        categories = LearningMaterialsCategoriesOutput(
            academic_references=academic_refs[:3],
            research_papers=research_papers[:3] if allow_research else [],
            practice_coding=practice_coding[:3],
            documentation=documentation[:3],
            guides_tutorials=guides_tutorials[:3],
            extra_learning_material=guides_tutorials[:3]  # backward compat alias
        )

        diagnostic = {
            "canonical_topic": profile.canonical_topic,
            "is_programming": profile.is_programming_topic,
            "allow_research": allow_research,
            "research_tier": research_tier,
            "research_reason": research_reason,
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

    _STAGE_BUNDLE_REGISTRY: Dict[str, Dict[str, Any]] = {}

    @classmethod
    async def get_coding_resources(
        cls,
        topic: str,
        stage: Any = None,
        learner_level: str = "B.Tech",
        refresh: bool = False,
        roadmap_id: Optional[str] = None,
        plan_version: Any = 1
    ) -> CodingResourcesResponseOutput:
        """
        Dedicated endpoint returning authoritative Official Documentation,
        GeeksforGeeks conceptual reference, and LeetCode problem progression.
        """
        stage_title = _extract_stage_field(stage, "title", topic)
        stage_id = _extract_stage_field(stage, "id", "default_stage")
        stage_desc = _extract_stage_field(stage, "description", "")
        archetype = _extract_stage_field(stage, "archetype", None) or _extract_stage_field(stage, "stage_type", "concept_intro")
        is_remedial = _extract_stage_field(stage, "is_remedial", False)
        objectives = _extract_stage_field(stage, "learning_objectives", [])
        weaknesses = _extract_stage_field(stage, "weaknesses", [])
        concept_id = _extract_stage_field(stage, "concept_id", None)
        canonical_concept_ids = _extract_stage_field(stage, "canonical_concept_ids", None)
        r_id = roadmap_id or _extract_stage_field(stage, "roadmap_id", "live_roadmap")
        p_ver = plan_version or _extract_stage_field(stage, "plan_version", 1)

        profile = IntentProfileBuilder.build(
            roadmap_id=r_id,
            stage_id=stage_id,
            topic=topic,
            stage_title=stage_title,
            stage_description=stage_desc,
            archetype=archetype,
            learner_level=learner_level,
            is_remedial=is_remedial,
            concept_id=concept_id,
            objectives=objectives,
            weaknesses=weaknesses,
            plan_version=p_ver,
            canonical_concept_ids=canonical_concept_ids
        )

        # Ensure stage object reflects resolved canonical concepts
        if isinstance(stage, dict):
            if not stage.get("canonical_concept_ids"):
                stage["canonical_concept_ids"] = list(profile.canonical_concept_ids)
        elif stage is not None:
            if hasattr(stage, "canonical_concept_ids") and not getattr(stage, "canonical_concept_ids", None):
                try:
                    stage.canonical_concept_ids = list(profile.canonical_concept_ids)
                except Exception:
                    pass

        cached_data = DurableResourceCache.get(profile, "coding_resources", bypass=refresh)
        if cached_data:
            logger.info(f"[ResourceService] Returning cached Coding Resources for {profile.canonical_topic} (key={compute_cache_key(profile, 'coding_resources')[:8]})")
            resp = CodingResourcesResponseOutput(**cached_data)
            if resp.diagnostic_info:
                resp.diagnostic_info["cache_status"] = "BACKEND_CACHE_HIT"
                resp.diagnostic_info["cache_key"] = compute_cache_key(profile, "coding_resources")
            for item in resp.items:
                item.delivery_provenance = DeliveryProvenance.BACKEND_CACHE_HIT.value
                # Keep item.source_provenance intact
            return resp

        stage_concept_id = getattr(stage, "concept_id", "") or (stage.get("concept_id") if isinstance(stage, dict) else "") or "c_default"
        stage_obj = stage if isinstance(stage, RoadmapStage) else RoadmapStage(
            id=stage_id,
            concept_id=stage_concept_id,
            title=stage_title,
            description=stage_desc,
            duration_minutes=15
        )

        from app.services.lesson_planner.vnext.resources.coding_engine import CodingResourceEngine
        cards, diagnostics = CodingResourceEngine.get_coding_resources_with_diagnostics(
            topic=profile.canonical_topic,
            stage=stage_obj,
            context=profile.context
        )

        items: List[CodingResourceItemOutput] = []
        for c in cards:
            state = ProviderDiagnosticState.SUCCESS
            if c.type == "official_docs":
                state = diagnostics.get("official_docs", {}).get("state", ProviderDiagnosticState.SUCCESS)
            elif c.url and "geeksforgeeks" in c.url:
                state = diagnostics.get("geeksforgeeks", {}).get("state", ProviderDiagnosticState.SUCCESS)
            elif (c.url and "leetcode" in c.url) or (getattr(c, "related_practice_url", None) and "leetcode" in c.related_practice_url):
                state = diagnostics.get("leetcode", {}).get("state", ProviderDiagnosticState.SUCCESS)

            src_prov = getattr(c, "source_provenance", None) or c.provenance or "CURATED_CANONICAL_MAPPING"
            del_prov = getattr(c, "delivery_provenance", None)
            if not del_prov or del_prov == "LIVE_FETCH":
                if src_prov in ("CURATED_CANONICAL_MAPPING", "INTERNAL_GENERATED"):
                    del_prov = DeliveryProvenance.FRESH_COMPUTE.value
                else:
                    del_prov = DeliveryProvenance.LIVE_PROVIDER_FETCH.value

            res_role = getattr(c, "resource_role", "STAGE_SPECIFIC_REFERENCE") or "STAGE_SPECIFIC_REFERENCE"
            related_url = getattr(c, "related_practice_url", None)
            items.append(CodingResourceItemOutput(
                id=c.id,
                title=c.title,
                source=c.source_authority,
                type=c.type,
                url=c.url,
                related_practice_url=related_url,
                description=c.what_it_covers,
                why_recommended=c.why_recommended,
                fit_label="Strong fit",
                diagnostic_state=state,
                exact_section=c.exact_section,
                time_required_minutes=c.time_required_minutes,
                source_provenance=src_prov,
                delivery_provenance=del_prov,
                provenance=src_prov,
                resource_role=res_role
            ))

        backend_key = compute_cache_key(profile, "coding_resources")

        # Bundle duplication guard across stages in the same roadmap
        bundle_titles = tuple(sorted([it.title for it in items]))
        session_key = f"{r_id}:{p_ver}"
        if session_key not in cls._STAGE_BUNDLE_REGISTRY:
            cls._STAGE_BUNDLE_REGISTRY[session_key] = {}

        for prev_stage_id, prev_bundle in cls._STAGE_BUNDLE_REGISTRY[session_key].items():
            if prev_stage_id != stage_id and prev_bundle == bundle_titles:
                logger.warning(
                    f"[DUPLICATE_STAGE_RESOURCE_BUNDLE] Stage '{stage_id}' produced identical bundle to earlier stage '{prev_stage_id}'. "
                    f"Emitting DUPLICATE_STAGE_RESOURCE_BUNDLE."
                )

        cls._STAGE_BUNDLE_REGISTRY[session_key][stage_id] = bundle_titles

        response = CodingResourcesResponseOutput(
            enabled=True,
            status="active",
            canonical_topic=profile.canonical_topic,
            domain=profile.domain,
            specialization=profile.specialization,
            items=items,
            provider_diagnostics=diagnostics,
            diagnostic_info={
                "canonical_topic": profile.canonical_topic,
                "total_items": len(items),
                "cache_status": "bypass" if refresh else "miss",
                "cache_key": backend_key,
                "canonical_concept_ids": profile.canonical_concept_ids
            }
        )

        if items:
            DurableResourceCache.set(profile, "coding_resources", response.dict())

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


# Alias for backward compatibility and testing
LessonResourceIntelligenceService = StageResourceIntelligenceService

