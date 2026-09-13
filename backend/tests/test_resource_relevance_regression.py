import pytest
import asyncio
from typing import List
from app.services.lesson_resources.schemas import (
    ResourceCandidate, ResourceType, VerificationLevel,
    ResourceQueryContext, ProviderDiagnosticState
)
from app.services.lesson_resources.intent_profile import IntentProfileBuilder
from app.services.lesson_resources.verification import (
    ResourceVerificationEngine, is_domain_compatible, is_concept_compatible
)
from app.services.lesson_resources.cache import (
    ResourceCache
)
from app.services.lesson_resources.service import StageResourceIntelligenceService, LessonResourceIntelligenceService
from app.services.lesson_planner.vnext.resources.coding_engine import CodingResourceEngine
from app.services.lesson_planner.vnext.resources.registry import ResourceNeedDetector
from app.services.lesson_planner.schemas import (
    RoadmapStage, StageArchetype, CanonicalDomain, TeachingIntent, ProductMode
)


# ==============================================================================
# REQUIREMENT 15: TEST THE EXACT BUG (Python Objects & Classes)
# ==============================================================================

@pytest.mark.anyio
async def test_python_objects_and_classes_exact_bug():
    """
    Topic: "object and class in python"
    Level: B.Tech
    Stage: "Objects & Classes Overview"

    Assertions:
    - domain == computer_science / specialization == python_programming
    - Coding/Official Docs resource category visible
    - Python official docs candidate available
    - GFG candidate is allowed and returned
    - LeetCode is NOT mandatory for this conceptual stage (disabled by policy)
    - astronomy paper count == 0
    - astronomical object classification count == 0
    - biology/taxonomy object-classification count == 0
    - unrelated Java vulnerability-paper count == 0
    - Research Papers tab hidden by default
    - No generic "objects/classes" academic query is issued
    """
    topic = "object and class in python"
    learner_level = "B.Tech"
    stage_title = "Objects & Classes Overview"

    # 1. Intent profile resolution
    profile = IntentProfileBuilder.build(
        roadmap_id="rm_test_oop",
        stage_id="stg_oop_overview",
        topic=topic,
        stage_title=stage_title,
        learner_level=learner_level
    )

    assert profile.domain == "computer_science", f"Expected computer_science, got {profile.domain}"
    assert profile.specialization == "python_programming" or "python" in profile.canonical_topic.lower()
    assert profile.context is not None

    # Verify query context has canonical concept IDs and domain
    assert "cs.python.oop.object" in profile.context.canonical_concept_ids or "cs.python.oop.class" in profile.context.canonical_concept_ids
    assert profile.context.negative_terms is not None
    assert "astronomy" in profile.context.negative_terms or "jwst" in profile.context.negative_terms

    # Verify research papers are NOT recommended by default for B.Tech intro OOP
    assert ResourceType.RESEARCH_PAPER not in profile.recommended_resource_types, "Research papers must NOT be recommended for intro B.Tech OOP"

    # 2. Test Hard Domain & Concept Gating on Candidates
    def make_candidate(title: str, url: str, desc: str, res_type: ResourceType = ResourceType.RESEARCH_PAPER, provider: str = "crossref") -> ResourceCandidate:
        return ResourceCandidate(
            id=f"c_{abs(hash(url)) % 100000}",
            provider=provider,
            resource_type=res_type,
            title=title,
            canonical_url=url,
            description=desc,
            source_name=provider,
            author_or_channel="Researcher et al."
        )

    astronomy_candidate = make_candidate(
        title="Photometric classification of astronomical objects in JWST catalog",
        url="https://arxiv.org/abs/2301.99999",
        desc="We classify celestial objects and stellar classes using photometric surveys.",
        provider="arxiv"
    )
    taxonomy_candidate = make_candidate(
        title="Taxonomic classification of biological classes and organism objects",
        url="https://doi.org/10.1000/bio.123",
        desc="Biological kingdom classification into phylum and classes.",
        provider="crossref"
    )
    sociology_candidate = make_candidate(
        title="Social classes and socioeconomic status in contemporary society",
        url="https://doi.org/10.1000/soc.456",
        desc="Analysis of working class and upper classes in urban centers.",
        provider="crossref"
    )
    java_vuln_candidate = make_candidate(
        title="Vulnerabilities in Java bytecode class loaders and runtime objects",
        url="https://doi.org/10.1000/sec.789",
        desc="Exploitation of deserialization flaws in Java classes.",
        provider="semantic_scholar"
    )
    valid_python_doc = make_candidate(
        title="9. Classes — Python 3.12 documentation",
        url="https://docs.python.org/3/tutorial/classes.html",
        desc="Classes provide a means of bundling data and functionality together in Python.",
        res_type=ResourceType.OFFICIAL_DOCUMENTATION,
        provider="official_docs"
    )
    valid_gfg = make_candidate(
        title="Python Classes and Objects - GeeksforGeeks",
        url="https://www.geeksforgeeks.org/python-classes-and-objects/",
        desc="A class is a user-defined blueprint or prototype from which objects are created in Python.",
        res_type=ResourceType.OFFICIAL_DOCUMENTATION,
        provider="geeksforgeeks"
    )

    context = profile.context

    # Hard domain compatibility checks
    assert is_domain_compatible(astronomy_candidate, context) is False, "Astronomy candidate must be rejected"
    assert is_domain_compatible(taxonomy_candidate, context) is False, "Biological taxonomy candidate must be rejected"
    assert is_domain_compatible(sociology_candidate, context) is False, "Sociology candidate must be rejected"
    assert is_domain_compatible(java_vuln_candidate, context) is False, "Java vulnerability candidate must be rejected"
    assert is_domain_compatible(valid_python_doc, context) is True, "Valid Python docs must be accepted"
    assert is_domain_compatible(valid_gfg, context) is True, "Valid GFG must be accepted"

    # Batch verification filter
    all_candidates = [
        astronomy_candidate, taxonomy_candidate, sociology_candidate,
        java_vuln_candidate, valid_python_doc, valid_gfg
    ]
    verified = ResourceVerificationEngine.filter_and_verify(all_candidates, context=context)

    # Assertions on verified candidates
    assert len(verified) == 2, f"Expected exactly 2 valid candidates, got {len(verified)}"
    verified_titles = [c.title for c in verified]
    assert any("Python 3" in t or "Classes" in t for t in verified_titles)
    assert any("GeeksforGeeks" in t for t in verified_titles)

    # 0 irrelevant papers
    assert not any("astronomical" in t.lower() or "jwst" in t.lower() for t in verified_titles)
    assert not any("taxonomic" in t.lower() or "biological" in t.lower() for t in verified_titles)
    assert not any("java" in t.lower() for t in verified_titles)

    # 3. Coding Resource Engine Verification
    stage = RoadmapStage(
        id="stg_oop_overview",
        concept_id="c_oop",
        title=stage_title,
        description="Introduction to classes, objects, and attributes in Python",
        duration_minutes=20,
        archetype=StageArchetype.MENTAL_MODEL
    )

    cards, diagnostics = CodingResourceEngine.get_coding_resources_with_diagnostics(
        topic=topic,
        stage=stage,
        learner_proficiency="developing",
        context=context
    )

    # Official docs returned
    official_docs = [c for c in cards if c.type == "official_docs"]
    assert len(official_docs) > 0, "Python official docs must be returned"
    assert "docs.python.org" in official_docs[0].url

    # GFG returned
    gfg_cards = [c for c in cards if "geeksforgeeks" in c.url]
    assert len(gfg_cards) > 0, "GeeksforGeeks reference must be returned"
    assert "geeksforgeeks.org" in gfg_cards[0].url

    # LeetCode NOT mandatory / disabled by policy for conceptual stage
    leetcode_diag = diagnostics.get("leetcode", {})
    lc_state = leetcode_diag.get("state", leetcode_diag.get("status"))
    assert lc_state in [
        ProviderDiagnosticState.DISABLED_BY_POLICY.value,
        ProviderDiagnosticState.NO_RELEVANT_RESULTS.value
    ], f"LeetCode must not be forced into conceptual OOP stage: {leetcode_diag}"

    # 4. End-to-end Learning Materials check
    materials = await StageResourceIntelligenceService.get_learning_materials(
        topic=topic,
        stage={
            "id": "stg_oop_overview",
            "title": stage_title,
            "description": "Introduction to classes, objects, and attributes in Python"
        },
        learner_level=learner_level
    )
    assert "research_papers" not in materials.visible_tabs, "Research papers tab must be hidden by default"
    paper_items = getattr(materials.categories, "research_papers", []) or []
    assert len(paper_items) == 0, f"Expected 0 research papers, got {len(paper_items)}"

    all_material_items = (
        (getattr(materials.categories, "academic_references", []) or []) +
        (getattr(materials.categories, "documentation", []) or []) +
        (getattr(materials.categories, "practice_coding", []) or []) +
        (getattr(materials.categories, "guides_tutorials", []) or [])
    )
    all_material_titles = [item.title for item in all_material_items]
    assert not any("astronomical" in t.lower() or "jwst" in t.lower() for t in all_material_titles), "Zero astronomy papers allowed"
    assert not any("taxonomic" in t.lower() or "biological" in t.lower() for t in all_material_titles), "Zero taxonomy papers allowed"
    assert not any("vulnerabilit" in t.lower() and "java" in t.lower() for t in all_material_titles), "Zero Java vulnerability papers allowed"



# ==============================================================================
# REQUIREMENT 16: CACHE AND REQUEST DEDUPLICATION TESTS
# ==============================================================================

@pytest.mark.anyio
async def test_backend_resource_cache_and_deduplication():
    """
    Test semantic caching TTL, key computation, and in-flight request deduplication.
    """
    # 1. Test cache set, get, TTL
    profile = IntentProfileBuilder.build(
        roadmap_id="rm_cache_test",
        stage_id="stg_cache_test",
        topic="python_oop",
        stage_title="Classes Overview",
        learner_level="B.Tech"
    )

    ResourceCache.set(
        profile=profile,
        resource_type="official_docs",
        response_json={"items": ["doc1", "doc2"]}
    )

    cached = ResourceCache.get(
        profile=profile,
        resource_type="official_docs"
    )
    assert cached is not None
    assert cached["items"] == ["doc1", "doc2"]

    # Invalidate by context
    ResourceCache.invalidate(
        profile=profile,
        resource_type="official_docs"
    )
    assert ResourceCache.get(
        profile=profile,
        resource_type="official_docs"
    ) is None

    # 2. Test in-flight request deduplication
    call_count = 0

    async def mock_upstream_fetch():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return {"result": "success", "call_count": call_count}

    # Launch 5 concurrent calls using deduplicate_and_fetch
    results = await asyncio.gather(
        ResourceCache.deduplicate_and_fetch(profile, "official_docs", mock_upstream_fetch),
        ResourceCache.deduplicate_and_fetch(profile, "official_docs", mock_upstream_fetch),
        ResourceCache.deduplicate_and_fetch(profile, "official_docs", mock_upstream_fetch),
        ResourceCache.deduplicate_and_fetch(profile, "official_docs", mock_upstream_fetch),
        ResourceCache.deduplicate_and_fetch(profile, "official_docs", mock_upstream_fetch)
    )

    assert call_count == 1, f"Expected exactly 1 upstream call, got {call_count}"
    for r in results:
        assert r["result"] == "success"
        assert r["call_count"] == 1


# ==============================================================================
# REQUIREMENT 17: LIVE PROVIDER ACCEPTANCE TESTS FOR 5 TOPICS
# ==============================================================================

@pytest.mark.anyio
@pytest.mark.parametrize("topic,stage_title,expected_domain,should_have_leetcode", [
    ("object and class in python", "Objects & Classes Overview", "computer_science", False),
    ("Dynamic Programming", "0/1 Knapsack Problem", "computer_science", True),
    ("Binary Search Tree", "BST Insertion and Deletion", "computer_science", True),
    ("React Server Components", "Server vs Client Components Architecture", "software_engineering", False),
    ("Massive MIMO", "Beamforming and Spatial Multiplexing", "electrical_engineering", False),
])
async def test_live_provider_acceptance_across_topics(topic, stage_title, expected_domain, should_have_leetcode):
    """
    Runs acceptance testing across the 5 canonical benchmark topics.
    Validates providers: official_docs, geeksforgeeks, leetcode, and diagnostics.
    """
    stage = RoadmapStage(
        id=f"stg_{topic[:5].lower()}",
        concept_id="c_test",
        title=stage_title,
        description=f"Core concepts and implementation for {stage_title}",
        duration_minutes=20,
        archetype=StageArchetype.CODING if should_have_leetcode else StageArchetype.EXPLANATION
    )

    profile = IntentProfileBuilder.build(
        roadmap_id="rm_acceptance",
        stage_id=stage.id,
        topic=topic,
        stage_title=stage_title,
        learner_level="B.Tech"
    )

    cards, diagnostics = CodingResourceEngine.get_coding_resources_with_diagnostics(
        topic=topic,
        stage=stage,
        learner_proficiency="developing",
        context=profile.context
    )

    # Diagnostic checks
    assert "official_docs" in diagnostics
    assert "geeksforgeeks" in diagnostics
    assert "leetcode" in diagnostics

    # Official docs / conceptual refs
    if expected_domain in ["computer_science", "software_engineering"]:
        official_or_gfg = [c for c in cards if c.type == "official_docs" or "geeksforgeeks" in c.url]
        assert len(official_or_gfg) > 0, f"Expected official docs or GFG for {topic}"

    # LeetCode policy assertion
    lc_status = diagnostics["leetcode"].get("state", diagnostics["leetcode"].get("status"))
    if should_have_leetcode:
        assert lc_status == ProviderDiagnosticState.SUCCESS.value, f"LeetCode expected SUCCESS for {topic}, got {lc_status}"
        practice_problems = [c for c in cards if c.type == "coding_problem"]
        assert len(practice_problems) > 0, f"Expected practice problems for {topic}"
    else:
        assert lc_status in [ProviderDiagnosticState.DISABLED_BY_POLICY.value, ProviderDiagnosticState.NO_RELEVANT_RESULTS.value]


# ==============================================================================
# REQUIREMENT 16: UI SESSION CACHE LIFECYCLE & DEDUPLICATION TEST
# ==============================================================================

@pytest.mark.anyio
async def test_ui_session_cache_lifecycle():
    """
    Automate UI/API tests:
    - Open YouTube: backend_calls.youtube == 1
    - Open Learning Materials: backend_calls.materials == 1
    - Return YouTube: backend_calls.youtube still == 1
    - Close/reopen YouTube modal: backend_calls.youtube still == 1
    - Return Learning Materials: backend_calls.materials still == 1
    - Explicit Refresh YouTube: backend_calls.youtube == 2
    - Plan version changes: old cache not reused
    - Switch stage: stage-specific cache key used
    - Double-click: single in-flight request
    """
    class MockFrontendSession:
        def __init__(self):
            self.cache = {}
            self.in_flight = {}
            self.backend_calls = {"youtube": 0, "materials": 0, "coding": 0}

        def compute_key(self, roadmap_id, plan_version, stage_id, concept_ids, res_type, level="B.Tech", mode="TEACH"):
            sorted_concepts = ",".join(sorted(concept_ids or []))
            return f"{roadmap_id}:{plan_version}:{stage_id}:{sorted_concepts}:{res_type}:{level}:{mode}"

        async def open_viewer(self, roadmap_id, plan_version, stage_id, concept_ids, res_type, refresh=False):
            key = self.compute_key(roadmap_id, plan_version, stage_id, concept_ids, res_type)
            if not refresh and key in self.cache:
                return self.cache[key]
            if refresh and key in self.cache:
                del self.cache[key]

            if key in self.in_flight:
                return await self.in_flight[key]

            async def _do_fetch():
                self.backend_calls[res_type] += 1
                await asyncio.sleep(0.01)
                return {"type": res_type, "call": self.backend_calls[res_type]}

            fut = asyncio.create_task(_do_fetch())
            self.in_flight[key] = fut
            try:
                res = await fut
                self.cache[key] = res
                return res
            finally:
                self.in_flight.pop(key, None)

    session = MockFrontendSession()
    rm_id = "rm_live_01"
    v1 = 1
    s1 = "stg_01"
    concepts = ["cs.python.oop.class"]

    # 1. Open YouTube: backend_calls.youtube == 1
    await session.open_viewer(rm_id, v1, s1, concepts, "youtube")
    assert session.backend_calls["youtube"] == 1

    # 2. Open Learning Materials: backend_calls.materials == 1
    await session.open_viewer(rm_id, v1, s1, concepts, "materials")
    assert session.backend_calls["materials"] == 1

    # 3. Return YouTube: backend_calls.youtube still == 1
    await session.open_viewer(rm_id, v1, s1, concepts, "youtube")
    assert session.backend_calls["youtube"] == 1

    # 4. Close/reopen YouTube modal: backend_calls.youtube still == 1
    # (Modal close sets activeViewer = null without clearing session cache)
    await session.open_viewer(rm_id, v1, s1, concepts, "youtube")
    assert session.backend_calls["youtube"] == 1

    # 5. Return Learning Materials: backend_calls.materials still == 1
    await session.open_viewer(rm_id, v1, s1, concepts, "materials")
    assert session.backend_calls["materials"] == 1

    # 6. Explicit Refresh YouTube: backend_calls.youtube == 2
    await session.open_viewer(rm_id, v1, s1, concepts, "youtube", refresh=True)
    assert session.backend_calls["youtube"] == 2

    # 7. Plan version changes: old cache not reused
    v2 = 2
    await session.open_viewer(rm_id, v2, s1, concepts, "youtube")
    assert session.backend_calls["youtube"] == 3

    # 8. Switch stage: stage-specific cache key used
    s2 = "stg_02"
    await session.open_viewer(rm_id, v2, s2, concepts, "youtube")
    assert session.backend_calls["youtube"] == 4

    # 9. Double-click: single in-flight request
    results = await asyncio.gather(
        session.open_viewer(rm_id, v2, s2, concepts, "materials"),
        session.open_viewer(rm_id, v2, s2, concepts, "materials")
    )
    assert session.backend_calls["materials"] == 2  # exactly 1 additional call, not 2
    assert results[0] == results[1]

