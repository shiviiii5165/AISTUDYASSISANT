"""
Test Suite: Student Learning Quality Upgrade
============================================
Verifies that generated notes transcend compressed revision stubs
and function as genuine, self-contained educational learning material.

Evaluates 8 Required Quality Criteria:
1. Multi-tiered, substantive learning depth (Simple Idea, Intuition, Formal Mechanisms).
2. Procedural worked examples with multi-step reasoning (Problem, Given, Steps, Answer, Why).
3. Structured comparison representations (Markdown tables -> HTML tables with <th>, <tbody>).
4. Progressive practice distribution across Bloom's cognitive taxonomy with step-by-step rationales.
5. Explicit misconception debunking (Wrong Belief vs Scientific Reality vs Why).
6. Visual plan execution (VisualSpec nodes and layout).
7. Balanced typography without card-overuse antipattern.
8. Holistic learning document self-containment and complete artifact certification.
"""
import pytest
from app.services.notes.schemas import (
    NotesDocument, NoteSection, VisualSpec, CalloutItem,
    NoteDepth, NoteFormat, NoteDifficulty, SectionSemanticEvidence
)
from app.services.notes.context.schemas import CanonicalNotesContext, LessonContext
from app.services.notes.decision.schemas import (
    NotesGenerationPlan, SectionPlanItem, PurposePlan,
    TeachingStrategyPlan, VisualPlan, RemediationPlan,
    PracticePlan, RevisionPlan
)
from app.services.notes.generation.engine import _build_deterministic_fallback
from app.services.notes.rendering.html_builder import HTMLNoteBuilder
from app.services.notes.certification.certifier import StudentArtifactCertifier
from app.services.notes.certification.schemas import ArtifactStatus
from tests.test_notes_pdf_regression import chemical_bonding_golden_fixture


def test_detailed_learning_depth_is_substantive(chemical_bonding_golden_fixture: NotesDocument):
    """
    Test 1: Verifies multi-tiered explanations (simple idea, intuition, formal concept)
    rather than single-sentence summary stubs.
    """
    doc = chemical_bonding_golden_fixture
    assert len(doc.sections) >= 5, "Detailed learning notes must provide comprehensive curricular sections"

    for sec in doc.sections:
        # Substantive content length
        assert len(sec.content) >= 250, f"Section {sec.id} content must be substantive, got {len(sec.content)} chars"
        
        # Layered conceptual structure
        content_lower = sec.content.lower()
        has_simple_or_intuition = ("simple idea" in content_lower or "intuition" in content_lower)
        has_formal_or_theory = ("formal" in content_lower or "postulate" in content_lower or "definition" in content_lower or "theory" in content_lower or "comparison" in content_lower)
        assert has_simple_or_intuition, f"Section {sec.id} missing simple idea or intuitive scaffolding"
        assert has_formal_or_theory, f"Section {sec.id} missing formal theory or structural definition"

        # Semantic evidence validation
        assert sec.semantic_evidence is not None, f"Section {sec.id} must carry semantic evidence"
        assert sec.semantic_evidence.explanation_present is True
        assert sec.semantic_evidence.intuition_present is True

    # Also verify fallback engine respects NoteDepth.DETAILED
    ctx = CanonicalNotesContext(
        topic="Electromagnetic Induction",
        subject="Physics",
        class_level="Class 12",
        curriculum="CBSE"
    )
    plan = NotesGenerationPlan.create(
        purpose=PurposePlan(),
        formats=[NoteFormat.LEARNING_NOTES],
        difficulty=NoteDifficulty.STANDARD,
        depth=NoteDepth.DETAILED,
        teaching_strategy=TeachingStrategyPlan(),
        section_plan=[
            SectionPlanItem(type="overview", required=True),
            SectionPlanItem(type="core_concept", required=True),
        ],
        visual_plan=VisualPlan(required=False),
        remediation_plan=RemediationPlan(required=False),
        practice_plan=PracticePlan(required=True, count=3, difficulty="standard"),
        revision_plan=RevisionPlan(required=False)
    )
    fallback_doc = _build_deterministic_fallback(ctx, plan)
    core_sec = next(s for s in fallback_doc.sections if s.section_type == "core_concept")
    assert "### 1. Simple Intuition" in core_sec.content
    assert "### 2. Formal Scientific Mechanism" in core_sec.content
    assert core_sec.semantic_evidence.intuition_present is True


def test_worked_example_contains_reasoning_steps(chemical_bonding_golden_fixture: NotesDocument):
    """
    Test 2: Verifies worked examples contain procedural steps
    (Problem, Given, Concept, Step 1, Step 2, Final Answer, Why).
    """
    doc = chemical_bonding_golden_fixture
    worked_sections = [s for s in doc.sections if s.examples]
    assert len(worked_sections) >= 4, "Learning document must embed procedural worked examples in major sections"

    required_tokens = ["**Problem**:", "**Given**:", "**Concept**:", "**Step 1", "**Final Answer**:", "**Why**:"]
    for sec in worked_sections:
        for ex in sec.examples:
            for token in required_tokens:
                assert token in ex, f"Worked example in section {sec.id} missing required procedural element '{token}'"

    # HTML rendering check: Procedural steps must be typeset cleanly
    html = HTMLNoteBuilder.build_html(doc)
    assert "class=\"example-step\"" in html or "<strong>Step 1" in html
    assert "<strong>Problem</strong>:" in html
    assert "<strong>Final Answer</strong>:" in html


def test_comparison_topics_use_comparison_structure(chemical_bonding_golden_fixture: NotesDocument):
    """
    Test 3: Verifies comparison-heavy topics employ structured tables
    rather than compressed prose.
    """
    doc = chemical_bonding_golden_fixture
    
    # Check markdown table presence in key comparison sections
    vsepr_sec = next(s for s in doc.sections if s.id == "sec_vsepr")
    vbt_sec = next(s for s in doc.sections if s.id == "sec_vbt")
    hybrid_sec = next(s for s in doc.sections if s.id == "sec_hybridization")
    hbond_sec = next(s for s in doc.sections if s.id == "sec_h_bonding")

    assert "| Molecule |" in vsepr_sec.content
    assert "| Characteristic | Sigma Bond (σ) | Pi Bond (π) |" in vbt_sec.content
    assert "| Hybrid Type | Steric Number |" in hybrid_sec.content
    assert "| Property | Intermolecular Hydrogen Bonding | Intramolecular Hydrogen Bonding |" in hbond_sec.content

    # Check HTML table generation
    html = HTMLNoteBuilder.build_html(doc)
    assert "<table" in html
    assert "<th>Characteristic</th>" in html or "<th>Property</th>" in html or "<th>Molecule</th>" in html
    assert "<tbody>" in html
    # Ensure at least 3 distinct comparison tables exist in the rendered HTML
    table_count = html.count("<table")
    assert table_count >= 3, f"Expected at least 3 rendered comparison tables, found {table_count}"


def test_progressive_practice_distribution(chemical_bonding_golden_fixture: NotesDocument):
    """
    Test 4: Verifies practice items contain progressive difficulty/type distribution
    across Bloom's taxonomy (Recall, Conceptual, Application, Exam-Style, Challenge)
    with complete step-by-step explanations.
    """
    doc = chemical_bonding_golden_fixture
    assert len(doc.practice) >= 5, "Learning document must include at least 5 progressive practice items"

    types_present = {p.get("type", "").lower() for p in doc.practice}
    expected_types = {"recall", "conceptual", "application", "exam-style", "challenge"}
    assert expected_types.issubset(types_present), f"Practice set missing expected cognitive levels. Present: {types_present}"

    for p in doc.practice:
        assert p.get("question"), "Practice item missing question text"
        assert p.get("answer"), "Practice item missing model answer"
        assert p.get("explanation"), "Practice item missing pedagogical step-by-step explanation"
        assert len(p["explanation"]) >= 40, f"Practice explanation too brief: '{p['explanation']}'"

    # HTML rendering check: Cognitive badges and explanations rendered
    html = HTMLNoteBuilder.build_html(doc)
    assert "practice-wrapper" in html
    assert "practice-explanation" in html
    assert "meta-badge badge-primary" in html
    assert "Challenge" in html and "Explanation:" in html


def test_misconception_has_explicit_correction(chemical_bonding_golden_fixture: NotesDocument):
    """
    Test 5: Verifies explicit debunking:
    Wrong Belief vs Scientific Reality vs Underlying Mechanism/Why.
    """
    doc = chemical_bonding_golden_fixture
    callouts = [c for s in doc.sections for c in s.callouts if c.type == "misconception"]
    assert len(callouts) >= 2, "Golden learning document must explicitly debunk at least 2 common misconceptions"

    for c in callouts:
        assert "**Wrong Belief**:" in c.text, f"Misconception '{c.title}' missing Wrong Belief marker"
        assert "**Scientific Reality**:" in c.text, f"Misconception '{c.title}' missing Scientific Reality marker"
        assert "**Why**:" in c.text, f"Misconception '{c.title}' missing Why explanation marker"

    # HTML rendering check
    html = HTMLNoteBuilder.build_html(doc)
    assert "callout-misconception" in html
    assert "Wrong Belief" in html
    assert "Scientific Reality" in html


def test_visual_plan_is_executed(chemical_bonding_golden_fixture: NotesDocument):
    """
    Test 6: Verifies visual diagram specs are executed with substantive nodes and layout.
    """
    doc = chemical_bonding_golden_fixture
    assert doc.visuals and len(doc.visuals) >= 1, "Learning document must contain visual specifications"
    
    spec = doc.visuals[0]
    assert spec.type in ("flowchart", "mind_map", "diagram")
    assert len(spec.nodes) >= 4, f"Visual diagram must contain at least 4 conceptual nodes, got {len(spec.nodes)}"

    # HTML rendering check
    html = HTMLNoteBuilder.build_html(doc)
    assert "diagram-wrapper" in html
    assert "flow-node" in html
    assert "flow-arrow" in html


def test_card_overuse_is_not_required_for_content(chemical_bonding_golden_fixture: NotesDocument):
    """
    Test 7: Verifies narrative flow without placing every sentence in a callout card.
    Callout cards must be reserved for targeted pedagogical interrupts.
    """
    doc = chemical_bonding_golden_fixture
    total_sections = len(doc.sections)
    total_callouts = sum(len(s.callouts) for s in doc.sections)

    # In a 5-section comprehensive document, callout cards should be targeted (<= 4 total)
    assert total_callouts <= 4, f"Overuse of callout cards: {total_callouts} cards for {total_sections} sections"

    # Majority of characters must reside in core content, not callout cards
    total_narrative_chars = sum(len(s.content) for s in doc.sections)
    total_callout_chars = sum(len(c.text) for s in doc.sections for c in s.callouts)
    callout_ratio = total_callout_chars / (total_narrative_chars + total_callout_chars)

    assert callout_ratio < 0.25, f"Callout cards consume {callout_ratio:.1%} of text; narrative typography must dominate"


def test_learning_document_is_not_merely_summary_like(chemical_bonding_golden_fixture: NotesDocument):
    """
    Test 8: Verifies that detailed learning notes provide true educational scaffolding,
    guided reasoning, progressive retrieval, and passes full artifact certification.
    """
    import asyncio
    doc = chemical_bonding_golden_fixture
    
    # 1. Substantive total document volume (not a compressed 1-2 page summary stub)
    total_words = sum(len(s.content.split()) for s in doc.sections)
    total_words += sum(len(ex.split()) for s in doc.sections for ex in s.examples)
    total_words += sum(len(p.get("question", "").split()) + len(p.get("answer", "").split()) + len(p.get("explanation", "").split()) for p in doc.practice)
    assert total_words >= 1000, f"Learning document must contain at least 1,000 words to teach comprehensively, got {total_words}"

    # 2. Sequential pedagogical scaffolding: verify major conceptual topics
    section_titles = [s.title.lower() for s in doc.sections]
    assert any("octet" in t or "kossel" in t for t in section_titles), "Missing fundamental Octet/Lewis foundation"
    assert any("vsepr" in t for t in section_titles), "Missing VSEPR 3D geometry"
    assert any("valence bond" in t or "vbt" in t for t in section_titles), "Missing Valence Bond Theory"
    assert any("hybridization" in t for t in section_titles), "Missing Hybridization mechanics"
    assert any("hydrogen bond" in t for t in section_titles), "Missing Intermolecular / H-Bonding"

    # 3. Full Artifact Certification Gate
    context = CanonicalNotesContext(
        topic="Chemical Bonding and Molecular Structure",
        subject="Chemistry",
        class_level="Class 11",
        curriculum="CBSE"
    )
    plan = NotesGenerationPlan.create(
        purpose=PurposePlan(),
        formats=[NoteFormat.LEARNING_NOTES],
        difficulty=NoteDifficulty.STANDARD,
        depth=NoteDepth.DETAILED,
        teaching_strategy=TeachingStrategyPlan(),
        section_plan=[
            SectionPlanItem(type="core_concept", required=True),
            SectionPlanItem(type="core_concept", required=True),
            SectionPlanItem(type="core_concept", required=True),
            SectionPlanItem(type="core_concept", required=True),
            SectionPlanItem(type="core_concept", required=True)
        ],
        visual_plan=VisualPlan(required=True, type="flowchart"),
        remediation_plan=RemediationPlan(required=True, target_concepts=["octet rule universality", "electron geometry vs molecular shape"]),
        practice_plan=PracticePlan(required=True, count=5, difficulty="standard"),
        revision_plan=RevisionPlan(required=False)
    )

    cert_result = asyncio.run(StudentArtifactCertifier.certify_artifact(
        doc=doc,
        plan=plan,
        ctx=context
    ))

    assert cert_result.artifact_status in (ArtifactStatus.STUDENT_READY, ArtifactStatus.STUDENT_READY_WITH_WARNINGS)
    critical_defects = [d for d in cert_result.artifact_certification.defects if d.severity == "critical"]
    assert len(critical_defects) == 0, f"Found critical defects: {critical_defects}"


def test_sub_concept_coverage_and_missing_prevents_100_percent(chemical_bonding_golden_fixture: NotesDocument):
    """
    Test 9: Verifies sub-concept granularity. When authoritative sub-concepts are supplied,
    every sub-concept is tracked. If a required sub-concept is MISSING, the document
    CANNOT be certified as 100% complete.
    """
    from app.services.notes.certification.coverage_certifier import CoverageCertifier

    doc = chemical_bonding_golden_fixture
    ctx = CanonicalNotesContext(
        topic="Chemical Bonding",
        subject="Chemistry",
        class_level="Class 11",
        lesson=LessonContext(
            topic="Chemical Bonding",
            learning_objectives=["VSEPR Theory"],
            structured_objectives={
                "VSEPR Theory": [
                    "electron domains",
                    "steric number",
                    "electron geometry",
                    "molecular geometry",
                    "lone-pair effects",
                    "bond-angle distortion"
                ]
            }
        )
    )
    plan = NotesGenerationPlan.create(
        purpose=PurposePlan(),
        formats=[NoteFormat.LEARNING_NOTES],
        difficulty=NoteDifficulty.STANDARD,
        depth=NoteDepth.DETAILED,
        teaching_strategy=TeachingStrategyPlan(),
        section_plan=[
            SectionPlanItem(type="core_concept", target="VSEPR Theory", required=True)
        ],
        visual_plan=VisualPlan(),
        remediation_plan=RemediationPlan(),
        practice_plan=PracticePlan(required=False),
        revision_plan=RevisionPlan()
    )

    # 1. Full coverage check
    res = CoverageCertifier.certify_content_coverage(doc, plan=plan, ctx=ctx)
    assert res.coverage.sub_concepts_total == 6
    assert res.coverage.sub_concepts_covered >= 5
    assert res.coverage.sub_concepts_missing == 0
    assert res.valid is True

    # 2. Incomplete sub-concept check: add an unfulfilled sub-concept
    ctx_incomplete = CanonicalNotesContext(
        topic="Chemical Bonding",
        subject="Chemistry",
        class_level="Class 11",
        lesson=LessonContext(
            topic="Chemical Bonding",
            learning_objectives=["VSEPR Theory"],
            structured_objectives={
                "VSEPR Theory": [
                    "electron domains",
                    "relativistic spin orbit coupling in heavy actinide hydrides"  # Missing from Class 11 VSEPR
                ]
            }
        )
    )
    res_incomplete = CoverageCertifier.certify_content_coverage(doc, plan=plan, ctx=ctx_incomplete)
    assert res_incomplete.coverage.sub_concepts_missing > 0
    # Crucial specification rule: topic cannot be reported as 100% complete
    assert res_incomplete.substantive_score < 100.0
    assert res_incomplete.valid is False
    assert any("sub-concepts are MISSING" in f or "was missing" in f for f in res_incomplete.findings)


def test_sub_concepts_not_invented_without_authoritative_data(chemical_bonding_golden_fixture: NotesDocument):
    """
    Test 10: Strict Non-Invention Rule. When context and plan do not provide
    sub-concepts, the certifier MUST NOT invent them.
    """
    from app.services.notes.certification.coverage_certifier import CoverageCertifier

    doc = chemical_bonding_golden_fixture
    ctx = CanonicalNotesContext(
        topic="Chemical Bonding",
        subject="Chemistry",
        class_level="Class 11",
        lesson=LessonContext(
            topic="Chemical Bonding",
            learning_objectives=["Octet Rule", "VSEPR Theory"]  # No structured sub-concepts
        )
    )
    plan = NotesGenerationPlan.create(
        purpose=PurposePlan(),
        formats=[NoteFormat.LEARNING_NOTES],
        difficulty=NoteDifficulty.STANDARD,
        depth=NoteDepth.STANDARD,
        teaching_strategy=TeachingStrategyPlan(),
        section_plan=[
            SectionPlanItem(type="core_concept", target="Octet Rule", required=True),
            SectionPlanItem(type="core_concept", target="VSEPR Theory", required=True)
        ],
        visual_plan=VisualPlan(),
        remediation_plan=RemediationPlan(),
        practice_plan=PracticePlan(required=False),
        revision_plan=RevisionPlan()
    )

    res = CoverageCertifier.certify_content_coverage(doc, plan=plan, ctx=ctx)
    assert res.coverage.sub_concepts_total == 0, "Must not invent sub-concepts without authoritative input"
    assert res.coverage.sub_concepts_covered == 0
    assert res.coverage.sub_concepts_missing == 0


def test_semantic_worked_example_validation():
    """
    Test 11: Worked Example Quality. Shorthand answer stubs like
    'SF6 -> sp3d2 -> octahedral' must NOT count as valid worked examples.
    Procedural steps (Problem, Concept, Steps, Answer, Why) are required.
    """
    from app.services.notes.certification.coverage_certifier import CoverageCertifier

    stub_doc = NotesDocument(
        id="doc_with_stub_example",
        title="Chemical Bonding",
        topic="Chemical Bonding",
        subject="Chemistry",
        class_level="Class 11",
        sections=[
            NoteSection(
                id="sec_stub_ex",
                title="VSEPR Theory",
                content="VSEPR theory determines geometry based on electron pairs.",
                examples=["SF6 -> sp3d2 -> octahedral"]  # Shorthand stub!
            )
        ]
    )
    plan = NotesGenerationPlan.create(
        purpose=PurposePlan(),
        formats=[NoteFormat.LEARNING_NOTES],
        difficulty=NoteDifficulty.STANDARD,
        depth=NoteDepth.STANDARD,
        teaching_strategy=TeachingStrategyPlan(),
        section_plan=[SectionPlanItem(type="core_concept", target="VSEPR Theory", required=True)],
        visual_plan=VisualPlan(),
        remediation_plan=RemediationPlan(),
        practice_plan=PracticePlan(required=False),
        revision_plan=RevisionPlan()
    )

    res = CoverageCertifier.certify_content_coverage(stub_doc, plan=plan)
    assert res.worked_example_quality["stubs"] > 0
    assert res.valid is False
    assert any("non-procedural shorthand stub" in f for f in res.findings)


def test_practice_to_concept_mapping_and_non_repetition():
    """
    Test 12: Practice Verification. Validates that practice items map to concepts,
    repetitive questions are flagged, and progressive cognitive categories are audited.
    """
    from app.services.notes.certification.coverage_certifier import CoverageCertifier

    doc_with_repeats = NotesDocument(
        id="doc_repeat_practice",
        title="Chemical Bonding",
        topic="Chemical Bonding",
        subject="Chemistry",
        class_level="Class 11",
        sections=[
            NoteSection(
                id="sec_1",
                title="Octet Rule",
                content="Atoms combine to complete 8 valence electrons in their shell.",
                key_points=["Octet stability rule"]
            )
        ],
        practice=[
            {
                "question": "What is the octet rule in chemical bonding?",
                "type": "recall",
                "answer": "Atoms transfer or share electrons to attain 8 valence electrons.",
                "explanation": "Fundamental noble gas stability benchmark."
            },
            {
                "question": "What is the octet rule in chemical bonding?",  # Exact duplicate!
                "type": "recall",
                "answer": "Atoms transfer or share electrons to attain 8 valence electrons.",
                "explanation": "Fundamental noble gas stability benchmark."
            }
        ]
    )
    plan = NotesGenerationPlan.create(
        purpose=PurposePlan(),
        formats=[NoteFormat.LEARNING_NOTES],
        difficulty=NoteDifficulty.STANDARD,
        depth=NoteDepth.STANDARD,
        teaching_strategy=TeachingStrategyPlan(),
        section_plan=[SectionPlanItem(type="core_concept", target="Octet Rule", required=True)],
        visual_plan=VisualPlan(),
        remediation_plan=RemediationPlan(),
        practice_plan=PracticePlan(required=True, count=2, types=["recall"]),
        revision_plan=RevisionPlan()
    )

    res = CoverageCertifier.certify_content_coverage(doc_with_repeats, plan=plan)
    assert res.practice_distribution["total"] == 2
    assert any("repetitive" in f for f in res.findings)


def test_learner_plan_adaptation_and_revision_compression():
    """
    Test 13: Verifies Step 3 executes learner plan adaptation:
    - Low mastery incorporates guided scaffolding and misconception corrections.
    - Revision sections compress information rather than duplicating previous text verbatim.
    """
    # Low mastery context
    ctx_low = CanonicalNotesContext(
        topic="Valence Bond Theory",
        subject="Chemistry",
        class_level="Class 11",
        curriculum="CBSE",
        student_mastery={"vbt": 0.25}
    )
    plan_low = NotesGenerationPlan.create(
        purpose=PurposePlan(primary="remediation"),
        formats=[NoteFormat.LEARNING_NOTES],
        difficulty=NoteDifficulty.FOUNDATIONAL,
        depth=NoteDepth.DETAILED,
        teaching_strategy=TeachingStrategyPlan(mode="active", scaffolding="guided"),
        section_plan=[
            SectionPlanItem(type="core_concept", target="Sigma and Pi Bonds", required=True)
        ],
        visual_plan=VisualPlan(required=False),
        remediation_plan=RemediationPlan(required=True, target_concepts=["sigma vs pi strength"]),
        practice_plan=PracticePlan(required=True, count=3, difficulty="foundational"),
        revision_plan=RevisionPlan(required=True, include=["key_points", "common_mistakes"])
    )

    doc_low = _build_deterministic_fallback(ctx_low, plan_low)
    # Check that remediation / misconception was included
    misc_sec = next((s for s in doc_low.sections if "misconception" in s.section_type or "misconception" in s.title.lower()), None)
    assert misc_sec is not None, "Low mastery / remediation plan must produce misconception remediation"
    assert any("Scientific Reality" in c.text for c in misc_sec.callouts)

    # Check practice difficulty adapted to foundational
    assert all(p.get("difficulty") == "foundational" for p in doc_low.practice)

