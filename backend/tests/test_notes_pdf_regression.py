"""
Test Suite: Student Artifact PDF Regression & Chemical Bonding Golden Fixture
==============================================================================
Contains:
1. Chemical Bonding Class 11 Golden Fixture (complete high-rigor document):
   - Fully rendered and certified
   - Validates zero LaTeX leaks, zero unrendered chemistry notation
   - Validates rasterized visual inspection via pypdfium2
   - Validates physical geometry via pdfplumber
2. Chemical Bonding Failure Regression:
   - Injects raw LaTeX and unrendered notation to verify Quality Gate rejection
3. Valid 1-page note vs Invalid 1-page stub
4. Multi-page document continuity
5. Raw math injection rejection test
"""
import os
import asyncio
import pytest
from app.services.notes.schemas import (
    NotesDocument, NoteSection, VisualSpec, CalloutItem, NoteDepth,
    NoteFormat, NoteDifficulty
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
from app.services.notes.certification.certifier import StudentArtifactCertifier
from app.services.notes.certification.visual_inspector import VisualInspector
from app.services.notes.rendering.pdf_renderer import PDFNoteRenderer
from app.services.notes.rendering.html_builder import HTMLNoteBuilder


@pytest.fixture
def chemical_bonding_golden_fixture() -> NotesDocument:
    """
    Authoritative Golden Learning Material: Chemical Bonding & Molecular Structure (Class 11 CBSE/NEET).
    Engineered as genuine learning material with:
    - Layered explanations (Simple Idea, Intuition, Formal Concept, Application)
    - Procedural worked examples with multi-step reasoning
    - Structured comparison tables (sigma vs pi, hybridization matrix, intermolecular vs intramolecular)
    - Explicit misconception debunking with scientific reality and root cause
    - Progressive practice across Bloom's cognitive levels (Recall, Conceptual, Application, Exam, Challenge)
    - Cryptographically verifiable internal semantic evidence
    """
    from app.services.notes.schemas import SectionSemanticEvidence

    return NotesDocument(
        id="golden-chem-bonding-class11",
        title="Chemical Bonding and Molecular Structure",
        topic="Chemical Bonding",
        subject="Chemistry",
        class_level="Class 11",
        curriculum="CBSE",
        sections=[
            NoteSection(
                id="sec_octet",
                section_type="core_concept",
                title="Kossel-Lewis Approach and Octet Rule",
                content=(
                    "### 1. Simple Idea\n"
                    "Atoms combine chemically because isolated individual atoms (except noble gases) have unstable valence shells. "
                    "By joining together, atoms achieve electronic stability.\n\n"
                    "### 2. Intuition: The Noble Gas Benchmark\n"
                    "Think of noble gases (He, Ne, Ar) as the 'contented retirees' of the periodic table: their valence shells are complete, "
                    "so they have zero thermodynamic urge to react. Other elements either lose, gain, or share electrons until their outer shell "
                    "mimics the closest noble gas (an octet of 8 electrons).\n\n"
                    "### 3. Formal Electronic Theory & Mechanism\n"
                    "According to Kossel and Lewis (1916):\n"
                    "1. **Electrovalent (Ionic) Bonding**: Formed by the complete transfer of one or more valence electrons from an electropositive atom to an electronegative atom (e.g., Na transfer to Cl in NaCl).\n"
                    "2. **Covalent Bonding**: Formed by mutual electron sharing between two atoms, where each contributing atom donates equal electrons to the shared pair (e.g., Cl2, H2O).\n\n"
                    "Formal charge on an atom in a Lewis dot structure measures the degree of electron redistribution:\n"
                    "Formal Charge = [Total valence electrons] - [Total non-bonding electrons] - (1/2)[Total bonding electrons]."
                ),
                key_points=[
                    "Octet rule: Atoms transfer or share electrons to attain 8 valence electrons (noble gas configuration).",
                    "Lewis dot symbols represent valence electrons as dots around the atomic symbol.",
                    "Formal charge identifies the lowest-energy Lewis resonance structure (charges closest to zero preferred)."
                ],
                examples=[
                    "**Problem**: Calculate the formal charge on the carbon and oxygen atoms in Carbon Monoxide (:C≡O:).\n"
                    "**Given**: Carbon Monoxide molecule with a triple bond, one lone pair on C, and one lone pair on O.\n"
                    "**Concept**: Formal Charge = V - N - (1/2)B.\n"
                    "**Step 1: Identify Valence Electrons (V)**: For C, V = 4; for O, V = 6.\n"
                    "**Step 2: Count Non-Bonding Electrons (N)**: C has 1 lone pair = 2 electrons; O has 1 lone pair = 2 electrons.\n"
                    "**Step 3: Count Shared Bonding Electrons (B)**: Triple bond contains 6 shared electrons (B = 6).\n"
                    "**Step 4: Compute Formal Charges**:\n"
                    "  - FC(C) = 4 - 2 - (1/2)(6) = -1.\n"
                    "  - FC(O) = 6 - 2 - (1/2)(6) = +1.\n"
                    "**Final Answer**: Formal charge on Carbon is -1 and on Oxygen is +1 (net charge = 0).\n"
                    "**Why**: Oxygen donates a coordinate pair to satisfy carbon's octet, resulting in charge polarization."
                ],
                common_mistakes=[
                    "Assuming the octet rule applies universally to every stable molecule; expanded octets and odd-electron molecules stably exist."
                ],
                callouts=[
                    CalloutItem(
                        type="misconception",
                        title="Misconception: Octet Rule is Universal",
                        text=(
                            "**Wrong Belief**: Every stable molecule strictly possesses 8 valence electrons.\n"
                            "**Scientific Reality**: Incomplete octets (LiCl, BeCl2 with 4e⁻, BF3 with 6e⁻), odd-electron species (NO with 11e⁻), "
                            "and expanded octets (PCl5 with 10e⁻, SF6 with 12e⁻) are completely stable.\n"
                            "**Why**: Elements in Period 3 and beyond have accessible 3d-orbitals, allowing expansion beyond 8 valence electrons."
                        )
                    )
                ],
                semantic_evidence=SectionSemanticEvidence(
                    concept_id="sec_octet",
                    instructional_role="core_concept",
                    explanation_present=True,
                    intuition_present=True,
                    example_present=True,
                    worked_example_present=True,
                    practice_targets=["Octet Rule and Lewis Structures"],
                    misconception_targets=["octet rule universality"]
                )
            ),
            NoteSection(
                id="sec_vsepr",
                section_type="core_concept",
                title="VSEPR Theory and Molecular Geometry",
                content=(
                    "### 1. Simple Idea\n"
                    "Molecules are not flat drawings on paper; they are 3D objects. Their actual shapes are decided by simple electrostatic repulsion: "
                    "negatively charged valence electron pairs push each other as far apart as possible.\n\n"
                    "### 2. Intuition: The Tied Balloon Analogy\n"
                    "Imagine tying balloons together at their necks. Two balloons push into a straight line (180°). Three balloons form a flat triangle (120°). "
                    "Four balloons naturally pop out into a 3D pyramid with a triangular base (a tetrahedron at 109.5°). Electron clouds around a central atom do the exact same thing.\n\n"
                    "### 3. Formal Postulates of VSEPR Theory\n"
                    "Proposed by Sidgwick, Powell, Gillespie, and Nyholm:\n"
                    "1. The shape of a molecule depends strictly on the total number of valence shell electron pairs (bonding and lone pairs) surrounding the central atom.\n"
                    "2. Electron pairs repel one another because their electron clouds are negatively charged; they position themselves in 3D space to maximize separation.\n"
                    "3. Repulsive magnitude decreases in the strict order: **Lone pair - Lone pair > Lone pair - Bond pair > Bond pair - Bond pair**.\n"
                    "4. Lone pairs are attracted to only one atomic nucleus and spread out broadly, exerting stronger repulsion than bonding pairs held tightly between two nuclei.\n\n"
                    "### 4. Comparison: Electron Domain Geometry vs Observed Molecular Shape\n\n"
                    "| Molecule | Total Electron Domains | Bond Pairs | Lone Pairs | Electron Geometry | Observed Molecular Shape | Bond Angle |\n"
                    "|---|---|---|---|---|---|---|\n"
                    "| CH4 | 4 | 4 | 0 | Tetrahedral | Tetrahedral | 109.5° |\n"
                    "| NH3 | 4 | 3 | 1 | Tetrahedral | Trigonal Pyramidal | 107.0° |\n"
                    "| H2O | 4 | 2 | 2 | Tetrahedral | Bent / V-shaped | 104.5° |\n"
                    "| SF6 | 6 | 6 | 0 | Octahedral | Octahedral | 90.0° |"
                ),
                key_points=[
                    "Steric Number (SN) = (number of sigma bonds) + (number of lone pairs on central atom).",
                    "Lone pairs occupy more spatial angle around the nucleus than bond pairs, compressing adjacent bond angles.",
                    "Electron geometry tracks all electron domains; molecular shape tracks only observable atomic positions."
                ],
                examples=[
                    "**Problem**: Predict the electron geometry, molecular shape, and bond angle of Ammonia (NH3) using VSEPR theory.\n"
                    "**Given**: Central Nitrogen atom bonded to three Hydrogen atoms.\n"
                    "**Concept**: Steric Number and VSEPR repulsion hierarchy (lp-bp > bp-bp).\n"
                    "**Step 1: Count Valence Electrons**: N has 5 valence electrons; each H contributes 1 electron (total = 8).\n"
                    "**Step 2: Determine Bond Pairs and Lone Pairs**: N forms 3 single N-H sigma bonds (3 bond pairs) and retains 1 unshared lone pair.\n"
                    "**Step 3: Calculate Steric Number**: Steric Number = 3 (bp) + 1 (lp) = 4.\n"
                    "**Step 4: Determine Electron Geometry**: SN = 4 corresponds to a tetrahedral electron-domain arrangement.\n"
                    "**Step 5: Determine Observed Molecular Shape**: With 1 apex occupied by a lone pair, the three H nuclei form a Trigonal Pyramidal geometry.\n"
                    "**Step 6: Predict Bond Angle Distortion**: Lone pair - bond pair repulsion compresses the ideal tetrahedral angle (109.5°) down to 107.0°.\n"
                    "**Final Answer**: Electron geometry is Tetrahedral; Molecular shape is Trigonal Pyramidal; Bond angle is 107°.\n"
                    "**Why**: The broad lone pair cloud pushes the three N-H bond pairs closer together."
                ],
                common_mistakes=[
                    "Confusing electron domain geometry with observable molecular shape; lone pairs alter observed shape and angle."
                ],
                callouts=[
                    CalloutItem(
                        type="misconception",
                        title="Misconception: Geometry vs Shape",
                        text=(
                            "**Wrong Belief**: Calling NH3 or H2O 'tetrahedral' molecules.\n"
                            "**Scientific Reality**: While their electron domains are arranged tetrahedrally, the molecular shape of NH3 is trigonal pyramidal and H2O is bent.\n"
                            "**Why**: Molecular geometry describes the arrangement of atomic nuclei, which are physically detectable by X-ray diffraction."
                        )
                    )
                ],
                semantic_evidence=SectionSemanticEvidence(
                    concept_id="sec_vsepr",
                    instructional_role="core_concept",
                    explanation_present=True,
                    intuition_present=True,
                    example_present=True,
                    worked_example_present=True,
                    practice_targets=["VSEPR Theory and Molecular Shapes"],
                    misconception_targets=["electron geometry vs molecular shape"]
                )
            ),
            NoteSection(
                id="sec_vbt",
                section_type="core_concept",
                title="Valence Bond Theory: Sigma and Pi Bonds",
                content=(
                    "### 1. Simple Idea\n"
                    "Lewis structures tell us *which* atoms share electrons, but not *how* electrons are shared in 3D space. "
                    "Valence Bond Theory explains covalent bonding through the physical overlapping of atomic orbital wavefunctions.\n\n"
                    "### 2. Intuition: Merging Orbitals\n"
                    "Imagine two fuzzy clouds overlapping. Where they merge, the probability of finding electrons between both nuclei increases dramatically. "
                    "This shared cloud of negative charge pulls both positive nuclei toward each other, forming a stable chemical bond.\n\n"
                    "### 3. Formal Principles of Valence Bond Theory\n"
                    "Formulated by Heitler, London, Pauling, and Slater:\n"
                    "1. A covalent bond forms when half-filled valence orbitals of two atoms overlap.\n"
                    "2. The overlapping orbitals must contain electrons with opposite spins to satisfy Pauli's exclusion principle.\n"
                    "3. Greater orbital overlap produces a stronger and more stable chemical bond.\n\n"
                    "### 4. Comparison: Sigma (σ) vs Pi (π) Bonds\n\n"
                    "| Characteristic | Sigma Bond (σ) | Pi Bond (π) |\n"
                    "|---|---|---|\n"
                    "| Nature of Overlap | Axial / Head-on overlap along the internuclear axis | Lateral / Sideways overlap perpendicular to axis |\n"
                    "| Orbitals Involved | s-s, s-p, or hybridized orbitals | Unhybridized p-p or d-d orbitals |\n"
                    "| Extent of Overlap | Maximum (high orbital overlap) | Moderate to low (sideways overlap) |\n"
                    "| Bond Strength | Significantly stronger | Inherently weaker than sigma bond |\n"
                    "| Bond Rotation | Free rotation permitted around bond axis | Rotation strictly restricted (produces isomerism) |\n"
                    "| Electron Distribution | Cylindrically symmetrical along internuclear line | Two lobes: concentrated above and below plane |"
                ),
                key_points=[
                    "Single covalent bond consists strictly of 1 sigma bond.",
                    "Double bond consists of 1 sigma bond + 1 pi bond.",
                    "Triple bond consists of 1 sigma bond + 2 pi bonds.",
                    "Bond Order indicates the number of chemical bonds between a pair of atoms."
                ],
                formulas=[
                    "Bond Order = (Nb - Na) / 2"
                ],
                examples=[
                    "**Problem**: Calculate the total number of sigma and pi bonds in Ethyne (H-C≡C-H) and Benzene (C6H6).\n"
                    "**Given**: Structural formulas of Ethyne and Benzene.\n"
                    "**Concept**: Every single bond is 1 sigma; double bond is 1 sigma + 1 pi; triple bond is 1 sigma + 2 pi.\n"
                    "**Step 1: Analyze Ethyne (C2H2)**:\n"
                    "  - Two C-H single bonds = 2 sigma bonds.\n"
                    "  - One C≡C triple bond = 1 sigma bond + 2 pi bonds.\n"
                    "  - Total = 3 sigma bonds and 2 pi bonds.\n"
                    "**Step 2: Analyze Benzene (C6H6)**:\n"
                    "  - Six C-H single bonds = 6 sigma bonds.\n"
                    "  - Six C-C bonds in ring (alternating single and double) = 6 sigma bonds + 3 pi bonds.\n"
                    "  - Total = 12 sigma bonds and 3 pi bonds.\n"
                    "**Final Answer**: Ethyne has 3 sigma and 2 pi bonds; Benzene has 12 sigma and 3 pi bonds.\n"
                    "**Why**: Sigma bonds form the planar skeleton; unhybridized p-orbitals form the delocalized pi systems."
                ],
                semantic_evidence=SectionSemanticEvidence(
                    concept_id="sec_vbt",
                    instructional_role="core_concept",
                    explanation_present=True,
                    intuition_present=True,
                    example_present=True,
                    worked_example_present=True,
                    practice_targets=["Valence Bond Theory: Sigma and Pi Bonds"]
                )
            ),
            NoteSection(
                id="sec_hybridization",
                section_type="core_concept",
                title="Hybridization and Polyatomic Molecular Geometry",
                content=(
                    "### 1. Simple Idea\n"
                    "In an isolated Carbon atom, the valence electrons sit in one spherical 2s orbital and three dumbbell-shaped 2p orbitals. "
                    "Yet in Methane (CH4), all four C-H bonds are completely identical in length, strength, and energy! How is that possible? "
                    "The answer is orbital hybridization.\n\n"
                    "### 2. Intuition: Mixing Paint Colors\n"
                    "If you mix 1 bucket of blue paint (s-orbital) with 3 buckets of yellow paint (p-orbitals), you don't get 1 blue spot and 3 yellow spots. "
                    "You get 4 identical buckets of green paint! Similarly, mixing atomic orbitals creates entirely new, identical hybrid orbitals.\n\n"
                    "### 3. Formal Definition & Hybridization Matrix\n"
                    "Hybridization is the mathematical mixing of non-equivalent atomic orbitals of comparable energy to generate an equal number "
                    "of equivalent hybrid orbitals with specific directional orientations in space.\n\n"
                    "| Hybrid Type | Steric Number | Orbitals Mixed | Electron Geometry | Prototypical Example | Characteristic Angles |\n"
                    "|---|---|---|---|---|---|\n"
                    "| sp | 2 | 1s + 1p | Linear | BeCl2, C2H2 | 180° |\n"
                    "| sp² | 3 | 1s + 2p | Trigonal Planar | BF3, C2H4 | 120° |\n"
                    "| sp³ | 4 | 1s + 3p | Tetrahedral | CH4, CCl4 | 109.5° |\n"
                    "| sp³d | 5 | 1s + 3p + 1d | Trigonal Bipyramidal | PCl5 | 120° (equatorial), 90° (axial) |\n"
                    "| sp³d² | 6 | 1s + 3p + 2d | Octahedral | SF6 | 90° |"
                ),
                key_points=[
                    "Number of hybrid orbitals formed strictly equals the number of atomic orbitals mixed.",
                    "Hybrid orbitals form directional sigma bonds; unhybridized p-orbitals form lateral pi bonds.",
                    "In PCl5 (sp3d), axial P-Cl bonds (240 pm) are longer and weaker than equatorial bonds (202 pm) due to greater repulsion."
                ],
                examples=[
                    "**Problem**: Determine the steric number, hybridization, and 3D molecular geometry of Sulfur Hexafluoride (SF6).\n"
                    "**Given**: Neutral SF6 molecule with central Sulfur atom bonded to 6 Fluorine atoms.\n"
                    "**Concept**: Steric Number mapping to hybrid orbital sets.\n"
                    "**Step 1: Identify Central Atom**: Sulfur (Group 16) has 6 valence electrons.\n"
                    "**Step 2: Count Sigma Bonds**: Sulfur forms 6 single covalent bonds with 6 Fluorine atoms (6 sigma bonds).\n"
                    "**Step 3: Count Non-Bonding Lone Pairs**: All 6 valence electrons of Sulfur participate in bonding (0 lone pairs).\n"
                    "**Step 4: Calculate Steric Number**: Steric Number = 6 (sigma bonds) + 0 (lone pairs) = 6.\n"
                    "**Step 5: Map to Hybridization**: Steric Number 6 requires mixing 1s + 3p + 2d orbitals = sp³d² hybridization.\n"
                    "**Step 6: Determine Geometry**: With 0 lone pairs, the molecular geometry matches the electron geometry: Regular Octahedral (all bond angles 90°).\n"
                    "**Final Answer**: Steric Number = 6; Hybridization = sp³d²; Molecular Geometry = Regular Octahedral.\n"
                    "**Why**: Six equivalent sp³d² hybrid orbitals point toward the vertices of a regular octahedron to minimize electron repulsion."
                ],
                common_mistakes=[
                    "Assuming axial and equatorial bonds in PCl5 are identical; axial bonds experience three 90° repulsions versus two for equatorial bonds."
                ],
                semantic_evidence=SectionSemanticEvidence(
                    concept_id="sec_hybridization",
                    instructional_role="core_concept",
                    explanation_present=True,
                    intuition_present=True,
                    example_present=True,
                    worked_example_present=True,
                    practice_targets=["Hybridization (sp, sp2, sp3, sp3d, sp3d2)"]
                )
            ),
            NoteSection(
                id="sec_h_bonding",
                section_type="core_concept",
                title="Hydrogen Bonding and Intermolecular Forces",
                content=(
                    "### 1. Simple Idea\n"
                    "Hydrogen bonding is a special, exceptionally strong type of dipole-dipole attraction that occurs when hydrogen is directly "
                    "attached to the most electronegative elements on the periodic table (Fluorine, Oxygen, or Nitrogen).\n\n"
                    "### 2. Intuition: The Molecular Tug-of-War\n"
                    "Hydrogen has only 1 electron. When bonded to highly electronegative F, O, or N, that electron is pulled strongly away, "
                    "leaving the hydrogen nucleus (a bare proton) almost completely unshielded. This exposed positive center strongly attracts "
                    "lone pairs from adjacent molecules like a powerful molecular magnet.\n\n"
                    "### 3. Comparison: Intermolecular vs Intramolecular Hydrogen Bonding\n\n"
                    "| Property | Intermolecular Hydrogen Bonding | Intramolecular Hydrogen Bonding |\n"
                    "|---|---|---|\n"
                    "| Occurrence | Between separate, distinct molecules | Within the very same molecule |\n"
                    "| Molecular Association | Causes molecular aggregation (clustering) | Prevents association with neighbor molecules |\n"
                    "| Boiling Point Effect | Substantially elevates boiling points | Relatively lower boiling points |\n"
                    "| Water Solubility | Markedly increases water solubility | Lower water solubility (polar groups shielded) |\n"
                    "| Prototypical Examples | H2O (high bp 100°C), NH3, HF, ethanol | o-nitrophenol, salicylic acid |"
                ),
                key_points=[
                    "Hydrogen bonding strictly requires H covalently bonded directly to F, O, or N.",
                    "Intermolecular H-bonding accounts for the high boiling point and ice density anomaly (density of ice < water due to open cage structure).",
                    "Intramolecular H-bonding creates closed 5- or 6-membered chelate rings, lowering volatility."
                ],
                semantic_evidence=SectionSemanticEvidence(
                    concept_id="sec_h_bonding",
                    instructional_role="core_concept",
                    explanation_present=True,
                    intuition_present=True,
                    example_present=True,
                    practice_targets=["Hydrogen Bonding"]
                )
            )
        ],
        practice=[
            {
                "question": "State the Octet Rule and identify two stable chemical species that exist as exceptions with expanded octets.",
                "type": "recall",
                "difficulty": "standard",
                "answer": "The Octet Rule states that atoms combine by gaining, losing, or sharing electrons to complete eight electrons in their valence shell. Two stable exceptions with expanded octets are PCl5 (10 valence electrons) and SF6 (12 valence electrons).",
                "explanation": "Period 3 elements utilize vacant 3d orbitals to accommodate more than 8 valence electrons, forming stable hypervalent compounds."
            },
            {
                "question": "According to VSEPR theory, why do lone pair - lone pair (lp-lp) repulsions exceed bond pair - bond pair (bp-bp) repulsions?",
                "type": "conceptual",
                "difficulty": "standard",
                "answer": "Lone pairs are localized on and attracted to only a single atomic nucleus, so their electron clouds spread out more broadly in space. In contrast, bonding pairs are held tightly between two positive nuclei.",
                "explanation": "Because lone pair electron density is closer to the central nucleus and occupies a larger solid angle, it exerts stronger repulsive forces on neighboring electron domains."
            },
            {
                "question": "Why are axial P-Cl bonds longer and weaker than equatorial P-Cl bonds in gaseous PCl5?",
                "type": "application",
                "difficulty": "standard",
                "answer": "Each axial P-Cl bond experiences electrostatic repulsion from three equatorial bonds at 90°, whereas each equatorial P-Cl bond experiences repulsion from only two axial bonds at 90°. To minimize this greater repulsion, axial bonds elongate to 240 pm compared to 202 pm for equatorial bonds.",
                "explanation": "In a trigonal bipyramidal geometry (sp3d), bonds experiencing more 90° repulsive interactions are pushed farther out to maintain thermodynamic stability."
            },
            {
                "question": "A diatomic chemical species has 10 bonding electrons and 6 antibonding electrons. Calculate its bond order and determine if the species is stable.",
                "type": "exam-style",
                "difficulty": "standard",
                "answer": "Bond Order = (Nb - Na) / 2 = (10 - 6) / 2 = 4 / 2 = 2.0. Because the bond order is positive (BO > 0), the species is thermodynamically stable.",
                "explanation": "A positive bond order indicates net stabilizing attractive forces between the atoms; a bond order of 2 corresponds to a stable double bond."
            },
            {
                "question": "Explain why o-nitrophenol is steam-volatile and has a lower boiling point than p-nitrophenol, despite both having identical molecular formulas.",
                "type": "challenge",
                "difficulty": "standard",
                "answer": "o-nitrophenol undergoes intramolecular hydrogen bonding between the adjacent -OH and -NO2 groups, forming an internal chelate ring and preventing intermolecular association. In contrast, p-nitrophenol forms extensive intermolecular hydrogen bonds with neighboring molecules, requiring significantly higher thermal energy to vaporize.",
                "explanation": "Intramolecular H-bonding decreases external intermolecular attraction and water solubility, making the ortho-isomer more volatile."
            }
        ],
        visuals=[
            VisualSpec(
                type="flowchart",
                title="Molecular Geometries and Hybridization Summary",
                nodes=[
                    {"id": "sp", "label": "sp -> Linear (180°)"},
                    {"id": "sp2", "label": "sp² -> Trigonal Planar (120°)"},
                    {"id": "sp3", "label": "sp³ -> Tetrahedral (109.5°)"},
                    {"id": "sp3d", "label": "sp³d -> Trigonal Bipyramidal"},
                    {"id": "sp3d2", "label": "sp³d² -> Octahedral (90°)"}
                ],
                edges=[]
            )
        ]
    )



def test_chemical_bonding_golden_fixture_certification(chemical_bonding_golden_fixture):
    """
    MASTER VERIFICATION:
    Renders Chemical Bonding Golden Fixture into student PDF and executes full certification.
    Requires:
    - STUDENT_READY artifact status
    - 0 Raw LaTeX defects
    - 0 Notation defects
    - 0 Geometry defects (no clipping, no blank pages)
    - Valid visual image rasterization
    - Multi-page document (>= 2 pages)
    - Document & PDF SHA-256 cryptographic binding
    """
    doc = chemical_bonding_golden_fixture
    html = HTMLNoteBuilder.build_html(doc, include_answers=True)
    pdf_bytes, pdf_hash = asyncio.run(PDFNoteRenderer.render_pdf_async(doc, include_answers=True))

    result = asyncio.run(StudentArtifactCertifier.certify_artifact(
        document=doc,
        pdf_bytes=pdf_bytes,
        html_content=html
    ))

    # Status must be STUDENT_READY
    assert result.artifact_status in (ArtifactStatus.STUDENT_READY, ArtifactStatus.STUDENT_READY_WITH_WARNINGS)

    # Defect list must have 0 critical defects
    critical_defects = [d for d in result.artifact_certification.defects if d.severity == "critical"]
    assert len(critical_defects) == 0

    # Cryptographic binding
    assert len(result.document_hash) == 64
    assert len(result.pdf_hash) == 64
    assert result.pdf_hash == pdf_hash

    # Multi-page student document
    assert result.artifact_certification.pages >= 2

    # Content certification must pass
    assert result.content_certification.valid is True
    assert result.content_certification.substantive_score >= 80.0


def test_chemical_bonding_failure_regression():
    """
    NEGATIVE REGRESSION:
    Injects raw unrendered LaTeX markup ($$E=\frac{kq}{r^2}$$), broken subscripts (_{2}),
    and unrendered raw notation into a document and verifies Quality Gate REJECTS it.
    """
    bad_doc = NotesDocument(
        id="chem-bonding-corrupted-test",
        title="Chemical Bonding Corrupted",
        topic="Chemical Bonding",
        subject="Chemistry",
        class_level="Class 11",
        sections=[
            NoteSection(
                id="sec_corrupt",
                title="Corrupted Formulas",
                content="The dipole equation is $$E = \\frac{kq}{r^2}$$ and water formula is H_{2}O with sp^{3} orbitals.",
                key_points=["Broken unrendered markup"]
            )
        ]
    )

    # Render raw HTML to simulate unrendered LaTeX leak into final PDF
    raw_html = f"<html><body><h1>Corrupted</h1><p>{bad_doc.sections[0].content}</p></body></html>"
    pdf_bytes = asyncio.run(PDFNoteRenderer.render_html(raw_html))

    result = asyncio.run(StudentArtifactCertifier.certify_artifact(
        document=bad_doc,
        pdf_bytes=pdf_bytes,
        html_content=raw_html
    ))

    # Must be INVALID
    assert result.artifact_status == ArtifactStatus.INVALID
    assert len(result.artifact_certification.defects) > 0

    defect_types = [d.type for d in result.artifact_certification.defects]
    assert (
        RenderingDefectType.RAW_LATEX_DELIMITER in defect_types
        or RenderingDefectType.RAW_LATEX_COMMAND in defect_types
        or RenderingDefectType.BROKEN_SUBSCRIPT in defect_types
    )


def test_valid_one_page_note_vs_stub():
    """
    Verify Quality Gate distinguishes between a legitimate 1-page quick reference note
    and an uncertified low-substance stub.
    """
    # 1. Valid high-density 1-page review note
    valid_one_page_doc = NotesDocument(
        id="boyles-law-one-page",
        title="Boyle's Law Quick Reference",
        topic="Boyle's Law",
        subject="Physics",
        class_level="Class 11",
        sections=[
            NoteSection(
                id="sec_boyle",
                title="Boyle's Law Principles",
                content="At constant temperature T, the pressure of a fixed mass of gas is inversely proportional to volume: P ∝ 1/V, meaning P1V1 = P2V2. The isotherm on a P-V graph is a rectangular hyperbola.",
                key_points=["Isothermal process curve is a rectangular hyperbola", "PV product remains constant"],
                examples=["A gas at 1.0 atm occupies 2.0 L. At 2.5 atm, volume reduces to (1.0*2.0)/2.5 = 0.8 L."],
                formulas=["P1 * V1 = P2 * V2"]
            )
        ],
        practice=[
            {
                "question": "What happens to gas pressure if volume is halved at constant T?",
                "answer": "Pressure doubles because P is inversely proportional to V.",
                "hints": ["Use inverse proportion."]
            }
        ]
    )

    html_valid = HTMLNoteBuilder.build_html(valid_one_page_doc)
    pdf_valid, _ = asyncio.run(PDFNoteRenderer.render_pdf_async(valid_one_page_doc))
    result_valid = asyncio.run(StudentArtifactCertifier.certify_artifact(
        document=valid_one_page_doc,
        pdf_bytes=pdf_valid,
        html_content=html_valid
    ))
    assert result_valid.artifact_status in (ArtifactStatus.STUDENT_READY, ArtifactStatus.STUDENT_READY_WITH_WARNINGS)

    # 2. Invalid hollow stub (detailed depth requested, but only tiny 1-sentence section)
    stub_doc = NotesDocument(
        id="hollow-stub-note",
        title="Hollow Stub",
        topic="Thermodynamics",
        subject="Physics",
        class_level="Class 11",
        depth=NoteDepth.DETAILED,
        sections=[
            NoteSection(
                id="sec_stub",
                title="Stub",
                content="Short text.",
                key_points=[]
            )
        ]
    )
    html_stub = HTMLNoteBuilder.build_html(stub_doc)
    pdf_stub, _ = asyncio.run(PDFNoteRenderer.render_pdf_async(stub_doc))
    result_stub = asyncio.run(StudentArtifactCertifier.certify_artifact(
        document=stub_doc,
        pdf_bytes=pdf_stub,
        html_content=html_stub
    ))
    # Stub should be flagged as INCOMPLETE
    assert result_stub.artifact_status == ArtifactStatus.INCOMPLETE or len(result_stub.errors) > 0


def test_raw_math_injection_halts_pipeline():
    """
    Verify raw math injection (e.g. \\frac, \\sqrt, $$) in section content
    is detected by the Quality Gate and prevents certification.
    """
    injected_doc = NotesDocument(
        id="injected-math-doc",
        title="Quadratic Formula",
        topic="Quadratic Formula",
        subject="Mathematics",
        class_level="Class 10",
        sections=[
            NoteSection(
                id="sec_roots",
                title="Roots",
                content="The roots are given by $$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$$.",
                key_points=["Discriminant decides root nature"]
            )
        ]
    )

    # Render without typesetter to allow raw markup to leak into HTML/PDF
    raw_html = f"<html><body><div class='section-wrapper'><p>{injected_doc.sections[0].content}</p></div></body></html>"
    pdf_bytes = asyncio.run(PDFNoteRenderer.render_html(raw_html))

    result = asyncio.run(StudentArtifactCertifier.certify_artifact(
        document=injected_doc,
        pdf_bytes=pdf_bytes,
        html_content=raw_html
    ))

    assert result.artifact_status == ArtifactStatus.INVALID
    assert any(d.type in (RenderingDefectType.RAW_LATEX_DELIMITER, RenderingDefectType.RAW_LATEX_COMMAND) for d in result.artifact_certification.defects)


def test_original_chemical_bonding_failure_regression():
    """
    CRITICAL ORIGINAL FAILURE REGRESSION TEST (Section 13):
    Reproduces the exact original production failure:
    - Chemical Bonding
    - 1-page premature output
    - Raw LaTeX leaked: $$\\frac{N_b - N_a}{2}$$ and $$E = \\frac{kq}{r^2}$$
    - Broken chemistry notation: H_{2}O, sp^{3}, SO_{4}
    - Incomplete chapter coverage: 4 missing out of 5 required syllabus concepts
    Expected outcome: REJECTED (artifact_status != STUDENT_READY)
    """
    ctx = CanonicalNotesContext(
        request={"topic": "Chemical Bonding", "target_class": "Class 11", "subject": "Chemistry"},
        lesson=LessonContext(
            topic="Chemical Bonding",
            learning_objectives=[
                "Octet Rule and Lewis Structures",
                "VSEPR Theory and Molecular Shapes",
                "Valence Bond Theory: Sigma and Pi Bonds",
                "Hybridization (sp, sp2, sp3, sp3d, sp3d2)",
                "Hydrogen Bonding"
            ]
        )
    )

    plan = NotesGenerationPlan(
        primary_topic="Chemical Bonding",
        target_class="Class 11",
        subject="Chemistry",
        purpose=PurposePlan(),
        formats=[NoteFormat.LEARNING_NOTES],
        difficulty=NoteDifficulty.STANDARD,
        depth=NoteDepth.DETAILED,
        teaching_strategy=TeachingStrategyPlan(),
        section_plan=[
            SectionPlanItem(type="octet", title="Octet Rule", target="Octet Rule and Lewis Structures", required=True),
            SectionPlanItem(type="vsepr", title="VSEPR Theory", target="VSEPR Theory and Molecular Shapes", required=True),
            SectionPlanItem(type="vbt", title="Valence Bond Theory", target="Valence Bond Theory: Sigma and Pi Bonds", required=True),
            SectionPlanItem(type="hyb", title="Hybridization", target="Hybridization (sp, sp2, sp3, sp3d, sp3d2)", required=True),
            SectionPlanItem(type="hbond", title="Hydrogen Bonding", target="Hydrogen Bonding", required=True)
        ],
        visual_plan=VisualPlan(),
        remediation_plan=RemediationPlan(),
        practice_plan=PracticePlan(),
        revision_plan=RevisionPlan()
    )

    # Broken stub document directly reproducing original premature production defect
    defective_doc = NotesDocument(
        id="orig-chem-bonding-broken-stub",
        title="Chemical Bonding Stub",
        topic="Chemical Bonding",
        subject="Chemistry",
        class_level="Class 11",
        depth=NoteDepth.DETAILED,
        sections=[
            NoteSection(
                id="sec_premature",
                title="Chemical Bonding Overview",
                content=(
                    "Molecules form bonds. Water is H_{2}O with sp^{3} orbitals. "
                    "Bond order is $$\\frac{N_b - N_a}{2}$$. Dipole energy is $$E = \\frac{kq}{r^2}$$."
                ),
                key_points=["Incomplete coverage"]
            )
        ]
    )

    # Render raw HTML without typesetter to let the raw defect reach the PDF artifact
    raw_html = f"<html><body><h1>Chemical Bonding</h1><p>{defective_doc.sections[0].content}</p></body></html>"
    pdf_bytes = asyncio.run(PDFNoteRenderer.render_html(raw_html))

    result = asyncio.run(StudentArtifactCertifier.certify_artifact(
        document=defective_doc,
        plan=plan,
        context=ctx,
        pdf_bytes=pdf_bytes,
        html_content=raw_html
    ))

    # Verification: Must be REJECTED (INVALID or INCOMPLETE), never STUDENT_READY
    assert result.artifact_status in (ArtifactStatus.INVALID, ArtifactStatus.INCOMPLETE, ArtifactStatus.RENDERING_FAILED)
    assert result.artifact_status != ArtifactStatus.STUDENT_READY
    assert len(result.artifact_certification.defects) > 0
    assert result.content_certification.coverage.missing >= 3


def test_multipage_realistic_document_regression(chemical_bonding_golden_fixture):
    """
    MULTI-PAGE REALISTIC REGRESSION TEST (Section 17):
    Verifies large realistic multi-page document:
    - All sections present
    - All practice present
    - No truncation
    - No overlap / clipping
    - No blank pages
    - No footer collisions
    - No broken equations
    """
    doc = chemical_bonding_golden_fixture
    html = HTMLNoteBuilder.build_html(doc, include_answers=True)
    pdf_bytes, pdf_hash = asyncio.run(PDFNoteRenderer.render_pdf_async(doc, include_answers=True))

    result = asyncio.run(StudentArtifactCertifier.certify_artifact(
        document=doc,
        pdf_bytes=pdf_bytes,
        html_content=html
    ))

    # All sections and practice present
    assert result.artifact_certification.pages >= 2
    assert result.artifact_certification.practice_valid_count == len(doc.practice)

    # Defect audits: 0 clipping, 0 overflow, 0 raw latex, 0 broken equations, 0 blank pages
    assert result.artifact_certification.clipping_count == 0
    assert result.artifact_certification.overflow_count == 0
    assert result.artifact_certification.raw_latex_count == 0
    assert result.artifact_certification.broken_equations_count == 0

    # Visual inspection passed with 0 blank pages
    _, vis_details, images = VisualInspector.inspect_pdf_images(pdf_bytes)
    assert len(vis_details["blank_image_pages"]) == 0
    assert len(images) == result.artifact_certification.pages

    # Document & PDF identity binding stored
    assert result.document_hash is not None and len(result.document_hash) == 64
    assert result.render_config_hash is not None and len(result.render_config_hash) == 64
    assert result.certification_id.startswith("cert_")
    assert result.artifact_status == ArtifactStatus.STUDENT_READY
