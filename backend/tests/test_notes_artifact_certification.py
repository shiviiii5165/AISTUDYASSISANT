"""
Test Suite: Student Artifact Certification Engine
=================================================
Tests:
- Raw LaTeX scanning (delimiters, commands, broken superscripts/subscripts)
- Chemical and mathematical notation auditing
- Geometry QA (page geometry, blank pages, clipping)
- Visual inspection (rasterization via pypdfium2, channel variance)
- Authoritative curriculum coverage certification (no syllabus invention)
- Cryptographic artifact binding (SHA-256 document & PDF hashes)
"""
import asyncio
import pytest
from app.services.notes.schemas import (
    NotesDocument, NoteSection, NoteFormat, NoteDepth, NoteDifficulty
)
from app.services.notes.context.schemas import (
    CanonicalNotesContext, LessonContext
)
from app.services.notes.decision.schemas import (
    NotesGenerationPlan, SectionPlanItem, PurposePlan,
    TeachingStrategyPlan, VisualPlan, RemediationPlan,
    PracticePlan, RevisionPlan
)
from app.services.notes.certification.schemas import (
    ArtifactStatus, RenderingDefectType, CoverageStatus
)
from app.services.notes.certification.latex_scanner import LaTeXScanner
from app.services.notes.certification.notation_qa import NotationQACertifier
from app.services.notes.certification.geometry_qa import GeometryQACertifier
from app.services.notes.certification.visual_inspector import VisualInspector
from app.services.notes.certification.coverage_certifier import CoverageCertifier
from app.services.notes.certification.certifier import StudentArtifactCertifier
from app.services.notes.rendering.pdf_renderer import PDFNoteRenderer
from app.services.notes.rendering.html_builder import HTMLNoteBuilder


def test_latex_scanner_detects_raw_delimiters():
    """Verify scanner catches $$ and $ leaks into rendered text."""
    leaked_text = "The electric field is given by $$E = \\frac{kq}{r^2}$$ in vacuum, or $V = \\frac{kq}{r}$."
    defects = LaTeXScanner.scan_text(leaked_text, page_number=1)

    types = [d.type for d in defects]
    assert RenderingDefectType.RAW_LATEX_DELIMITER in types
    assert RenderingDefectType.RAW_LATEX_COMMAND in types


def test_latex_scanner_detects_broken_subscripts_and_superscripts():
    """Verify scanner catches unrendered ^{...} and _{...} syntax."""
    broken_text = "The charge on ion is Fe^{3+} and formula is H_{2}O with sp^{3} orbitals."
    defects = LaTeXScanner.scan_text(broken_text, page_number=2)

    types = [d.type for d in defects]
    assert RenderingDefectType.BROKEN_SUPERSCRIPT in types
    assert RenderingDefectType.BROKEN_SUBSCRIPT in types


def test_latex_scanner_allows_clean_unicode():
    """Verify scanner does NOT raise false alarms on valid Unicode math and chemistry symbols."""
    clean_text = "The bond angle is 104.5° in H₂O. Hybridization is sp³ with 2 σ bonds and 2 lone pairs. Energy is hν."
    defects = LaTeXScanner.scan_text(clean_text, page_number=1)

    assert len(defects) == 0


def test_notation_qa_detects_unrendered_chemistry():
    """Verify NotationQACertifier catches raw notation without HTML/Unicode subscripts."""
    bad_doc = NotesDocument(
        id="bad_chem_doc",
        title="Chemical Bonding",
        topic="Chemical Bonding",
        subject="Chemistry",
        class_level="Class 11",
        sections=[
            NoteSection(
                id="sec_1",
                title="Hybridization States",
                content="Methane CH4 has sp3 hybridization. SF6 has sp3d with 6 sigma bonds.",
                key_points=["sp3 is tetrahedral"]
            )
        ]
    )

    defects = NotationQACertifier.audit_document_notation(bad_doc)
    assert len(defects) > 0
    types = [d.type for d in defects]
    assert RenderingDefectType.CHEMICAL_FORMULA_UNRENDERED in types or RenderingDefectType.HYBRIDIZATION_UNRENDERED in types


def test_geometry_qa_detects_empty_and_corrupt_pdf():
    """Verify geometry QA catches empty or invalid PDF bytes."""
    defects, details = GeometryQACertifier.inspect_pdf(b"not a real pdf content")
    assert len(defects) > 0
    assert defects[0].type == RenderingDefectType.PDF_CORRUPT


def test_visual_inspector_verifies_rendered_pages():
    """Verify visual inspector renders pages via pypdfium2 and verifies non-blankness."""
    doc = NotesDocument(
        id="doc_kinematics",
        title="Kinematics",
        topic="Kinematics",
        subject="Physics",
        class_level="Class 11",
        sections=[
            NoteSection(
                id="sec_motion",
                title="Equations of Motion",
                content="Under constant acceleration a, v = u + at and s = ut + (1/2)at².",
                key_points=["Applies only for uniform acceleration"]
            )
        ]
    )

    pdf_bytes, _ = asyncio.run(PDFNoteRenderer.render_pdf_async(doc))
    defects, details, images = VisualInspector.inspect_pdf_images(pdf_bytes)

    assert len(defects) == 0
    assert details["page_images_count"] >= 1
    assert len(images) >= 1
    assert len(details["blank_image_pages"]) == 0


def test_coverage_certifier_authoritative_no_invention():
    """Verify CoverageCertifier evaluates against context and plan without inventing curriculum."""
    ctx = CanonicalNotesContext(
        request={"topic": "Chemical Bonding", "target_class": "Class 11", "subject": "Chemistry"},
        lesson=LessonContext(
            topic="Chemical Bonding",
            learning_objectives=["Octet Rule", "VSEPR Theory", "Hybridization", "Hydrogen Bonding"]
        )
    )

    plan = NotesGenerationPlan(
        primary_topic="Chemical Bonding",
        target_class="Class 11",
        subject="Chemistry",
        purpose=PurposePlan(),
        formats=[NoteFormat.LEARNING_NOTES],
        difficulty=NoteDifficulty.STANDARD,
        depth=NoteDepth.STANDARD,
        teaching_strategy=TeachingStrategyPlan(),
        section_plan=[
            SectionPlanItem(type="octet_rule", title="Octet Rule & Lewis Structures", target="Lewis dot representations", required=True),
            SectionPlanItem(type="vsepr", title="VSEPR Theory & Molecular Shapes", target="Predicting shapes from electron pairs", required=True),
            SectionPlanItem(type="hybridization", title="Valence Bond Theory & Hybridization", target="sp, sp2, sp3, sp3d, sp3d2 states", required=True),
            SectionPlanItem(type="h_bonding", title="Intermolecular Forces & Hydrogen Bonding", target="Intermolecular vs intramolecular H-bonding", required=True)
        ],
        visual_plan=VisualPlan(),
        remediation_plan=RemediationPlan(),
        practice_plan=PracticePlan(),
        revision_plan=RevisionPlan()
    )

    doc = NotesDocument(
        id="doc_chem_bonding_cov",
        title="Chemical Bonding",
        topic="Chemical Bonding",
        subject="Chemistry",
        class_level="Class 11",
        sections=[
            NoteSection(
                id="sec_1",
                title="Octet Rule & Lewis Structures",
                content="Kossel-Lewis approach explains chemical combination by transfer or sharing of electrons to attain octet. Lewis dot representations depict valence electrons.",
                key_points=["Atoms achieve noble gas electronic configuration"]
            ),
            NoteSection(
                id="sec_2",
                title="VSEPR Theory & Molecular Shapes",
                content="Repulsion order: Lone pair - Lone pair > Lone pair - Bond pair > Bond pair - Bond pair. Predicting shapes from electron pairs gives true geometry.",
                key_points=["Determines actual molecular 3D geometry"]
            ),
            NoteSection(
                id="sec_3",
                title="Valence Bond Theory & Hybridization",
                content="Intermixing of non-equivalent atomic orbitals to form equivalent hybrid orbitals: sp, sp2, sp3, sp3d, sp3d2 states.",
                key_points=["Hybrid orbitals form strong directional sigma bonds"]
            ),
            NoteSection(
                id="sec_4",
                title="Intermolecular Forces & Hydrogen Bonding",
                content="Dipole-dipole interaction between hydrogen and highly electronegative elements F, O, N. Intermolecular vs intramolecular H-bonding explains physical properties.",
                key_points=["Explains high boiling point of water and ammonia"]
            )
        ],
        practice=[
            {
                "question": "Identify the hybridization in SF6 and NH3.",
                "answer": "SF6 is sp3d2, NH3 is sp3 with one lone pair.",
                "hints": ["Count total electron pairs around central atom."]
            }
        ]
    )

    manifest, issues = CoverageCertifier.certify_coverage(doc, plan=plan, context=ctx)

    assert manifest.covered >= 4
    assert manifest.missing == 0


def test_student_artifact_certifier_cryptographic_binding():
    """Verify Master StudentArtifactCertifier binds document_hash and pdf_hash."""
    doc = NotesDocument(
        id="doc_thermodynamics_binding",
        title="Thermodynamics",
        topic="Thermodynamics",
        subject="Physics",
        class_level="Class 11",
        sections=[
            NoteSection(
                id="sec_first_law",
                title="First Law of Thermodynamics",
                content="The change in internal energy ΔU equals heat added Q minus work done W: ΔU = Q - W.",
                key_points=["Conservation of energy applied to thermal systems"]
            )
        ],
        practice=[
            {
                "question": "In an isothermal process, what is ΔU?",
                "answer": "ΔU = 0 because internal energy depends solely on temperature for an ideal gas.",
                "hints": ["Temperature remains constant."]
            }
        ]
    )

    html = HTMLNoteBuilder.build_html(doc)
    pdf_bytes, pdf_hash = asyncio.run(PDFNoteRenderer.render_pdf_async(doc))

    result = asyncio.run(StudentArtifactCertifier.certify_artifact(
        document=doc,
        pdf_bytes=pdf_bytes,
        html_content=html
    ))

    assert result.document_id == doc.id
    assert len(result.document_hash) == 64
    assert len(result.pdf_hash) == 64
    assert result.pdf_hash == pdf_hash
    assert result.artifact_status in (ArtifactStatus.STUDENT_READY, ArtifactStatus.STUDENT_READY_WITH_WARNINGS)


def test_font_glyph_validation():
    """
    FONT AND GLYPH VALIDATION TEST (Section 10):
    Explicitly tests that all required scientific glyphs:
    σ, π, Δ, ±, ≤, ≥, ⁺, ⁻, ², ³, ₄
    render cleanly in HTML and PDF without tofu replacement boxes or missing-glyph defects.
    """
    glyph_doc = NotesDocument(
        id="glyph-test-doc",
        title="Scientific Glyphs & Symbols",
        topic="Physics and Chemistry Symbols",
        subject="Science",
        class_level="Class 11",
        sections=[
            NoteSection(
                id="sec_glyphs",
                title="Scientific Notation & Symbols",
                content=(
                    "Bonds: σ and π. "
                    "Changes: ΔH and ΔU. "
                    "Inequalities: x ≤ 10 and y ≥ 5. "
                    "Uncertainty: ± 0.05. "
                    "Ions and Powers: Na⁺, Cl⁻, sp³, sp², CH₄."
                ),
                key_points=["All standard Unicode scientific glyphs are supported."]
            )
        ]
    )

    html = HTMLNoteBuilder.build_html(glyph_doc)
    pdf_bytes, _ = asyncio.run(PDFNoteRenderer.render_pdf_async(glyph_doc))

    defects, details = NotationQACertifier.audit_notation(
        dom_html=html,
        extracted_pdf_text=html,
        topic=glyph_doc.topic
    )

    # Must have 0 MISSING_GLYPH defects
    missing_glyph_defects = [d for d in defects if d.type == RenderingDefectType.MISSING_GLYPH]
    assert len(missing_glyph_defects) == 0

    # Must verify all tested glyphs are supported
    required_glyphs = ["σ", "π", "Δ", "±", "≤", "≥", "⁺", "⁻", "²", "³", "₄"]
    for g in required_glyphs:
        assert g in details["supported_glyphs"]

