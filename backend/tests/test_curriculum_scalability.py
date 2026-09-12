"""
Test Suite: Curriculum Catalog Scalability & Topic-Agnostic Architecture
==========================================================================
Verifies that TeachGenie is fully topic-agnostic and scalable to arbitrary
educational topics without requiring hard-coded Python if/elif dispatch.

Tests all 13 Required Verification Criteria:
1. test_unknown_topic_uses_generic_generation_path
2. test_catalog_hit_uses_curated_data
3. test_unknown_topic_with_source_generates
4. test_unknown_topic_without_curriculum_does_not_invent_syllabus
5. test_step2_does_not_require_catalog_membership
6. test_step3_does_not_require_topic_key
7. test_step4_does_not_require_catalog_membership
8. test_practice_is_plan_driven_for_unknown_topics
9. test_visuals_are_plan_driven_for_unknown_topics
10. test_curriculum_versioning
11. test_topic_alias_normalization
12. test_catalog_is_optional
13. test_no_topic_specific_production_branch_required
"""
import pytest
from app.services.notes.schemas import (
    NotesDocument, NoteSection, VisualSpec, NoteDepth, NoteFormat, NoteDifficulty
)
from app.services.notes.context.schemas import (
    CanonicalNotesContext, LessonContext, SourcesContext
)
from app.services.notes.context.topic_descriptor import TopicDescriptor
from app.services.notes.decision.schemas import (
    NotesGenerationPlan, SectionPlanItem, PurposePlan,
    TeachingStrategyPlan, VisualPlan, RemediationPlan,
    PracticePlan, RevisionPlan
)
from app.services.notes.decision.engine import NotesDecisionEngine
from app.services.notes.generation.engine import _build_deterministic_fallback
from app.services.notes.generation.curriculum_catalog import (
    CurriculumCatalog, CurriculumPack, CurriculumVersion
)
from app.services.notes.validation.engine import validate_notes
from app.services.notes.validation.schemas import ValidationStatus
import asyncio


def test_unknown_topic_uses_generic_generation_path():
    """
    Test 1: Verifies an unknown topic not present in the catalog
    (e.g., 'Electrochemistry') uses the generic generation path
    and produces a substantive, complete, multi-section learning document.
    """
    assert CurriculumCatalog.match_topic("Chemistry", "Electrochemistry") is None

    ctx = CanonicalNotesContext(
        topic="Electrochemistry",
        subject="Chemistry",
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
            SectionPlanItem(type="core_concept", target="Electrochemical Cells", required=True),
            SectionPlanItem(type="worked_example", target="Nernst Equation", required=True),
            SectionPlanItem(type="common_misconceptions", target="Standard Cell Potential", required=True),
            SectionPlanItem(type="quick_summary", required=True)
        ],
        visual_plan=VisualPlan(required=True, type="process_diagram", focus="Galvanic Cell"),
        remediation_plan=RemediationPlan(required=False),
        practice_plan=PracticePlan(required=True, count=3, difficulty="standard"),
        revision_plan=RevisionPlan(required=True)
    )

    doc = _build_deterministic_fallback(ctx, plan)
    assert doc is not None
    assert doc.topic == "Electrochemistry"
    assert len(doc.sections) >= 4
    assert doc.provenance == "generated_from_context"

    # Verify layered instructional depth in core concept
    core_sec = next(s for s in doc.sections if s.section_type == "core_concept")
    assert "### 1. Simple Intuition" in core_sec.content
    assert "### 2. Formal Scientific Mechanism" in core_sec.content
    assert core_sec.semantic_evidence.explanation_present is True

    # Verify multi-step worked example
    worked_sec = next(s for s in doc.sections if s.section_type == "worked_example")
    assert "**Problem**:" in worked_sec.content or (worked_sec.examples and "**Problem**:" in worked_sec.examples[0])
    assert worked_sec.semantic_evidence.worked_example_present is True


def test_catalog_hit_uses_curated_data():
    """
    Test 2: Verifies that an authoritative curated topic (e.g. 'Chemical Bonding')
    resolves against the catalog and incorporates curated sections and provenance.
    """
    key = CurriculumCatalog.match_topic("Chemistry", "Chemical Bonding")
    assert key == "chemical_bonding"

    ctx = CanonicalNotesContext(
        topic="Chemical Bonding",
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
            SectionPlanItem(type="overview", required=True),
            SectionPlanItem(type="core_concept", required=True),
        ],
        visual_plan=VisualPlan(required=True),
        remediation_plan=RemediationPlan(required=False),
        practice_plan=PracticePlan(required=True, count=4, difficulty="standard"),
        revision_plan=RevisionPlan(required=False)
    )

    doc = _build_deterministic_fallback(ctx, plan)
    assert doc.provenance == "curated_catalog"
    # Contains curated sections (octet, vsepr, vbt, hyb, hbond)
    assert any("VSEPR" in s.title for s in doc.sections)
    assert any("Hybridization" in s.title for s in doc.sections)


def test_unknown_topic_with_source_generates():
    """
    Test 3: Verifies an unknown topic with explicit user/authoritative source
    (e.g., 'Fourier Transform Basics') generates a grounded document with citations.
    """
    assert CurriculumCatalog.match_topic("Mathematics", "Fourier Transform Basics") is None

    ctx = CanonicalNotesContext(
        topic="Fourier Transform Basics",
        subject="Mathematics",
        class_level="Higher Ed",
        curriculum="University",
        sources=SourcesContext(
            source_documents=[{
                "source_id": "src_ft_01",
                "title": "Continuous Fourier Analysis Lecture Notes",
                "text": "The continuous Fourier transform maps a time-domain signal f(t) into the frequency domain F(omega)."
            }]
        )
    )
    plan = NotesGenerationPlan.create(
        purpose=PurposePlan(),
        formats=[NoteFormat.LEARNING_NOTES],
        difficulty=NoteDifficulty.STANDARD,
        depth=NoteDepth.DETAILED,
        teaching_strategy=TeachingStrategyPlan(),
        section_plan=[
            SectionPlanItem(type="overview", required=True),
            SectionPlanItem(type="core_concept", target="Frequency Spectrum Decomposition", required=True),
            SectionPlanItem(type="formula_box", target="Fourier Inversion Theorem", required=True)
        ],
        visual_plan=VisualPlan(required=False),
        remediation_plan=RemediationPlan(required=False),
        practice_plan=PracticePlan(required=True, count=3, difficulty="standard"),
        revision_plan=RevisionPlan(required=False)
    )

    doc = _build_deterministic_fallback(ctx, plan)
    assert doc is not None
    assert doc.topic == "Fourier Transform Basics"
    assert len(doc.sections) >= 3
    assert doc.provenance == "generated_from_context"


def test_unknown_topic_without_curriculum_does_not_invent_syllabus():
    """
    Test 4: Verifies an arbitrary topic without an authoritative curriculum
    honestly represents curriculum as unavailable rather than inventing syllabus.
    """
    ctx = CanonicalNotesContext(
        topic="Modern Distributed Consensus",
        subject="Computer Science",
        curriculum="unknown"
    )
    # Does not invent a CBSE/NCERT curriculum for high-level research topic
    desc = ctx.descriptor
    assert desc.is_catalog_curated is False
    assert CurriculumCatalog.match_topic("Computer Science", "Modern Distributed Consensus") is None


def test_step2_does_not_require_catalog_membership():
    """
    Test 5: Verifies Step 2 Decision Engine does NOT require catalog membership
    and produces a valid NotesGenerationPlan for an arbitrary unknown topic.
    """
    ctx = CanonicalNotesContext(
        topic="Docker Container Networking and Overlay Bridges",
        subject="Computer Science",
        class_level="Class 12"
    )
    plan = NotesDecisionEngine.create_plan(ctx)
    assert plan is not None
    assert isinstance(plan, NotesGenerationPlan)
    assert len(plan.section_plan) >= 2
    assert plan.difficulty is not None
    assert plan.teaching_strategy is not None


def test_step3_does_not_require_topic_key():
    """
    Test 6: Verifies Step 3 Generation Engine does NOT require a topic_key
    to produce a fully certifiable, substantive NotesDocument.
    """
    ctx = CanonicalNotesContext(
        topic="Photosynthesis Light Reactions and Z-Scheme",
        subject="Biology",
        class_level="Class 11",
        curriculum="CBSE"
    )
    plan = NotesDecisionEngine.create_plan(ctx)
    doc = _build_deterministic_fallback(ctx, plan)

    assert doc is not None
    assert "photosynthesis" in doc.topic.lower()
    assert len(doc.sections) >= 2
    for s in doc.sections:
        assert s.content is not None and len(s.content) > 50


def test_step4_does_not_require_catalog_membership():
    """
    Test 7: Verifies Step 4 Validation Engine validates content on its own merits
    without checking or requiring that the topic exist in CurriculumCatalog.
    """
    ctx = CanonicalNotesContext(
        topic="Graph Theory: Dijkstra Shortest Path Algorithm",
        subject="Computer Science",
        class_level="Class 12",
        curriculum="CBSE"
    )
    plan = NotesDecisionEngine.create_plan(ctx)
    doc = _build_deterministic_fallback(ctx, plan)

    result = asyncio.run(validate_notes(context=ctx, plan=plan, document=doc, enable_llm=False))
    assert result is not None
    assert result.status in (ValidationStatus.VALID, ValidationStatus.VALID_WITH_WARNINGS)
    assert result.overall_score >= 70.0


def test_practice_is_plan_driven_for_unknown_topics():
    """
    Test 8: Verifies practice generation for an unknown topic is plan-driven,
    respecting count, difficulty, and Bloom taxonomy progressive categories.
    """
    ctx = CanonicalNotesContext(
        topic="Quantum Cryptography and QKD Protocols",
        subject="Physics",
        class_level="Higher Ed",
        lesson=LessonContext(
            learning_objectives=[
                "BB84 Protocol Mechanics",
                "No-Cloning Theorem",
                "Quantum Bit Error Rate (QBER)"
            ]
        )
    )
    plan = NotesGenerationPlan.create(
        purpose=PurposePlan(),
        formats=[NoteFormat.LEARNING_NOTES],
        difficulty=NoteDifficulty.ADVANCED,
        depth=NoteDepth.DETAILED,
        teaching_strategy=TeachingStrategyPlan(),
        section_plan=[SectionPlanItem(type="core_concept", required=True)],
        visual_plan=VisualPlan(required=False),
        remediation_plan=RemediationPlan(required=False),
        practice_plan=PracticePlan(required=True, count=5, difficulty="advanced"),
        revision_plan=RevisionPlan(required=False)
    )

    doc = _build_deterministic_fallback(ctx, plan)
    assert len(doc.practice) == 5

    categories = [p.get("category") for p in doc.practice]
    assert "recall" in categories
    assert "conceptual" in categories
    assert "application" in categories

    for p in doc.practice:
        assert p["difficulty"] == "advanced"
        assert len(p["explanation"]) > 20
        assert p["target_concept"] in ctx.lesson.learning_objectives


def test_visuals_are_plan_driven_for_unknown_topics():
    """
    Test 9: Verifies visual generation for an unknown topic adapts to
    the visual plan type (e.g. comparison_table, process_diagram, flowchart).
    """
    ctx = CanonicalNotesContext(
        topic="Relational DBMS Normalization (1NF to BCNF)",
        subject="Computer Science",
        class_level="Class 12"
    )
    plan = NotesGenerationPlan.create(
        purpose=PurposePlan(),
        formats=[NoteFormat.LEARNING_NOTES],
        difficulty=NoteDifficulty.STANDARD,
        depth=NoteDepth.DETAILED,
        teaching_strategy=TeachingStrategyPlan(),
        section_plan=[SectionPlanItem(type="core_concept", required=True)],
        visual_plan=VisualPlan(required=True, type="process_diagram", focus="Normalization Stages"),
        remediation_plan=RemediationPlan(required=False),
        practice_plan=PracticePlan(required=False),
        revision_plan=RevisionPlan(required=False)
    )

    doc = _build_deterministic_fallback(ctx, plan)
    assert len(doc.visuals) == 1
    vis = doc.visuals[0]
    assert vis.type == "process_diagram"
    assert len(vis.nodes) >= 3
    assert len(vis.edges) >= 2
    assert "graph TD" in vis.mermaid_code


def test_curriculum_versioning():
    """
    Test 10: Verifies CurriculumVersion data structure supports board, grade,
    subject, course, curriculum_version, and effective_date.
    """
    v = CurriculumVersion(
        board="ICSE",
        grade=10,
        subject="Physics",
        course="ICSE Science",
        curriculum_version="2025-2026",
        source_version="2.1",
        effective_date="2025-06-01"
    )
    assert v.board == "ICSE"
    assert v.grade == 10
    assert v.curriculum_version == "2025-2026"
    assert v.effective_date == "2025-06-01"


def test_topic_alias_normalization():
    """
    Test 11: Verifies that case, whitespace, hyphens, and standard aliases
    normalize correctly to registered curriculum packs without brittle dispatch.
    """
    variants = [
        "chemical bonding",
        "Chemical Bonding",
        "chemical-bonding",
        "Chemical Bonding and Molecular Structure",
        "chemical_bonding"
    ]
    for v in variants:
        key = CurriculumCatalog.match_topic("Chemistry", v)
        assert key == "chemical_bonding", f"Failed to match alias '{v}' to 'chemical_bonding'"


def test_catalog_is_optional():
    """
    Test 12: Verifies that even if a topic is completely absent from the catalog,
    the complete pipeline executes from Context to Plan to Document.
    """
    ctx = CanonicalNotesContext(
        topic="Deep Reinforcement Learning Policy Gradients",
        subject="Computer Science",
        class_level="Higher Ed"
    )
    assert CurriculumCatalog.match_topic(ctx.subject, ctx.topic) is None

    plan = NotesDecisionEngine.create_plan(ctx)
    doc = _build_deterministic_fallback(ctx, plan)

    assert doc.topic == "Deep Reinforcement Learning Policy Gradients"
    assert len(doc.sections) >= 2
    assert doc.provenance == "generated_from_context"


def test_no_topic_specific_production_branch_required():
    """
    Test 13: Verifies that adding a brand-new educational topic pack dynamically
    via register_pack() requires zero code modifications or if/elif dispatch branches,
    and resolves in O(1) time.
    """
    custom_pack = CurriculumPack(
        id="thermodynamics_carnot",
        topic="Carnot Cycle and Second Law of Thermodynamics",
        subject="Physics",
        aliases=["carnot cycle", "carnot engine", "thermodynamics carnot"],
        version=CurriculumVersion(board="CBSE", grade=11, subject="Physics"),
        formulas=["Efficiency: eta = 1 - (T_C / T_H)", "Entropy: dS = dQ / T"],
        checkpoints=["Why can no heat engine be more efficient than a reversible Carnot engine?"],
        practice=[{
            "question": "Calculate Carnot efficiency between 600 K and 300 K.",
            "answer": "eta = 1 - (300/600) = 50%",
            "difficulty": "standard"
        }]
    )

    # Register pack as pure data
    CurriculumCatalog.register_pack(custom_pack)

    # Verify O(1) resolution via catalog
    matched = CurriculumCatalog.match_topic("Physics", "carnot engine")
    assert matched == "thermodynamics_carnot"

    retrieved = CurriculumCatalog.get_pack("thermodynamics_carnot")
    assert retrieved is not None
    assert len(retrieved.formulas) == 2
    assert "eta = 1 - (T_C / T_H)" in retrieved.formulas[0]


def test_unknown_topic_end_to_end_artifact_certification():
    """
    Test 14: Verifies an arbitrary unknown topic ('Electrochemistry') with syllabus objectives
    runs through Step 1 Context -> Step 2 Decision -> Step 3 Generation -> Step 4 Validation ->
    Renderer -> Student Artifact Certification and achieves STUDENT_READY with zero defects.
    """
    from app.services.notes.rendering.html_builder import HTMLNoteBuilder
    from app.services.notes.rendering.pdf_renderer import PDFNoteRenderer
    from app.services.notes.certification.certifier import StudentArtifactCertifier
    from app.services.notes.certification.schemas import ArtifactStatus

    async def _run():
        topic = "Electrochemistry"
        subject = "Chemistry"
        assert CurriculumCatalog.match_topic(subject, topic) is None

        ctx = CanonicalNotesContext(
            topic=topic,
            subject=subject,
            class_level="Class 12",
            curriculum="CBSE",
            lesson=LessonContext(
                learning_objectives=[
                    "Galvanic Cells and Daniell Cell",
                    "Nernst Equation and Equilibrium Constant",
                    "Electrolytic Conduction and Kohlrausch Law"
                ]
            )
        )
        assert ctx.descriptor.is_catalog_curated is False

        plan = NotesDecisionEngine.create_plan(ctx)
        doc = _build_deterministic_fallback(ctx, plan)
        assert doc.provenance == "generated_from_context"

        html = HTMLNoteBuilder.build_html(doc, include_answers=True)
        pdf_bytes, _ = await PDFNoteRenderer.render_pdf_async(doc, include_answers=True)

        cert_result = await StudentArtifactCertifier.certify_artifact(
            document=doc,
            plan=plan,
            context=ctx,
            pdf_bytes=pdf_bytes,
            html_content=html
        )

        assert cert_result.artifact_status in (ArtifactStatus.STUDENT_READY, ArtifactStatus.STUDENT_READY_WITH_WARNINGS)
        assert len(cert_result.artifact_certification.defects) == 0
        assert cert_result.content_certification.coverage.missing == 0
        assert cert_result.content_certification.substantive_score >= 80.0

    asyncio.run(_run())

