"""
Test Suite: Student Artifact Rendering Engine
=============================================
Tests SemanticTypesetter, HTMLNoteBuilder, and PDFNoteRenderer.
Verifies:
- Chemistry formatting (H2O, NH3, SO4^2-, Na+, Cl-, SF6, sp2, sp3, sp3d, sp3d2, sigma, pi)
- Mathematical typesetting (fractions, roots, superscripts, subscripts)
- HTML layout wrappers (.section-wrapper, .example-wrapper, .callout-wrapper, etc.)
- Locked A4 print CSS rules
- Playwright Chromium PDF generation and SHA-256 hash binding
"""
import asyncio
import pytest
from app.services.notes.schemas import (
    NotesDocument, NoteSection, VisualSpec, CalloutItem
)
from app.services.notes.rendering.typesetter import SemanticTypesetter
from app.services.notes.rendering.html_builder import HTMLNoteBuilder
from app.services.notes.rendering.pdf_renderer import PDFNoteRenderer, PDFRenderer


def test_chemistry_typesetting_formulas():
    """Verify chemical formulas are converted to formatted subscripts/superscripts."""
    text = "Water is H2O and ammonia is NH3. Sulfate ion is SO4^2- while sodium is Na+ and chloride is Cl-."
    typeset = SemanticTypesetter.typeset_chemistry(text)
    
    assert ("H₂O" in typeset or "H<sub>2</sub>O" in typeset)
    assert ("NH₃" in typeset or "NH<sub>3</sub>" in typeset)
    assert ("SO₄" in typeset or "SO<sub>4</sub>" in typeset)
    assert ("Na⁺" in typeset or "Na<sup>+</sup>" in typeset)
    assert ("Cl⁻" in typeset or "Cl<sup>−</sup>" in typeset or "Cl<sup>-</sup>" in typeset)
    assert "H2O " not in typeset
    assert "NH3." not in typeset


def test_chemistry_typesetting_hybridization_and_bonds():
    """Verify hybridization states and sigma/pi bonds are properly typeset."""
    text = "Methane has sp3 hybridization. Ethene has sp2 hybridization and contains 5 sigma bonds and 1 pi bond."
    typeset = SemanticTypesetter.typeset_chemistry(text)
    
    assert ("sp³" in typeset or "sp<sup>3</sup>" in typeset)
    assert ("sp²" in typeset or "sp<sup>2</sup>" in typeset)
    assert "σ bonds" in typeset
    assert "π bond" in typeset
    assert "sp3 hybridization" not in typeset
    assert "sp2 hybridization" not in typeset


def test_chemistry_complex_molecules():
    """Verify SF6, PCl5, and sp3d, sp3d2 states."""
    text = "SF6 has sp3d2 hybridization and PCl5 has sp3d hybridization with axial and equatorial bonds."
    typeset = SemanticTypesetter.typeset_chemistry(text)
    
    assert ("SF₆" in typeset or "SF<sub>6</sub>" in typeset)
    assert ("PCl₅" in typeset or "PCl<sub>5</sub>" in typeset)
    assert ("sp³d²" in typeset or "sp<sup>3</sup>d<sup>2</sup>" in typeset)
    assert ("sp³d" in typeset or "sp<sup>3</sup>d" in typeset)


def test_math_typesetting_fractions_and_greek():
    """Verify LaTeX math expressions are converted without raw $ delimiters."""
    math_text = "The kinetic energy is $E = \\frac{1}{2}mv^2$ and wavelength is $\\lambda = \\frac{h}{p}$."
    typeset = SemanticTypesetter.typeset_markdown(math_text)
    
    assert "$" not in typeset
    assert "\\frac" not in typeset
    assert ("mv²" in typeset or "<sup>2</sup>" in typeset)
    assert ("λ" in typeset or "\\lambda" not in typeset)


def test_html_builder_structural_wrappers():
    """Verify HTMLNoteBuilder wraps sections and pedagogical elements in protective print containers."""
    doc = NotesDocument(
        id="doc_chem_rendering_1",
        title="Chemical Bonding & Molecular Structure",
        topic="Chemical Bonding",
        subject="Chemistry",
        class_level="Class 11",
        curriculum="CBSE",
        sections=[
            NoteSection(
                id="sec_1",
                title="Hybridization and Molecular Geometry",
                content="sp3 hybridization in methane CH4 gives a tetrahedral shape with 109.5° bond angle.",
                key_points=["4 hybrid orbitals directed to tetrahedral corners", "Equal bond lengths and energies"],
                examples=["SF6 molecule exhibits sp3d2 hybridization with regular octahedral geometry and 90° bond angles."],
                formulas=["Formal Charge = V - N - (1/2)B"],
                common_mistakes=["Confusing molecular geometry with electron geometry when lone pairs are present"],
                callouts=[CalloutItem(type="tip", title="Exam Alert", text="SF6 has zero lone pairs and symmetric 90° angles.")]
            )
        ],
        practice=[
            {
                "question": "Predict the shape and bond angle of NH3 using VSEPR theory.",
                "answer": "Trigonal pyramidal, approximately 107° due to lone pair-bond pair repulsion.",
                "hints": ["Nitrogen has 5 valence electrons and 3 bond pairs."]
            }
        ],
        visuals=[
            VisualSpec(
                type="flowchart",
                title="VSEPR Molecular Shapes Summary",
                nodes=[{"id": "1", "label": "Steric No 4"}],
                edges=[]
            )
        ]
    )

    html = HTMLNoteBuilder.build_html(doc, include_answers=True)

    # Check structural CSS print classes
    assert "section-wrapper" in html
    assert "example-wrapper" in html
    assert "practice-wrapper" in html
    assert "callout-wrapper" in html
    assert "key-points-box" in html

    # Check print media CSS
    assert "@media print" in html
    assert "break-inside: avoid" in html
    assert "A4 portrait" in html

    # Check typeset content inside HTML
    assert ("CH₄" in html or "CH<sub>4</sub>" in html)
    assert ("sp³" in html or "sp<sup>3</sup>" in html)
    assert ("SF₆" in html or "SF<sub>6</sub>" in html)
    assert ("sp³d²" in html or "sp<sup>3</sup>d<sup>2</sup>" in html)
    assert ("NH₃" in html or "NH<sub>3</sub>" in html)


def test_pdf_renderer_generates_valid_pdf():
    """Verify PDFNoteRenderer generates valid, non-empty PDF bytes with SHA-256 hash."""
    doc = NotesDocument(
        id="doc_periodic_trends",
        title="Periodic Classification of Elements",
        topic="Periodic Trends",
        subject="Chemistry",
        class_level="Class 11",
        curriculum="CBSE",
        sections=[
            NoteSection(
                id="sec_trends",
                title="Periodic Trends in Physical Properties",
                content="Atomic radius decreases along a period due to increased effective nuclear charge.",
                key_points=["Atomic radii decrease across periods", "Electronegativity increases across periods"]
            )
        ],
        practice=[
            {
                "question": "Why is cation smaller than its parent atom?",
                "answer": "Loss of electrons increases effective nuclear charge per remaining electron.",
                "hints": ["Consider nuclear charge pulling fewer electrons."]
            }
        ]
    )

    pdf_bytes, pdf_hash = asyncio.run(PDFNoteRenderer.render_pdf_async(doc))

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_hash) == 64


def test_adversarial_typesetter_strings():
    """
    Verify strict context-awareness in SemanticTypesetter:
    - English words remain English (overlapping, spins, pin)
    - Chemical bonds are preserved without false ion conversion (P-Cl, C-Cl)
    - Free ions are properly formatted (Na+, Cl-)
    - Chemical bonds sigma/pi are typeset without leaking backslashes
    - Non-chemistry names (Raspberry Pi, Six Sigma) are never corrupted
    """
    adversarial_cases = [
        ("overlapping atoms", "overlapping atoms"),
        ("spins of electrons", "spins of electrons"),
        ("Na is sodium metal", "Na is sodium metal"),
        ("N_a is an antibonding variable", "N<sub>a</sub> is an antibonding variable"),
        ("P-Cl bond is covalent", "P-Cl bond is covalent"),
        ("P-Cl - axial bond length is 240 pm", "P-Cl - axial bond length is 240 pm"),
        ("Cl- ion in aqueous solution", "Cl<sup>−</sup> ion in aqueous solution"),
        ("Cl^- is a chloride ion", "Cl<sup>−</sup> is a chloride ion"),
        ("Na+ ion attracts Cl- ion", "Na<sup>+</sup> ion attracts Cl<sup>−</sup> ion"),
        ("pi bond is formed by lateral overlap", "π bond is formed by lateral overlap"),
        ("pi bonds in ethyne", "π bonds in ethyne"),
        (r"\pi bond", "π bond"),
        ("sigma bond is formed by axial overlap", "σ bond is formed by axial overlap"),
        ("sigma bonds in methane", "σ bonds in methane"),
        (r"\sigma bond", "σ bond"),
        ("Raspberry Pi is a single-board computer", "Raspberry Pi is a single-board computer"),
        ("Six Sigma methodology", "Six Sigma methodology"),
    ]

    for raw_input, expected in adversarial_cases:
        actual = SemanticTypesetter.typeset_markdown(raw_input)
        assert actual == expected, f"Failed for input '{raw_input}': expected '{expected}', got '{actual}'"


def test_mathematics_bond_order_fraction_equation():
    """Verify equations like Bond Order = (N_b - N_a) / 2 render as proper fractions."""
    eq_text = "Bond Order = (N_b - N_a) / 2"
    actual = SemanticTypesetter.typeset_markdown(eq_text)
    assert '<span class="fraction">' in actual
    assert '<span class="num">N<sub>b</sub> − N<sub>a</sub></span>' in actual
    assert '<span class="den">2</span>' in actual
    assert "Na⁺" not in actual  # Never false ion conversion


def test_latex_environments_and_unbracketed_frac():
    """Verify LaTeX math environments are unwrapped and currency amounts are not swallowed."""
    env_math = r"$$\begin{aligned} x &= 1 \\ y &= 2 \end{aligned}$$"
    actual_env = SemanticTypesetter.typeset_markdown(env_math)
    assert "{aligned}" not in actual_env
    assert "\\\\" not in actual_env
    assert "&" not in actual_env
    assert "<br>" in actual_env

    # Currency protection
    currency_text = "The cost is $50 and the discount is $20."
    actual_currency = SemanticTypesetter.typeset_markdown(currency_text)
    assert actual_currency == "The cost is $50 and the discount is $20."

    # Unbracketed frac in prose
    prose_frac = r"The formula is \frac{N_b - N_a}{2}."
    actual_prose = SemanticTypesetter.typeset_markdown(prose_frac)
    assert '<span class="fraction">' in actual_prose
    assert "N<sub>b</sub>" in actual_prose
    assert "N<sub>a</sub>" in actual_prose
    assert "\\frac" not in actual_prose

    # Complex nested fraction with square root
    quad_math = r"The roots are $x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$."
    actual_quad = SemanticTypesetter.typeset_markdown(quad_math)
    assert '<span class="fraction">' in actual_quad
    assert '±' in actual_quad
    assert '√<span class="radicand">b<sup>2</sup> - 4ac</span>' in actual_quad
    assert '$' not in actual_quad
    assert '{2a}' not in actual_quad

