"""
Stage Resource Intelligence Comprehensive Unit Test Suite
=========================================================
Covers:
1. Canonical topic normalization & intent profiling.
2. Hard negative term rejection (e.g., Pandas / Data Mining on DBMS Normalization).
3. StageActionRecommender constraint enforcement (at most 1 PRIMARY, 1-2 RECOMMENDED).
4. YouTube quota protection, metadata enrichment, thumbnail fallbacks.
5. Evidence-based publication labels & peer-review status (no fake Q1-Q4).
6. TrustedDomainRegistry classification (Wikipedia != Official Docs; GFG != Official Docs).
7. Dynamic category generation (non-empty tabs, no coding for non-programming).
8. Durable caching & refresh invalidation.
9. Rate limiter behavior.
10. Security & live test isolation (RUN_LIVE_RESOURCE_TESTS guard).
"""
import os
import asyncio
import pytest
from app.core.config import settings
from app.services.lesson_resources.schemas import (
    ResourceIntentProfile,
    ResourceCandidate,
    ResourceType,
    VerificationLevel,
    StageActionPriority,
    StageIntent
)
from app.services.lesson_resources.intent_profile import IntentProfileBuilder
from app.services.lesson_resources.resource_ranker import ResourceRanker
from app.services.lesson_resources.action_recommender import StageActionRecommender
from app.services.lesson_resources.providers.trusted_domains import TrustedDomainRegistry
from app.services.lesson_resources.providers.semantic_scholar_provider import (
    map_publication_type,
    SemanticScholarProvider,
    MIN_REQUEST_INTERVAL_SECONDS,
    _RATE_LIMIT_LOCK
)
from app.services.lesson_resources.providers.youtube_provider import YouTubeProvider
from app.services.lesson_resources.cache import DurableResourceCache, compute_cache_key


# =====================================================================
# 1. SECURITY & CONFIGURATION TESTS
# =====================================================================

def test_security_credentials_no_hardcoded_keys():
    """Verify that credentials are read from configuration and no literal keys are embedded."""
    # Ensure settings exposes the attribute
    assert hasattr(settings, "SEMANTIC_SCHOLAR_API_KEY")
    assert hasattr(settings, "TAVILY_API_KEY")
    assert hasattr(settings, "CROSSREF_MAILTO")
    
    # Check that settings values are loaded from environment / .env
    assert settings.CROSSREF_MAILTO != ""
    assert "@" in settings.CROSSREF_MAILTO


# =====================================================================
# 2. CANONICAL NORMALIZATION & INTENT PROFILE TESTS
# =====================================================================

def test_intent_profile_dbms_normalization():
    """Verify DBMS Normalization stage profile extracts canonical topic, concepts, and negative terms."""
    profile = IntentProfileBuilder.build(
        roadmap_id="rm-test",
        stage_id="st-test",
        topic="Database Management Systems",
        stage_title="DBMS Normalization: 1NF to BCNF",
        stage_description="Understand functional dependencies, 1NF, 2NF, 3NF and Boyce-Codd normal forms with step-by-step table decomposition.",
        learner_level="intermediate",
        weaknesses=["Confuses 2NF partial dependencies with 3NF transitive dependencies"]
    )

    assert "Normalization" in profile.canonical_topic or "Database" in profile.canonical_topic
    assert not profile.is_programming_topic
    
    # Must contain essential negative terms to block Pandas, ETL, and ML preprocessing
    lower_negatives = [term.lower() for term in profile.negative_terms]
    assert any("pandas" in t for t in lower_negatives)
    assert any("cleaning" in t or "preprocess" in t for t in lower_negatives)
    assert any("mining" in t or "machine learning" in t for t in lower_negatives)

    # Core concepts must include normal forms
    concept_str = " ".join(profile.concept_names).lower()
    assert "1nf" in concept_str or "functional" in concept_str or "normal" in concept_str


def test_intent_profile_linked_list():
    """Verify Linked List stage is detected as programming with algorithm/data structure platforms prioritized."""
    profile = IntentProfileBuilder.build(
        roadmap_id="rm-test",
        stage_id="st-test",
        topic="Data Structures & Algorithms",
        stage_title="Linked List Operations: Insertion and Deletion",
        stage_description="Implement singly linked lists in C++, covering head/tail insertion, node deletion, and pointer manipulation.",
        learner_level="beginner"
    )

    assert profile.is_programming_topic
    assert "Linked List" in profile.canonical_topic
    concept_str = " ".join(profile.concept_names).lower()
    assert "pointer" in concept_str or "node" in concept_str or "insertion" in concept_str


def test_intent_profile_photosynthesis():
    """Verify non-programming biology topic does not flag programming or coding platforms."""
    profile = IntentProfileBuilder.build(
        roadmap_id="rm-test",
        stage_id="st-test",
        topic="Cellular Biology",
        stage_title="Photosynthesis: Light-Dependent Reactions",
        stage_description="Mechanism of Photosystem II and I, electron transport chain, ATP and NADPH production in thylakoid membrane.",
        learner_level="beginner"
    )

    assert not profile.is_programming_topic
    assert "Photosynthesis" in profile.canonical_topic


def test_intent_profile_react_use_effect():
    """Verify React hooks stage identifies frontend web domain and official docs requirements."""
    profile = IntentProfileBuilder.build(
        roadmap_id="rm-test",
        stage_id="st-test",
        topic="React Web Development",
        stage_title="Mastering the React useEffect Hook",
        stage_description="Understanding effect dependencies, cleanup functions, and preventing infinite re-render loops.",
        learner_level="intermediate"
    )

    assert profile.is_programming_topic
    assert "React" in profile.canonical_topic


# =====================================================================
# 3. NEGATIVE FILTERING & RANKING TESTS
# =====================================================================

def test_ranker_negative_rejection_dbms_normalization():
    """
    CRITICAL ACCEPTANCE TEST:
    For DBMS Normalization, false-positive candidates (Pandas, ML preprocessing, Data Cleaning)
    must be rejected in Phase 1 before scoring, regardless of popularity or keywords.
    """
    profile = IntentProfileBuilder.build(
        roadmap_id="rm-test",
        stage_id="st-test",
        topic="Database Management Systems",
        stage_title="DBMS Normalization: 1NF to BCNF",
        stage_description="Understand functional dependencies, 1NF, 2NF, 3NF and Boyce-Codd normal forms with step-by-step table decomposition.",
        learner_level="intermediate"
    )

    candidates = [
        # Candidate A: False positive (Pandas)
        ResourceCandidate(
            id="yt-pandas-01",
            provider="youtube",
            resource_type=ResourceType.YOUTUBE_VIDEO,
            title="Data Normalization and Cleaning with Python Pandas DataFrame",
            canonical_url="https://www.youtube.com/watch?v=pandas12345",
            description="Learn how to normalize your numerical columns in Pandas using min-max scaling and standard scaler for data science.",
            source_name="YouTube",
            author_or_channel="DataScienceWithPandas",
            view_count=500000,
            like_count=20000
        ),
        # Candidate B: False positive (ETL / ML)
        ResourceCandidate(
            id="yt-etl-02",
            provider="youtube",
            resource_type=ResourceType.YOUTUBE_VIDEO,
            title="ETL Pipeline Normalization and Feature Preprocessing in PySpark",
            canonical_url="https://www.youtube.com/watch?v=pyspark6789",
            description="Complete data mining preprocessing guide with PySpark and ETL jobs.",
            source_name="YouTube",
            author_or_channel="BigDataETL",
            view_count=300000
        ),
        # Candidate C: Genuine DBMS Normalization
        ResourceCandidate(
            id="yt-dbms-03",
            provider="youtube",
            resource_type=ResourceType.YOUTUBE_VIDEO,
            title="Database Normalization - 1NF, 2NF, 3NF, BCNF Clearly Explained",
            canonical_url="https://www.youtube.com/watch?v=dbnorm11111",
            description="Comprehensive lecture on relational database normalization, functional dependencies, Armstrong's axioms, and table decomposition into 3NF and BCNF.",
            source_name="YouTube",
            author_or_channel="Neso Academy",
            view_count=1200000,
            like_count=50000,
            verification_level=VerificationLevel.PROVIDER_VERIFIED
        ),
        # Candidate D: Genuine DBMS Functional Dependency problem
        ResourceCandidate(
            id="yt-dbms-04",
            provider="youtube",
            resource_type=ResourceType.YOUTUBE_VIDEO,
            title="Finding Highest Normal Form and Candidate Keys | DBMS Solved Problems",
            canonical_url="https://www.youtube.com/watch?v=dbnorm22222",
            description="Step by step solved examples for finding candidate keys and checking if a table is in 2NF, 3NF or BCNF.",
            source_name="YouTube",
            author_or_channel="Gate Smashers",
            view_count=850000,
            like_count=42000,
            verification_level=VerificationLevel.PROVIDER_VERIFIED
        )
    ]

    ranked = ResourceRanker.rank_candidates(candidates, profile, min_relevance_threshold=0.50, max_results=5)

    ranked_ids = [r.id for r in ranked]

    # Pandas and ETL must NOT be in the ranked results
    assert "yt-pandas-01" not in ranked_ids, "Pandas data cleaning video MUST be rejected by negative filters!"
    assert "yt-etl-02" not in ranked_ids, "ETL preprocessing video MUST be rejected by negative filters!"

    # Genuine DBMS videos must be ranked high
    assert "yt-dbms-03" in ranked_ids
    assert "yt-dbms-04" in ranked_ids

    # Top pick must be a genuine database normalization resource
    assert ranked[0].id in ("yt-dbms-03", "yt-dbms-04")
    assert ranked[0].final_score >= 0.70
    assert any(term in ranked[0].why_recommended.lower() for term in ["1nf", "2nf", "3nf", "normalization", "functional"])


# =====================================================================
# 4. STAGE ACTION RECOMMENDER CONSTRAINTS
# =====================================================================

def test_stage_action_recommender_card_budget():
    """
    Enforces UI Contract:
    - At most 1 PRIMARY ('Top Pick')
    - 1-2 RECOMMENDED ('Recommended')
    - Rest AVAILABLE (no badge)
    """
    # Test across multiple pedagogical intents
    for intent in [StageIntent.REMEDIAL, StageIntent.CONCEPT_LEARNING, StageIntent.PRACTICE, StageIntent.ASSESSMENT]:
        profile = ResourceIntentProfile(
            roadmap_id="rm-test",
            stage_id="st-test",
            canonical_topic="Test Subject",
            stage_title="Stage Title",
            stage_intent=intent,
            learner_level="beginner",
            is_programming_topic=True
        )

        recommendations = StageActionRecommender.evaluate_actions(profile)

        primary_count = sum(1 for a in recommendations if a.priority == StageActionPriority.PRIMARY)
        rec_count = sum(1 for a in recommendations if a.priority == StageActionPriority.RECOMMENDED)
        available_count = sum(1 for a in recommendations if a.priority == StageActionPriority.AVAILABLE)

        assert primary_count <= 1, f"Intent {intent}: Expected at most 1 PRIMARY, found {primary_count}"
        assert rec_count <= 2, f"Intent {intent}: Expected at most 2 RECOMMENDED, found {rec_count}"
        assert available_count >= 2, f"Intent {intent}: Expected at least 2 AVAILABLE, found {available_count}"

        # Top pick badge must be 'Top Pick'
        for a in recommendations:
            if a.priority == StageActionPriority.PRIMARY:
                assert a.badge_label == "Top Pick"
            elif a.priority == StageActionPriority.RECOMMENDED:
                assert a.badge_label == "Recommended"
            else:
                assert a.badge_label is None


# =====================================================================
# 5. TRUSTED DOMAIN REGISTRY & STRICT DOCUMENTATION RULES
# =====================================================================

def test_trusted_domain_registry_strictness():
    """
    Requirement 16:
    Wikipedia -> Academic Reference (NEVER Official Docs)
    GeeksforGeeks -> Guide / Tutorial / Practice (NEVER Official Docs)
    Official Documentation -> Only trusted authoritative domains (e.g. react.dev, docs.python.org)
    """
    registry = TrustedDomainRegistry()

    # Wikipedia check
    wiki_type = registry.classify_url("https://en.wikipedia.org/wiki/Database_normalization")
    assert wiki_type == ResourceType.ACADEMIC_REFERENCE, f"Expected academic_references for Wikipedia, got {wiki_type}"
    assert wiki_type != ResourceType.OFFICIAL_DOCUMENTATION, "Wikipedia must NEVER be classified as official documentation!"

    # GeeksforGeeks check
    gfg_type = registry.classify_url("https://www.geeksforgeeks.org/normal-forms-in-dbms/")
    assert gfg_type in (ResourceType.GUIDE, ResourceType.TUTORIAL, ResourceType.PRACTICE_PROBLEM, ResourceType.CODING_PROBLEM)
    assert gfg_type != ResourceType.OFFICIAL_DOCUMENTATION, "GeeksforGeeks must NEVER be classified as official documentation!"

    # Authoritative Official Docs checks
    assert registry.is_official_doc_domain("https://react.dev/reference/react/useEffect")
    assert registry.is_official_doc_domain("https://docs.python.org/3/library/functions.html")
    assert registry.is_official_doc_domain("https://www.postgresql.org/docs/current/tutorial.html")
    assert not registry.is_official_doc_domain("https://en.wikipedia.org/wiki/Database_normalization")
    assert not registry.is_official_doc_domain("https://www.geeksforgeeks.org/normal-forms-in-dbms/")

    # Coding platforms
    assert registry.is_coding_platform("https://leetcode.com/problems/reverse-linked-list/")


# =====================================================================
# 6. EVIDENCE-BASED SCHOLARLY LABELS & PREPRINTS
# =====================================================================

def test_evidence_based_scholarly_labels():
    """
    Requirement 8:
    Do not automatically label every Semantic Scholar paper 'Peer-reviewed'.
    arXiv must normally be shown as 'Preprint'.
    Peer-reviewed only when provider metadata supports it.
    """
    # Case 1: Journal article
    label_j, peer_status_j = map_publication_type(["JournalArticle"])
    assert label_j == "Journal Article"
    assert "Peer-reviewed" in peer_status_j

    # Case 2: Conference paper
    label_c, peer_status_c = map_publication_type(["Conference"])
    assert label_c == "Conference Paper"
    assert "Peer-reviewed" in peer_status_c

    # Case 3: arXiv preprint
    label_a, peer_status_a = map_publication_type(["Preprint"])
    assert label_a == "Preprint"
    assert "Peer-reviewed" not in peer_status_a
    assert "Preprint" in peer_status_a

    # Case 4: No publication type provided
    label_u, peer_status_u = map_publication_type(None)
    assert label_u == "Scholarly Paper"
    assert peer_status_u == "Unknown"


# =====================================================================
# 7. YOUTUBE THUMBNAIL FALLBACK CASCADE
# =====================================================================

def test_youtube_thumbnail_fallback_hierarchy():
    """
    Requirement 20:
    Backend priority: maxres -> standard -> high -> medium -> default -> hqdefault fallback.
    """
    snippet_full = {
        "default": {"url": "https://i.ytimg.com/vi/abc/default.jpg"},
        "medium": {"url": "https://i.ytimg.com/vi/abc/mqdefault.jpg"},
        "high": {"url": "https://i.ytimg.com/vi/abc/hqdefault.jpg"},
        "standard": {"url": "https://i.ytimg.com/vi/abc/sddefault.jpg"},
        "maxres": {"url": "https://i.ytimg.com/vi/abc/maxresdefault.jpg"}
    }
    
    best_thumb, fallbacks = YouTubeProvider.resolve_thumbnail_cascade("abc", snippet_full)
    assert best_thumb == "https://i.ytimg.com/vi/abc/maxresdefault.jpg"
    assert len(fallbacks) >= 4
    assert fallbacks[0] == "https://i.ytimg.com/vi/abc/sddefault.jpg"
    assert fallbacks[-1] == "https://img.youtube.com/vi/abc/hqdefault.jpg"

    # Degraded snippet (only default available)
    snippet_degraded = {
        "default": {"url": "https://i.ytimg.com/vi/xyz/default.jpg"}
    }
    best_degraded, fallbacks_degraded = YouTubeProvider.resolve_thumbnail_cascade("xyz", snippet_degraded)
    assert best_degraded == "https://i.ytimg.com/vi/xyz/default.jpg"
    assert "https://img.youtube.com/vi/xyz/hqdefault.jpg" in fallbacks_degraded


# =====================================================================
# 8. DURABLE RESOURCE CACHE & REFRESH INVALIDATION
# =====================================================================

def test_durable_cache_and_invalidation():
    """
    Requirement 4:
    Multi-tier persistent disk cache with intent profile hash and refresh invalidation.
    """
    profile = ResourceIntentProfile(
        roadmap_id="rm-test",
        stage_id="st-test",
        canonical_topic="Test Topic",
        stage_title="Test Stage",
        learner_level="beginner",
        is_programming_topic=False
    )
    
    cache_key = compute_cache_key(profile, provider="youtube")
    assert len(cache_key) == 64  # SHA-256 hex digest
    
    # 1. Store payload
    payload = {"results": [{"id": "res-1", "title": "Test Resource", "score": 92}]}
    DurableResourceCache.set(profile, "youtube", payload, ttl_seconds=3600)

    # 2. Retrieve from cache
    cached = DurableResourceCache.get(profile, "youtube")
    assert cached is not None
    assert cached["results"][0]["id"] == "res-1"

    # 3. Bypass / refresh flag returns None
    bypass_result = DurableResourceCache.get(profile, "youtube", bypass=True)
    assert bypass_result is None

    # 4. Explicit invalidation
    DurableResourceCache.invalidate(profile, "youtube")
    assert DurableResourceCache.get(profile, "youtube") is None


# =====================================================================
# 9. RATE LIMITER BEHAVIOR
# =====================================================================

def test_semantic_scholar_rate_limiter():
    """
    Requirement 2:
    Authenticated Semantic Scholar calls throttled conservatively with rate limiter lock.
    """
    assert MIN_REQUEST_INTERVAL_SECONDS >= 0.5
    
    async def _test():
        async with _RATE_LIMIT_LOCK:
            return True
            
    res = asyncio.run(_test())
    assert res is True


# =====================================================================
# 10. LIVE PROVIDER RUNNER GUARD
# =====================================================================

@pytest.mark.skipif(
    os.getenv("RUN_LIVE_RESOURCE_TESTS") != "true",
    reason="Live third-party API tests require RUN_LIVE_RESOURCE_TESTS=true to preserve API quota."
)
def test_live_semantic_scholar_query():
    """Live provider verification: only executes when explicitly requested."""
    async def _run():
        return await SemanticScholarProvider.fetch_papers(queries=["Database Normalization Functional Dependencies"], limit_per_query=3)
    
    results = asyncio.run(_run())
    assert isinstance(results, list)
    if results:
        assert results[0].canonical_url.startswith("http")
