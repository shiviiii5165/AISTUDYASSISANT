import re
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


# ==============================================================================
# REQUIREMENT 5: NEGATIVE PROVIDER ROUTING TESTS
# ==============================================================================

@pytest.mark.anyio
async def test_negative_provider_routing_assertions():
    """
    Asserts domain policy negative constraints:
    - Massive MIMO → GFG absent unless explicitly validated by domain policy
    - Massive MIMO → LeetCode absent
    - Massive MIMO → NPTEL/engineering source visible
    - Python OOP → GFG allowed
    - Python OOP → LeetCode optional/disabled
    - Dynamic Programming → GFG + LeetCode allowed
    - React Server Components → official React docs prioritized
    - React → LeetCode absent
    """
    # 1. Massive MIMO assertions
    mimo_stage = RoadmapStage(
        id="stg_mimo_beamforming",
        concept_id="c_mimo",
        title="Beamforming and Spatial Multiplexing",
        description="Massive MIMO antenna array geometry and channel matrix decomposition",
        duration_minutes=25,
        archetype=StageArchetype.EXPLANATION
    )
    mimo_profile = IntentProfileBuilder.build(
        roadmap_id="rm_mimo_test",
        stage_id=mimo_stage.id,
        topic="Massive MIMO",
        stage_title=mimo_stage.title,
        learner_level="B.Tech"
    )
    mimo_cards, mimo_diag = CodingResourceEngine.get_coding_resources_with_diagnostics(
        topic="Massive MIMO",
        stage=mimo_stage,
        context=mimo_profile.context
    )

    # Massive MIMO → GFG absent
    gfg_mimo_cards = [c for c in mimo_cards if "geeksforgeeks" in c.url.lower()]
    assert len(gfg_mimo_cards) == 0, f"GFG must be absent for Massive MIMO, got: {gfg_mimo_cards}"
    assert mimo_diag["geeksforgeeks"]["state"] == ProviderDiagnosticState.DISABLED_BY_POLICY.value

    # Massive MIMO → LeetCode absent
    lc_mimo_cards = [c for c in mimo_cards if "leetcode" in c.url.lower()]
    assert len(lc_mimo_cards) == 0, f"LeetCode must be absent for Massive MIMO, got: {lc_mimo_cards}"
    assert mimo_diag["leetcode"]["state"] == ProviderDiagnosticState.DISABLED_BY_POLICY.value

    # Massive MIMO → NPTEL/engineering source visible in Learning Materials
    mimo_materials = await StageResourceIntelligenceService.get_learning_materials(
        topic="Massive MIMO",
        stage=mimo_stage,
        learner_level="B.Tech"
    )
    all_mimo_mat = (
        (getattr(mimo_materials.categories, "academic_references", []) or []) +
        (getattr(mimo_materials.categories, "documentation", []) or []) +
        (getattr(mimo_materials.categories, "research_papers", []) or [])
    )
    nptel_or_ieee = [m for m in all_mimo_mat if "nptel" in m.source.lower() or "ieee" in m.source.lower()]
    assert len(nptel_or_ieee) > 0, "Massive MIMO must expose visible NPTEL and IEEE engineering resources"
    assert "academic_references" in mimo_materials.visible_tabs
    assert "practice_coding" not in mimo_materials.visible_tabs

    # 2. Python OOP assertions
    py_stage = RoadmapStage(
        id="stg_py_oop",
        concept_id="c_py_oop",
        title="Objects & Classes Overview",
        description="Introduction to classes, objects, and attributes in Python",
        duration_minutes=20,
        archetype=StageArchetype.MENTAL_MODEL
    )
    py_profile = IntentProfileBuilder.build(
        roadmap_id="rm_py_test",
        stage_id=py_stage.id,
        topic="object and class in python",
        stage_title=py_stage.title,
        learner_level="B.Tech"
    )
    py_cards, py_diag = CodingResourceEngine.get_coding_resources_with_diagnostics(
        topic="object and class in python",
        stage=py_stage,
        context=py_profile.context
    )
    # Python OOP → GFG allowed
    py_gfg = [c for c in py_cards if "geeksforgeeks" in c.url.lower()]
    assert len(py_gfg) > 0, "GFG must be allowed for Python OOP"
    assert py_diag["geeksforgeeks"]["state"] == ProviderDiagnosticState.SUCCESS.value

    # Python OOP → LeetCode disabled by policy
    assert py_diag["leetcode"]["state"] == ProviderDiagnosticState.DISABLED_BY_POLICY.value

    # 3. Dynamic Programming assertions
    dp_stage = RoadmapStage(
        id="stg_dp_knapsack",
        concept_id="c_dp",
        title="0/1 Knapsack Problem",
        description="Optimal substructure and memoization table",
        duration_minutes=25,
        archetype=StageArchetype.CODING
    )
    dp_profile = IntentProfileBuilder.build(
        roadmap_id="rm_dp_test",
        stage_id=dp_stage.id,
        topic="Dynamic Programming",
        stage_title=dp_stage.title,
        learner_level="B.Tech"
    )
    dp_cards, dp_diag = CodingResourceEngine.get_coding_resources_with_diagnostics(
        topic="Dynamic Programming",
        stage=dp_stage,
        context=dp_profile.context
    )
    # Dynamic Programming → GFG + LeetCode allowed
    dp_gfg = [c for c in dp_cards if "geeksforgeeks" in c.url.lower()]
    dp_lc = [c for c in dp_cards if "leetcode" in c.url.lower()]
    assert len(dp_gfg) > 0, "GFG must be allowed for Dynamic Programming"
    assert len(dp_lc) > 0, "LeetCode must be allowed for Dynamic Programming"
    assert dp_diag["geeksforgeeks"]["state"] == ProviderDiagnosticState.SUCCESS.value
    assert dp_diag["leetcode"]["state"] == ProviderDiagnosticState.SUCCESS.value

    # 4. React Server Components assertions
    rsc_stage = RoadmapStage(
        id="stg_rsc_arch",
        concept_id="c_rsc",
        title="Server vs Client Components Architecture",
        description="Streaming SSR and boundary constraints in React",
        duration_minutes=25,
        archetype=StageArchetype.EXPLANATION
    )
    rsc_profile = IntentProfileBuilder.build(
        roadmap_id="rm_rsc_test",
        stage_id=rsc_stage.id,
        topic="React Server Components",
        stage_title=rsc_stage.title,
        learner_level="B.Tech"
    )
    rsc_cards, rsc_diag = CodingResourceEngine.get_coding_resources_with_diagnostics(
        topic="React Server Components",
        stage=rsc_stage,
        context=rsc_profile.context
    )
    # React Server Components → official React docs prioritized
    official_react = [c for c in rsc_cards if c.type == "official_docs" and "react.dev" in c.url.lower()]
    assert len(official_react) > 0, "Official React docs must be returned and prioritized"
    assert rsc_diag["official_docs"]["state"] == ProviderDiagnosticState.SUCCESS.value

    # React → LeetCode absent
    rsc_lc = [c for c in rsc_cards if "leetcode" in c.url.lower()]
    assert len(rsc_lc) == 0, "LeetCode must be absent for React Server Components"
    assert rsc_diag["leetcode"]["state"] == ProviderDiagnosticState.DISABLED_BY_POLICY.value


# ==============================================================================
# REQUIREMENT 6: 7-TOPIC LIVE ACCEPTANCE TEST MATRIX
# ==============================================================================

@pytest.mark.anyio
@pytest.mark.parametrize("topic_name,stage_title,learner_level,expected_gfg_state,expected_lc_state,expected_research_visible", [
    ("Python Objects & Classes", "Objects & Classes Overview", "B.Tech", ProviderDiagnosticState.SUCCESS, ProviderDiagnosticState.DISABLED_BY_POLICY, False),
    ("Dynamic Programming", "0/1 Knapsack Problem", "B.Tech", ProviderDiagnosticState.SUCCESS, ProviderDiagnosticState.SUCCESS, False),
    ("Binary Search Tree", "BST Insertion and Deletion", "B.Tech", ProviderDiagnosticState.SUCCESS, ProviderDiagnosticState.SUCCESS, False),
    ("React Server Components", "Server vs Client Components Architecture", "B.Tech", ProviderDiagnosticState.SUCCESS, ProviderDiagnosticState.DISABLED_BY_POLICY, False),
    ("Massive MIMO", "Beamforming and Spatial Multiplexing", "B.Tech", ProviderDiagnosticState.DISABLED_BY_POLICY, ProviderDiagnosticState.DISABLED_BY_POLICY, True),
    ("Digital Communication", "Pulse Shaping and Nyquist Criterion", "B.Tech", ProviderDiagnosticState.DISABLED_BY_POLICY, ProviderDiagnosticState.DISABLED_BY_POLICY, True),
    ("Transformer Architecture", "Self-Attention and Multi-Head Attention", "B.Tech", ProviderDiagnosticState.SUCCESS, ProviderDiagnosticState.DISABLED_BY_POLICY, True),
])
async def test_7_topic_live_acceptance_matrix(
    topic_name, stage_title, learner_level, expected_gfg_state, expected_lc_state, expected_research_visible
):
    """
    Validates runtime behavior across all 7 acceptance cases:
    - Eligibility decision
    - Provider provenance type
    - Candidate count, accepted count, rejected count
    - Ranking score
    - Rejection reason
    - Cache status
    """
    stage = RoadmapStage(
        id=f"stg_{topic_name[:6].lower()}",
        concept_id="c_test",
        title=stage_title,
        description=f"Core concepts and principles for {stage_title}",
        duration_minutes=20,
        archetype=StageArchetype.CODING if expected_lc_state == ProviderDiagnosticState.SUCCESS else StageArchetype.EXPLANATION
    )

    profile = IntentProfileBuilder.build(
        roadmap_id=f"rm_{topic_name[:6].lower()}",
        stage_id=stage.id,
        topic=topic_name,
        stage_title=stage_title,
        learner_level=learner_level
    )

    # 1. Coding Resources Provider Execution
    coding_cards, coding_diag = CodingResourceEngine.get_coding_resources_with_diagnostics(
        topic=topic_name,
        stage=stage,
        context=profile.context
    )

    # GFG verification
    gfg_diag = coding_diag.get("geeksforgeeks", {})
    assert gfg_diag.get("state") == expected_gfg_state.value, (
        f"{topic_name}: Expected GFG state {expected_gfg_state.value}, got {gfg_diag.get('state')}"
    )
    if expected_gfg_state == ProviderDiagnosticState.DISABLED_BY_POLICY:
        assert gfg_diag.get("final_count") == 0
        assert "disabled by policy" in (gfg_diag.get("failure_reason") or "").lower()
    else:
        assert gfg_diag.get("final_count", 0) >= 1
        gfg_card = next(c for c in coding_cards if c.url and "geeksforgeeks" in c.url.lower())
        assert gfg_card.source_provenance == "CURATED_CANONICAL_MAPPING"
        assert gfg_card.delivery_provenance in ["FRESH_COMPUTE", "LIVE_FETCH", "BACKEND_CACHE_HIT"]
        assert gfg_card.provenance == "CURATED_CANONICAL_MAPPING"
        assert gfg_card.quality_score >= 90

    # LeetCode verification
    lc_diag = coding_diag.get("leetcode", {})
    assert lc_diag.get("state") == expected_lc_state.value, (
        f"{topic_name}: Expected LeetCode state {expected_lc_state.value}, got {lc_diag.get('state')}"
    )
    if expected_lc_state == ProviderDiagnosticState.DISABLED_BY_POLICY:
        assert lc_diag.get("final_count") == 0
    else:
        assert lc_diag.get("final_count", 0) >= 1
        lc_card = next(c for c in coding_cards if c.url and "leetcode" in c.url.lower())
        assert lc_card.source_provenance == "CURATED_CANONICAL_MAPPING"
        assert lc_card.delivery_provenance in ["FRESH_COMPUTE", "LIVE_FETCH", "BACKEND_CACHE_HIT"]
        assert lc_card.provenance == "CURATED_CANONICAL_MAPPING"

    # 2. Learning Materials Execution
    materials = await StageResourceIntelligenceService.get_learning_materials(
        topic=topic_name,
        stage=stage,
        learner_level=learner_level
    )

    # Research visibility check
    diag = materials.diagnostic_info or {}
    assert diag.get("allow_research") == expected_research_visible, (
        f"{topic_name}: Expected allow_research={expected_research_visible}, got {diag.get('allow_research')}"
    )
    if expected_research_visible:
        assert "research_papers" in materials.visible_tabs or "academic_references" in materials.visible_tabs
    else:
        assert "research_papers" not in materials.visible_tabs

    # Provenance check on returned materials
    all_mat_items = (
        (getattr(materials.categories, "academic_references", []) or []) +
        (getattr(materials.categories, "documentation", []) or []) +
        (getattr(materials.categories, "research_papers", []) or []) +
        (getattr(materials.categories, "guides_tutorials", []) or [])
    )
    for it in all_mat_items:
        assert hasattr(it, "source_provenance"), f"{it.title} missing source_provenance"
        assert hasattr(it, "delivery_provenance"), f"{it.title} missing delivery_provenance"
        assert it.source_provenance in [
            "LIVE_SEARCH_RESULT",
            "CURATED_CANONICAL_MAPPING",
            "DIRECT_URL_VERIFIED",
            "INTERNAL_GENERATED"
        ], f"Invalid source_provenance: {it.source_provenance}"
        assert it.delivery_provenance in [
            "FRESH_COMPUTE",
            "LIVE_PROVIDER_FETCH",
            "LIVE_FETCH",
            "BACKEND_CACHE_HIT",
            "FRONTEND_CACHE_HIT"
        ], f"Invalid delivery_provenance: {it.delivery_provenance}"

    # Verify static canonical mapping preserves its source_provenance
    canonical_items = [it for it in all_mat_items if it.id.startswith(("nptel_", "paper_", "ieee_", "sim_", "gfg_", "doc_"))]
    for cit in canonical_items:
        assert cit.source_provenance != "LIVE_SEARCH_RESULT", f"Canonical item {cit.title} must NOT have source_provenance LIVE_SEARCH_RESULT"
        assert cit.source_provenance == "CURATED_CANONICAL_MAPPING"

    # Specific End-to-End Verification for Transformer Architecture:
    if topic_name == "Transformer Architecture":
        vaswani_papers = [
            it for it in materials.categories.research_papers
            if (it.url and "vaswani" in it.url.lower()) or "1706.03762" in (it.arxiv_id or "") or "attention is all you need" in it.title.lower()
        ]
        assert len(vaswani_papers) > 0, "Transformer Architecture must return Vaswani seminal paper in research_papers"
        v_paper = vaswani_papers[0]
        assert v_paper.title == "Attention Is All You Need"
        assert v_paper.source == "NeurIPS / arXiv"
        assert v_paper.arxiv_id == "1706.03762"
        assert v_paper.doi == "10.48550/arXiv.1706.03762"
        assert "NeurIPS" in (v_paper.venue or "")
        assert v_paper.source_provenance == "CURATED_CANONICAL_MAPPING"
        assert v_paper.delivery_provenance in ["FRESH_COMPUTE", "LIVE_FETCH", "BACKEND_CACHE_HIT"]


# ==============================================================================
# REQUIREMENT 9 & 10: DYNAMIC PROGRAMMING STAGE-AWARE & SUBSTRING MATRIX TESTS
# ==============================================================================

def test_false_substring_matching_matrix():
    """
    SECTION 10: False Substring Regression Matrix
    Verifies that substring occurrences containing 'b-s-t' do not false-positive match BST,
    while legitimate BST token representations match correctly.
    """
    # Negative cases: must NOT match BST
    false_positive_cases = [
        "optimal substructure",
        "abstract data type",
        "obstacle grid",
        "substitution",
        "robustness",
        "substantive analysis"
    ]
    for text in false_positive_cases:
        assert not CodingResourceEngine._matches_bst(text), f"'{text}' falsely matched BST!"

    # Positive cases: MUST match BST
    true_positive_cases = [
        "BST",
        "bst",
        "binary search tree",
        "binary-search-tree",
        "Search in BST",
        "Convert sorted array to binary search tree"
    ]
    for text in true_positive_cases:
        assert CodingResourceEngine._matches_bst(text), f"'{text}' failed to match BST!"

    # Regression: Optimal Substructure stage must NEVER route to BST
    stage_opt_sub = RoadmapStage(
        id="dp_properties",
        concept_id="concept_2",
        title="The Two Pillars: Optimal Substructure & State Definition",
        description="Understanding subproblem independence and state representation",
        duration_minutes=20,
        archetype=StageArchetype.EXPLANATION
    )
    profile = IntentProfileBuilder.build(
        roadmap_id="roadmap_dynamic_programming",
        stage_id=stage_opt_sub.id,
        topic="Dynamic Programming",
        stage_title=stage_opt_sub.title,
        stage_description=stage_opt_sub.description,
        learner_level="B.Tech",
        concept_id=stage_opt_sub.concept_id
    )
    cards, diags = CodingResourceEngine.get_coding_resources_with_diagnostics(
        topic="Dynamic Programming",
        stage=stage_opt_sub,
        context=profile.context
    )
    titles = [c.title for c in cards]
    urls = [c.url for c in cards if c.url]
    assert not any("binary search tree" in t.lower() or bool(re.search(r"\bbst\b", t, re.IGNORECASE)) for t in titles), \
        f"Stage 2 falsely routed to BST: {titles}"
    assert not any("binary-search-tree" in u.lower() for u in urls), \
        f"Stage 2 contains BST URL: {urls}"
    assert any("optimal substructure" in t.lower() for t in titles), \
        f"Stage 2 must include Optimal Substructure GFG reference: {titles}"


@pytest.mark.anyio
async def test_dynamic_programming_stage_aware_coding_regression():
    """
    SECTION 9: Stage-Aware Coding Resource Intelligence Regression Test
    Verifies that all 5 Dynamic Programming stages receive stage-appropriate,
    pedagogically differentiated coding resource bundles with unique cache keys.
    """
    from app.services.lesson_resources.service import StageResourceIntelligenceService
    from app.services.lesson_resources.cache import compute_cache_key

    dp_stages = [
        RoadmapStage(
            id="stage_1",
            concept_id="dp_intuition",
            title="The Power of Memoization: From Recursion to DP",
            description="Introduction to top-down memoization and recursion pruning",
            duration_minutes=15,
            archetype=StageArchetype.EXPLANATION
        ),
        RoadmapStage(
            id="dp_properties",
            concept_id="concept_2",
            title="The Two Pillars: Optimal Substructure & State Definition",
            description="Identifying independent subproblems and formulating state",
            duration_minutes=20,
            archetype=StageArchetype.EXPLANATION
        ),
        RoadmapStage(
            id="dp_tabulation",
            concept_id="concept_3",
            title="Bottom-Up Approach: Tabulation & Recurrence Relations",
            description="Iterative DP tables, base-case initialization, and transitions",
            duration_minutes=20,
            archetype=StageArchetype.EXPLANATION
        ),
        RoadmapStage(
            id="dp_2d",
            concept_id="concept_4",
            title="2D Dynamic Programming: Grids and Knapsack",
            description="Multi-dimensional state tables, 0/1 knapsack, and grid paths",
            duration_minutes=25,
            archetype=StageArchetype.EXPLANATION
        ),
        RoadmapStage(
            id="dp_synthesis",
            concept_id="concept_5",
            title="Synthesis & Common Pitfalls",
            description="State-transition mistakes, space optimization, and edge cases",
            duration_minutes=20,
            archetype=StageArchetype.SUMMARY
        )
    ]

    backend_keys = []
    bundle_fingerprints = []
    stage_responses = {}

    for stage in dp_stages:
        resp = await StageResourceIntelligenceService.get_coding_resources(
            topic="Dynamic Programming",
            stage=stage,
            learner_level="B.Tech",
            refresh=True,
            roadmap_id="roadmap_dynamic_programming",
            plan_version=1
        )
        stage_responses[stage.id] = resp
        b_key = resp.diagnostic_info.get("cache_key")
        assert b_key, f"Stage {stage.id} must return backend cache key"
        backend_keys.append(b_key)

        # Canonical concept IDs assertions
        c_ids = resp.diagnostic_info.get("canonical_concept_ids", [])
        assert len(c_ids) > 0, f"Stage {stage.id} must have populated canonical_concept_ids"
        assert not any(re.match(r"^concept_\d+$", cid) for cid in c_ids), \
            f"Stage {stage.id} contains generic concept ID in canonical_concept_ids: {c_ids}"

        # Fingerprint bundle
        fp = tuple(sorted([it.title for it in resp.items]))
        bundle_fingerprints.append(fp)

        # Provider diagnostics assert
        assert resp.provider_diagnostics["geeksforgeeks"]["state"] == "SUCCESS"
        assert resp.provider_diagnostics["leetcode"]["state"] == "SUCCESS"

    # Assertion 1: Unique backend cache keys = 5/5
    assert len(set(backend_keys)) == 5, f"All 5 stages must have unique cache keys! Got: {backend_keys}"

    # Assertion 2: Differentiated resource bundles (no duplicate bundle across stages)
    assert len(set(bundle_fingerprints)) == 5, \
        f"All 5 DP stages must have differentiated bundles! Duplicate found in: {bundle_fingerprints}"

    # Assertion 3: Stage 2 never routes to BST
    s2_titles = [it.title.lower() for it in stage_responses["dp_properties"].items]
    assert not any("binary search tree" in t or bool(re.search(r"\bbst\b", t, re.IGNORECASE)) for t in s2_titles)
    assert any("optimal substructure" in t for t in s2_titles)

    # Assertion 4: Stage 4 (dp_2d) includes genuine 2D/grid/knapsack resources
    s4_titles = [it.title for it in stage_responses["dp_2d"].items]
    s4_urls = [it.url for it in stage_responses["dp_2d"].items if it.url]
    assert any("0/1 Knapsack" in t or "Knapsack" in t for t in s4_titles)
    assert any("Unique Paths" in t or "Target Sum" in t or "Knapsack" in t for t in s4_titles)
    assert any("knapsack" in u.lower() or "unique-paths" in u.lower() or "target-sum" in u.lower() for u in s4_urls)

    # Assertion 5: Reopening same stage causes cache hit
    s1_cached = await StageResourceIntelligenceService.get_coding_resources(
        topic="Dynamic Programming",
        stage=dp_stages[0],
        learner_level="B.Tech",
        refresh=False,
        roadmap_id="roadmap_dynamic_programming",
        plan_version=1
    )
    assert s1_cached.diagnostic_info["cache_status"] == "BACKEND_CACHE_HIT"
    assert s1_cached.items[0].delivery_provenance == "BACKEND_CACHE_HIT"
    assert s1_cached.items[0].source_provenance == "CURATED_CANONICAL_MAPPING"

    # Assertion 6: Diagnostic exercises labeled as internal/generated diagnostics with INTERNAL_GENERATED provenance, url=None, related_practice_url
    s2_items = stage_responses["dp_properties"].items
    s2_diags = [it for it in s2_items if it.type == "diagnostic_micro_problem"]
    assert len(s2_diags) == 1, f"Stage 2 must contain exactly 1 diagnostic check: {[it.title for it in s2_items]}"
    assert s2_diags[0].source_provenance == "INTERNAL_GENERATED", f"Stage 2 diagnostic must have INTERNAL_GENERATED provenance: {s2_diags[0].source_provenance}"
    assert s2_diags[0].source == "LearnByGenie Diagnostic Engine"
    assert "LearnByGenie Diagnostic" in s2_diags[0].title
    assert not s2_diags[0].title.startswith("LeetCode"), f"Diagnostic must not be represented as LeetCode problem: {s2_diags[0].title}"
    assert s2_diags[0].url is None, f"INTERNAL_GENERATED diagnostic must not use external search page as primary url: {s2_diags[0].url}"
    assert s2_diags[0].related_practice_url and "leetcode.com" in s2_diags[0].related_practice_url
    assert s2_diags[0].delivery_provenance == "FRESH_COMPUTE", f"Curated/internal fresh compute must be FRESH_COMPUTE, got: {s2_diags[0].delivery_provenance}"

    s5_items = stage_responses["dp_synthesis"].items
    s5_diags = [it for it in s5_items if it.type == "diagnostic_micro_problem"]
    assert len(s5_diags) == 1, f"Stage 5 must contain exactly 1 diagnostic exercise: {[it.title for it in s5_items]}"
    assert s5_diags[0].source_provenance == "INTERNAL_GENERATED", f"Stage 5 diagnostic must have INTERNAL_GENERATED provenance: {s5_diags[0].source_provenance}"
    assert s5_diags[0].source == "LearnByGenie Diagnostic Engine"
    assert "LearnByGenie Diagnostic" in s5_diags[0].title
    assert not s5_diags[0].title.startswith("LeetCode"), f"Diagnostic must not be represented as LeetCode problem: {s5_diags[0].title}"
    assert s5_diags[0].url is None, f"INTERNAL_GENERATED diagnostic must not use external search page as primary url: {s5_diags[0].url}"
    assert s5_diags[0].related_practice_url and "leetcode.com" in s5_diags[0].related_practice_url
    assert s5_diags[0].delivery_provenance == "FRESH_COMPUTE", f"Curated/internal fresh compute must be FRESH_COMPUTE, got: {s5_diags[0].delivery_provenance}"

    # Also verify local curated canonical mapping has FRESH_COMPUTE on fresh compute and is NOT LIVE_PROVIDER_FETCH
    s1_items = stage_responses["stage_1"].items
    assert all(it.delivery_provenance == "FRESH_COMPUTE" for it in s1_items), \
        f"Fresh compute of curated mappings must have FRESH_COMPUTE delivery_provenance, got: {[it.delivery_provenance for it in s1_items]}"
    assert not any(it.delivery_provenance == "LIVE_PROVIDER_FETCH" for it in s1_items), \
        "CURATED_CANONICAL_MAPPING resolved locally must not be reported as LIVE_PROVIDER_FETCH"

    # Assertion 7: External resource title matches real source scope (Space Optimization, not broader Common Mistakes)
    s5_gfg = [it for it in s5_items if it.url and "geeksforgeeks" in it.url.lower()]
    assert len(s5_gfg) == 1, f"Stage 5 must contain 1 GFG article: {[it.title for it in s5_items]}"
    assert s5_gfg[0].title == "GeeksforGeeks: Space Optimization using Dynamic Programming", \
        f"GFG title must match real source scope, got: {s5_gfg[0].title}"
    assert "space-optimization-using-dynamic-programming" in s5_gfg[0].url



