"""
TeachGenie Notes Generation Engine — Authoritative Curriculum Catalog
======================================================================
Provides authentic, syllabus-grounded, multi-subject pedagogical content
for standard curricular topics (Chemistry, Physics, Mathematics, Biology, Computer Science).
Ensures production generation produces publication-grade, student-ready notes
with layered teaching, procedural worked examples, comparison matrices, and progressive practice.

Architecture:
- CurriculumCatalog is an OPTIONAL curated curriculum/source registry.
- Provides pre-curated curriculum packs (Chemical Bonding, Newton's Laws, Quadratic Equations, Cell Structure, OOP Basics).
- Supports dynamic registration of arbitrary packs via register_pack().
- Absence of a topic from the catalog returns None / [] gracefully without failing generation.
"""
from typing import Dict, List, Any, Optional, Callable
from pydantic import BaseModel, Field
from app.services.notes.schemas import (
    NoteSection, VisualSpec, CalloutItem, NoteDepth, NoteDifficulty, SectionSemanticEvidence
)


class CurriculumVersion(BaseModel):
    """Represents versioning and syllabus authority for a curriculum pack."""
    board: str = "CBSE"
    grade: Optional[int] = None
    subject: str = "General"
    course: Optional[str] = None
    curriculum_version: str = "2024-2025"
    source_version: str = "1.0"
    effective_date: str = "2024-04-01"


class CurriculumPack(BaseModel):
    """Curated, structured curriculum knowledge pack for a specific educational topic."""
    id: str
    topic: str
    subject: str
    aliases: List[str] = Field(default_factory=list)
    version: CurriculumVersion = Field(default_factory=CurriculumVersion)
    sections_factory: Optional[Any] = None
    practice: List[Dict[str, Any]] = Field(default_factory=list)
    formulas: List[str] = Field(default_factory=list)
    capstone_example: Optional[Dict[str, Any]] = None
    checkpoints: List[str] = Field(default_factory=list)
    visual_spec: Optional[VisualSpec] = None
    misconceptions: List[Dict[str, Any]] = Field(default_factory=list)
    key_points: List[str] = Field(default_factory=list)

    def get_sections(
        self,
        depth: NoteDepth = NoteDepth.DETAILED,
        difficulty: NoteDifficulty = NoteDifficulty.STANDARD
    ) -> List[NoteSection]:
        if callable(self.sections_factory):
            return self.sections_factory(depth, difficulty)
        elif isinstance(self.sections_factory, list):
            return self.sections_factory
        return []


class CurriculumCatalog:
    """
    Authoritative repository of curriculum-aligned pedagogical content.
    Acts as an OPTIONAL curated knowledge source, NOT a topic whitelist or gatekeeper.
    """
    _REGISTRY: Dict[str, CurriculumPack] = {}
    _ALIAS_INDEX: Dict[str, str] = {}
    _INITIALIZED: bool = False

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Initializes default curated packs into the data registry if not already loaded."""
        if cls._INITIALIZED:
            return

        # 1. Chemical Bonding
        cls.register_pack(CurriculumPack(
            id="chemical_bonding",
            topic="Chemical Bonding",
            subject="Chemistry",
            aliases=[
                "chemical bonding",
                "chemical bonding and molecular structure",
                "chemical-bonding",
                "chemical_bonding",
                "molecular structure",
                "chemical bond"
            ],
            version=CurriculumVersion(board="CBSE", grade=11, subject="Chemistry", curriculum_version="2024-2025"),
            sections_factory=cls._chemical_bonding_sections,
            practice=cls._chemical_bonding_practice(),
            formulas=[
                "Formal Charge: FC = V - L - (1/2)B",
                "Bond Order = (N_b - N_a) / 2",
                "Steric Number: SN = (number of σ bonds) + (number of lone pairs)",
                "Dipole Moment: μ = q × d (expressed in Debye, D)"
            ],
            capstone_example={
                "title": "Comprehensive Worked Example: Geometry & Axial Asymmetry in PCl5",
                "content": (
                    "**Problem**: Determine the steric number, hybridization of the central atom, and 3D molecular geometry of Phosphorus Pentachloride (PCl5). Account for the difference between axial and equatorial bond lengths.\n\n"
                    "**Given**: Neutral PCl5 molecule with central Phosphorus atom (Group 15) bonded to 5 Chlorine atoms.\n\n"
                    "**Concept**: VSEPR steric number calculation and sp³d trigonal bipyramidal hybrid orbital mapping.\n\n"
                    "**Step 1: Valence Electron Identification**\nPhosphorus has 5 valence electrons in its outer shell (3s² 3p³). Each Chlorine atom requires 1 electron to complete its octet.\n\n"
                    "**Step 2: Determine Bonding and Lone Pairs**\nPhosphorus forms 5 single P-Cl covalent bonds (5 σ bonds) with zero unshared lone pairs.\n\n"
                    "**Step 3: Calculate Steric Number**\nSteric Number (SN) = (number of σ bonds) + (number of lone pairs) = 5 + 0 = 5.\n\n"
                    "**Step 4: Map to Hybridization**\nSteric Number 5 requires mixing one 3s, three 3p, and one 3d orbital, producing five sp³d hybrid orbitals arranged in a Trigonal Bipyramidal geometry.\n\n"
                    "**Step 5: Bond Length & Repulsion Analysis**\nThe three equatorial P-Cl bonds lie in a plane with 120° angles. The two axial P-Cl bonds lie along the vertical axis at 90° to the equatorial plane. Because 90° repulsions are significantly stronger, the axial bonds (240 pm) are longer and weaker than the equatorial bonds (202 pm).\n\n"
                    "**Final Answer**: Steric Number = 5; Central Atom Hybridization = sp³d; Molecular Geometry = Trigonal Bipyramidal; Axial P-Cl (240 pm) > Equatorial P-Cl (202 pm).\n\n"
                    "**Why**: Five electron domains arrange themselves to minimize mutual electrostatic repulsion, with axial positions experiencing three 90° interactions versus two for equatorial positions."
                ),
                "example": (
                    "**Problem**: Analyze PCl5 geometry and bond asymmetry.\n"
                    "**Step 1**: Central P has 5 valence electrons, forms 5 σ bonds (SN = 5).\n"
                    "**Step 2**: Hybridization = sp³d; Geometry = Trigonal Bipyramidal.\n"
                    "**Step 3**: Axial P-Cl bonds (240 pm) are longer than equatorial P-Cl bonds (202 pm) due to greater 90° repulsion.\n"
                    "**Final Answer**: Trigonal Bipyramidal with unequal axial/equatorial bonds."
                )
            },
            checkpoints=[
                "Why is the H-O-H bond angle in water (104.5°) smaller than the H-N-H angle in ammonia (107.0°) despite identical steric numbers?",
                "What structural factor permits PCl5 and SF6 to violate the octet rule while NCl5 does not exist?",
                "Distinguish between intermolecular and intramolecular hydrogen bonding and explain their respective effects on boiling points."
            ],
            visual_spec=VisualSpec(
                type="flowchart",
                title="Chemical Bonding Master Decision Architecture: From Valence Electrons to 3D Shape",
                raw_svg=(
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 260" width="100%" height="auto">'
                    '<defs>'
                    '<linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="100%">'
                    '<stop offset="0%" stop-color="#2b6cb0"/><stop offset="100%" stop-color="#3182ce"/>'
                    '</linearGradient>'
                    '<linearGradient id="g2" x1="0%" y1="0%" x2="100%" y2="100%">'
                    '<stop offset="0%" stop-color="#2c7a7b"/><stop offset="100%" stop-color="#319795"/>'
                    '</linearGradient>'
                    '<linearGradient id="g3" x1="0%" y1="0%" x2="100%" y2="100%">'
                    '<stop offset="0%" stop-color="#c05621"/><stop offset="100%" stop-color="#dd6b20"/>'
                    '</linearGradient>'
                    '<filter id="sh" x="-5%" y="-5%" width="110%" height="115%">'
                    '<feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.1"/>'
                    '</filter>'
                    '</defs>'
                    '<rect x="20" y="20" width="200" height="90" rx="8" fill="url(#g1)" filter="url(#sh)"/>'
                    '<text x="120" y="55" fill="#ffffff" font-size="13" font-weight="700" text-anchor="middle">Step 1: Valence Count</text>'
                    '<text x="120" y="75" fill="#e2e8f0" font-size="10" text-anchor="middle">Sum Valence Electrons (V)</text>'
                    '<path d="M 220 65 L 270 65" stroke="#4a5568" stroke-width="2.5" fill="none"/>'
                    '<rect x="280" y="20" width="200" height="90" rx="8" fill="url(#g2)" filter="url(#sh)"/>'
                    '<text x="380" y="55" fill="#ffffff" font-size="13" font-weight="700" text-anchor="middle">Step 2: Steric Number</text>'
                    '<text x="380" y="75" fill="#e2e8f0" font-size="10" text-anchor="middle">SN = (sigma bonds) + (lone pairs)</text>'
                    '<path d="M 480 65 L 530 65" stroke="#4a5568" stroke-width="2.5" fill="none"/>'
                    '<rect x="540" y="20" width="200" height="90" rx="8" fill="url(#g3)" filter="url(#sh)"/>'
                    '<text x="640" y="55" fill="#ffffff" font-size="13" font-weight="700" text-anchor="middle">Step 3: Electron Geometry</text>'
                    '<text x="640" y="75" fill="#e2e8f0" font-size="10" text-anchor="middle">SN 2: Linear | SN 4: Tetrahedral</text>'
                    '<path d="M 640 110 L 640 150" stroke="#4a5568" stroke-width="2.5" fill="none"/>'
                    '<rect x="280" y="150" width="460" height="85" rx="8" fill="#edf2f7" stroke="#cbd5e0" stroke-width="1.5" filter="url(#sh)"/>'
                    '<text x="510" y="180" fill="#2d3748" font-size="12" font-weight="700" text-anchor="middle">Step 4: Observed Molecular Shape (Adjust for Lone Pairs)</text>'
                    '<text x="510" y="202" fill="#4a5568" font-size="10.5" text-anchor="middle">VSEPR Repulsion Order: Lone Pair - Lone Pair > Lone Pair - Bond Pair > Bond Pair - Bond Pair</text>'
                    '<text x="510" y="220" fill="#718096" font-size="9.5" text-anchor="middle">Example: NH3 (SN=4, 1 lp) = Trigonal Pyramidal (107.0°) | H2O (SN=4, 2 lp) = Bent (104.5°)</text>'
                    '</svg>'
                ),
                nodes=[
                    {"id": "cb1", "label": "Step 1: Valence Electron Count (V)"},
                    {"id": "cb2", "label": "Step 2: Steric Number (SN = σ + lp)"},
                    {"id": "cb3", "label": "Step 3: Electron Geometry Mapping"},
                    {"id": "cb4", "label": "Step 4: Observable Molecular Shape"}
                ],
                edges=[
                    {"from": "cb1", "to": "cb2", "label": "sum domains"},
                    {"from": "cb2", "to": "cb3", "label": "determine geometry"},
                    {"from": "cb3", "to": "cb4", "label": "adjust for lone pairs"}
                ],
                mermaid_code="graph TD\n  A[Valence Count] --> B[Steric Number]\n  B --> C[Electron Geometry]\n  C --> D[Molecular Shape]"
            )
        ))

        # 2. Newton's Laws
        cls.register_pack(CurriculumPack(
            id="newtons_laws",
            topic="Newton's Laws of Motion",
            subject="Physics",
            aliases=[
                "newton's laws",
                "newtons laws",
                "newton's laws of motion",
                "newtons laws of motion",
                "laws of motion",
                "newtons_laws"
            ],
            version=CurriculumVersion(board="CBSE", grade=11, subject="Physics", curriculum_version="2024-2025"),
            sections_factory=cls._newtons_laws_sections,
            practice=cls._newtons_laws_practice(),
            formulas=[
                "Newton's Second Law: F_{net} = m · a = dp/dt",
                "Linear Momentum: p = m · v",
                "Impulse-Momentum Theorem: J = F_{avg} · Δt = Δp",
                "Maximum Static Friction: f_{s,max} = μ_s · N",
                "Kinetic Friction: f_k = μ_k · N"
            ],
            capstone_example={
                "title": "Comprehensive Worked Example: Two-Body Connected System on an Inclined Plane",
                "content": (
                    "**Problem**: A block of mass m1 = 5 kg rests on a frictionless plane inclined at 30°. It is connected by a light string over a frictionless pulley to a hanging mass m2 = 4 kg. Calculate the acceleration of the system and tension in the string. (g = 9.8 m/s²)\n\n"
                    "**Given**: m1 = 5 kg, θ = 30°, m2 = 4 kg, g = 9.8 m/s².\n\n"
                    "**Concept**: Newton's Second Law (ΣF = ma) applied to isolated free-body diagrams.\n\n"
                    "**Step 1: Coordinate Systems & Forces**\nFor m1 along the incline: T - m1·g·sin(30°) = m1·a.\nFor m2 vertically downward: m2·g - T = m2·a.\n\n"
                    "**Step 2: Eliminate Tension by Adding Equations**\n(m2·g - T) + (T - m1·g·sin(30°)) = (m1 + m2)·a\nm2·g - m1·g·sin(30°) = (m1 + m2)·a\n\n"
                    "**Step 3: Numerical Computation**\n4(9.8) - 5(9.8)(0.5) = (5 + 4)·a\n39.2 - 24.5 = 9·a -> 14.7 = 9·a -> a = 1.63 m/s².\n\n"
                    "**Step 4: Solve for String Tension**\nT = m2(g - a) = 4(9.8 - 1.63) = 4(8.17) = 32.68 N.\n\n"
                    "**Final Answer**: Acceleration a = 1.63 m/s² (m2 accelerating downward); Tension T = 32.68 N.\n\n"
                    "**Why**: Net gravitational driving force exceeds the parallel gravitational resistance of m1, producing uniform net system acceleration."
                ),
                "example": (
                    "**Problem**: Connected masses on 30° incline (m1 = 5 kg, m2 = 4 kg hanging).\n"
                    "**Step 1**: Write Second Law equations: T - m1·g·sin(30°) = m1·a and m2·g - T = m2·a.\n"
                    "**Step 2**: Solve for a: a = (4 - 2.5)(9.8) / 9 = 1.63 m/s².\n"
                    "**Step 3**: Solve for T: T = 4(9.8 - 1.63) = 32.68 N.\n"
                    "**Final Answer**: a = 1.63 m/s², T = 32.68 N."
                )
            },
            checkpoints=[
                "Why does an object moving at constant velocity require zero net external force according to the First Law?",
                "Using the impulse-momentum theorem, explain why catching a ball with yielding hands reduces the force on the palms.",
                "Identify the action-reaction pair when a person walks on a horizontal surface."
            ],
            visual_spec=VisualSpec(
                type="flowchart",
                title="Newton's Laws of Motion: Dynamic Force Analysis Workflow",
                nodes=[
                    {"id": "n1", "label": "Identify System & Isolated Body"},
                    {"id": "n2", "label": "Construct Free-Body Diagram (FBD)"},
                    {"id": "n3", "label": "Resolve Forces along Orthogonal Axes (x, y)"},
                    {"id": "n4", "label": "Apply Newton's Second Law: ΣF = ma"}
                ],
                edges=[
                    {"from": "n1", "to": "n2", "label": "isolate"},
                    {"from": "n2", "to": "n3", "label": "decompose"},
                    {"from": "n3", "to": "n4", "label": "solve"}
                ],
                mermaid_code="graph LR\n  A[Isolate Body] --> B[Draw FBD]\n  B --> C[Resolve Axes]\n  C --> D[Solve ΣF = ma]"
            )
        ))

        # 3. Quadratic Equations
        cls.register_pack(CurriculumPack(
            id="quadratic_equations",
            topic="Quadratic Equations",
            subject="Mathematics",
            aliases=[
                "quadratic equations",
                "quadratic equation",
                "quadratics",
                "quadratic_equations"
            ],
            version=CurriculumVersion(board="CBSE", grade=10, subject="Mathematics", curriculum_version="2024-2025"),
            sections_factory=cls._quadratic_equations_sections,
            practice=cls._quadratic_equations_practice(),
            formulas=[
                "Standard Form: ax² + bx + c = 0 (a ≠ 0)",
                "Quadratic Formula: x = (-b ± √(b² - 4ac)) / (2a)",
                "Discriminant: D = b² - 4ac",
                "Sum of Roots: α + β = -b/a",
                "Product of Roots: α · β = c/a"
            ],
            checkpoints=[
                "What condition on the discriminant D guarantees two real, distinct, and rational roots?",
                "Why must the leading coefficient 'a' be non-zero in the standard form ax² + bx + c = 0?",
                "Explain the geometric relationship between the discriminant D and the x-intercepts of the parabola y = ax² + bx + c."
            ],
            visual_spec=VisualSpec(
                type="flowchart",
                title="Quadratic Equations: Discriminant & Root Analysis Pathway",
                nodes=[
                    {"id": "q1", "label": "Standard Form: ax² + bx + c = 0"},
                    {"id": "q2", "label": "Compute Discriminant: D = b² - 4ac"},
                    {"id": "q3", "label": "D > 0: Two Real & Distinct Roots"},
                    {"id": "q4", "label": "D = 0: Two Real & Equal Roots (-b/2a)"},
                    {"id": "q5", "label": "D < 0: Complex Conjugate Roots"}
                ],
                edges=[
                    {"from": "q1", "to": "q2", "label": "calculate D"},
                    {"from": "q2", "to": "q3", "label": "D > 0"},
                    {"from": "q2", "to": "q4", "label": "D = 0"},
                    {"from": "q2", "to": "q5", "label": "D < 0"}
                ],
                mermaid_code="graph TD\n  A[ax² + bx + c = 0] --> B[D = b² - 4ac]\n  B --> C[D > 0: Two Real Distinct]\n  B --> D[D = 0: Equal -b/2a]\n  B --> E[D < 0: Complex Roots]"
            )
        ))

        # 4. Cell Structure
        cls.register_pack(CurriculumPack(
            id="cell_structure",
            topic="Cell Structure and Functions",
            subject="Biology",
            aliases=[
                "cell structure",
                "cell structure and functions",
                "cell biology",
                "cell organelles",
                "cell_structure"
            ],
            version=CurriculumVersion(board="CBSE", grade=9, subject="Biology", curriculum_version="2024-2025"),
            sections_factory=cls._cell_structure_sections,
            practice=cls._cell_structure_practice(),
            formulas=[
                "Surface Area to Volume Ratio: SA/V = (6s²)/(s³) = 6/s (for cubic cell)",
                "Magnification: M = Image Size / Actual Size",
                "Diffusion Rate: Fick's Law: J = -D · (dc/dx)"
            ],
            checkpoints=[
                "What structural features distinguish prokaryotic 70S ribosomes from eukaryotic 80S ribosomes?",
                "How does the fluid mosaic model explain the selective permeability of the plasma membrane?",
                "Why are mitochondria and chloroplasts classified as semi-autonomous organelles?"
            ]
        ))

        # 5. OOP Basics
        cls.register_pack(CurriculumPack(
            id="oop_basics",
            topic="Object Oriented Programming Basics",
            subject="Computer Science",
            aliases=[
                "oop basics",
                "object oriented programming",
                "oop",
                "object-oriented programming",
                "oop_basics"
            ],
            version=CurriculumVersion(board="CBSE", grade=11, subject="Computer Science", curriculum_version="2024-2025"),
            sections_factory=cls._oop_basics_sections,
            practice=cls._oop_basics_practice(),
            formulas=[
                "Cohesion Metric: High Cohesion = Single Responsibility Principle",
                "Coupling Metric: Low Coupling = Minimal Direct Dependencies",
                "Encapsulation: State + Operations = Class (Data Hiding via Private/Protected)"
            ],
            checkpoints=[
                "How does encapsulation protect data integrity compared to procedural programming?",
                "What distinguishes method overriding in inheritance from method overloading?",
                "Provide an example demonstrating runtime polymorphism using a common interface."
            ]
        ))

        cls._INITIALIZED = True

    @classmethod
    def register_pack(cls, pack: CurriculumPack) -> None:
        """
        Dynamically registers a curated curriculum pack into the catalog.
        Allows data-driven scaling to thousands of topics without code modifications.
        """
        cls._REGISTRY[pack.id] = pack
        cls._ALIAS_INDEX[pack.id.lower()] = pack.id
        cls._ALIAS_INDEX[pack.topic.lower()] = pack.id
        for alias in pack.aliases:
            cls._ALIAS_INDEX[alias.lower()] = pack.id

    @classmethod
    def get_pack(cls, topic_key: str) -> Optional[CurriculumPack]:
        """Returns the registered curriculum pack for a key, if present."""
        cls._ensure_initialized()
        return cls._REGISTRY.get(topic_key)

    @classmethod
    def match_topic(cls, subject: str, topic: str) -> Optional[str]:
        """
        Normalizes and matches incoming topic strings to registered catalog keys.
        Returns None for uncataloged topics. Catalog absence is NEVER an error.
        """
        cls._ensure_initialized()
        if not topic:
            return None

        t_clean = topic.strip().lower()
        if t_clean in cls._ALIAS_INDEX:
            return cls._ALIAS_INDEX[t_clean]

        import re
        t_alpha = re.sub(r'[^a-z0-9]+', ' ', t_clean).strip()
        if t_alpha in cls._ALIAS_INDEX:
            return cls._ALIAS_INDEX[t_alpha]

        for alias, pid in cls._ALIAS_INDEX.items():
            if alias == t_clean or alias == t_alpha:
                return pid
            if len(alias) >= 5 and (alias in t_clean or t_clean in alias):
                return pid

        return None

    @classmethod
    def get_sections(
        cls,
        topic_key: str,
        depth: NoteDepth = NoteDepth.DETAILED,
        difficulty: NoteDifficulty = NoteDifficulty.STANDARD
    ) -> List[NoteSection]:
        """Returns structured NoteSections for a registered curriculum topic."""
        pack = cls.get_pack(topic_key)
        if pack:
            return pack.get_sections(depth, difficulty)
        return []

    @classmethod
    def get_practice(
        cls,
        topic_key: str,
        count: int = 5,
        difficulty: str = "standard"
    ) -> List[Dict[str, Any]]:
        """Returns progressive Bloom's practice items for a registered curriculum topic."""
        pack = cls.get_pack(topic_key)
        if not pack or not pack.practice:
            return []

        items = pack.practice
        adapted: List[Dict[str, Any]] = []
        for idx, item in enumerate(items[:count]):
            it = dict(item)
            it["difficulty"] = difficulty
            q_text = it.get("question", "")
            if difficulty == "advanced" and "advanced" not in q_text.lower():
                it["question"] = f"Advanced Problem {idx+1}: {q_text}"
            elif difficulty == "foundational" and "foundational" not in q_text.lower():
                it["question"] = f"Foundational Review {idx+1}: {q_text}"
            adapted.append(it)

        return adapted

    @classmethod
    def get_formulas(cls, topic_key: str) -> List[str]:
        """Returns authentic quantitative formulations for a registered curriculum topic."""
        pack = cls.get_pack(topic_key)
        return list(pack.formulas) if pack else []

    @classmethod
    def get_capstone_worked_example(cls, topic_key: str) -> Optional[Dict[str, Any]]:
        """Returns capstone multi-step worked example for a registered curriculum topic."""
        pack = cls.get_pack(topic_key)
        return pack.capstone_example if pack else None

    @classmethod
    def get_checkpoints(cls, topic_key: str) -> List[str]:
        """Returns subject-tailored checkpoint assessment questions for a registered topic."""
        pack = cls.get_pack(topic_key)
        return list(pack.checkpoints) if pack else []

    @classmethod
    def get_visual_spec(cls, topic_key: str) -> Optional[VisualSpec]:
        """Returns master visual specification for a registered curriculum topic."""
        pack = cls.get_pack(topic_key)
        return pack.visual_spec if pack else None

    # =========================================================================
    # 1. CHEMICAL BONDING SECTIONS & PRACTICE
    # =========================================================================
    @classmethod
    def _chemical_bonding_sections(cls, depth: NoteDepth, difficulty: NoteDifficulty) -> List[NoteSection]:
        return [
            NoteSection(
                id="sec_octet",
                section_type="core_concept",
                title="Octet Rule and Lewis Molecular Structures",
                content=(
                    "### 1. Simple Idea\n"
                    "Atoms combine with one another to achieve electronic stability, mimicking the chemically inert noble gases "
                    "with eight valence electrons in their outermost shell.\n\n"
                    "### 2. Intuition: The Musical Chairs of Valence Shells\n"
                    "Think of valence shells like musical chairs where an atom is restless until all 8 seats are securely filled. "
                    "An atom will trade, surrender, or share electrons until every chair has a partner, minimizing electrostatic potential energy.\n\n"
                    "### 3. Formal Postulates & Lewis Dot Representations\n"
                    "Formulated by G.N. Lewis and W. Kossel (1916):\n"
                    "1. Atoms achieve stability by transferring or sharing valence electrons to attain a stable octet (ns² np⁶).\n"
                    "2. A covalent bond consists of a shared electron pair between two participating atoms.\n"
                    "3. Formal charge on an individual bonded atom evaluates electronic distribution across Lewis structures:\n"
                    "$$\\text{Formal Charge} = V - L - \\frac{1}{2}B$$\n"
                    "where $V$ is total valence electrons in the free atom, $L$ is non-bonding lone pair electrons, and $B$ is total bonding electrons.\n\n"
                    "### 4. Comparison: Lewis Dot Symbols & Representative Covalent Configurations\n\n"
                    "| Element / Molecule | Group Valence | Lewis Dot Representation | Bonding Electron Pairs | Lone Pairs | Resulting State |\n"
                    "|---|---|---|---|---|---|\n"
                    "| Carbon (CH4) | 4 | :C: (4 dots) | 4 shared pairs | 0 lone pairs | Stable octet |\n"
                    "| Nitrogen (NH3) | 5 | :N· (5 dots) | 3 shared pairs | 1 lone pair | Stable octet |\n"
                    "| Oxygen (H2O) | 6 | :Ö: (6 dots) | 2 shared pairs | 2 lone pairs | Stable octet |\n"
                    "| Boron (BF3) | 3 | ·B· (3 dots) | 3 shared pairs | 0 lone pairs | Incomplete octet (6e⁻) |\n"
                    "| Sulfur (SF6) | 6 | :S̈: (6 dots) | 6 shared pairs | 0 lone pairs | Expanded octet (12e⁻) |"
                ),
                key_points=[
                    "Octet rule states atoms combine by gaining, losing, or sharing electrons to achieve 8 valence electrons.",
                    "Formal charge calculation: FC = V - L - (1/2)B.",
                    "Incomplete octets (BF3), expanded octets (SF6, PCl5), and odd-electron molecules (NO) stably violate the rule."
                ],
                examples=[
                    "**Problem**: Calculate the formal charge on each oxygen atom in the Ozone molecule (O3).\n"
                    "**Given**: Ozone molecule with Lewis resonance structure: O(1)=O(2)-O(3).\n"
                    "**Concept**: Formal Charge equation FC = V - L - (1/2)B, where V = 6 for oxygen.\n"
                    "**Step 1: Central Oxygen O(1)**: V = 6. Forms 1 double bond and 1 single bond (B = 6). Retains 1 lone pair (L = 2). "
                    "FC = 6 - 2 - (1/2)(6) = +1.\n"
                    "**Step 2: Double-bonded Terminal Oxygen O(2)**: V = 6. Forms 1 double bond (B = 4). Retains 2 lone pairs (L = 4). "
                    "FC = 6 - 4 - (1/2)(4) = 0.\n"
                    "**Step 3: Single-bonded Terminal Oxygen O(3)**: V = 6. Forms 1 single bond (B = 2). Retains 3 lone pairs (L = 6). "
                    "FC = 6 - 6 - (1/2)(2) = -1.\n"
                    "**Step 4: Verification**: Sum of formal charges = (+1) + (0) + (-1) = 0 (matches neutral O3 molecule charge).\n"
                    "**Final Answer**: Central O = +1, Double-bonded O = 0, Single-bonded O = -1.\n"
                    "**Why**: Formal charge reflects true electron density distribution and explains why resonance hybrid is energetically favored."
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
                title="VSEPR Theory and Molecular Shapes",
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
                    "**Step 3: Calculate Steric Number**: Steric Number = 3 (bond pairs) + 1 (lone pair) = 4.\n"
                    "**Step 4: Map Electron Geometry**: Steric Number 4 corresponds to a Tetrahedral electron domain arrangement.\n"
                    "**Step 5: Determine Observed Shape and Bond Angle**: The single lone pair repels the three N-H bond pairs more strongly than bond pairs repel each other. "
                    "This compresses the standard tetrahedral angle of 109.5° down to 107.0°, yielding a Trigonal Pyramidal molecular shape.\n"
                    "**Final Answer**: Electron Geometry = Tetrahedral; Molecular Shape = Trigonal Pyramidal; Bond Angle = 107.0°.\n"
                    "**Why**: The unshared lone pair is localized on Nitrogen and spreads widely, squeezing the bonding pairs together."
                ],
                callouts=[
                    CalloutItem(
                        type="misconception",
                        title="Misconception: Electron Geometry Equals Molecular Shape",
                        text=(
                            "**Wrong Belief**: NH3 is tetrahedral because it has 4 electron pairs.\n"
                            "**Scientific Reality**: Its electron geometry is tetrahedral, but its observable molecular shape is trigonal pyramidal.\n"
                            "**Why**: Molecular shape is determined solely by the positions of atomic nuclei in 3D space; lone pairs distort angles but are invisible in spectroscopic shape determination."
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
                    "While Lewis theory tracks dots on paper, Valence Bond Theory (VBT) explains covalent bonding through the physical "
                    "overlapping of atomic orbital wavefunctions.\n\n"
                    "### 2. Intuition: Merging Quantum Clouds\n"
                    "Imagine two fuzzy clouds overlapping. Where they merge, the probability of finding electrons between both nuclei increases dramatically. "
                    "The shared negative charge pulls both positive nuclei inward, establishing a chemical bond.\n\n"
                    "### 3. Principles of Orbital Overlap\n"
                    "Introduced by Heitler and London (1927), developed by Linus Pauling:\n"
                    "1. A covalent bond forms when half-filled valence orbitals of two atoms overlap.\n"
                    "2. The overlapping orbitals must contain electrons with opposite spins to satisfy Pauli's exclusion principle.\n"
                    "3. Greater orbital overlap produces a stronger and more stable chemical bond.\n\n"
                    "### 4. Comparison: Sigma (σ) Bonds vs Pi (π) Bonds\n\n"
                    "| Characteristic | Sigma (σ) Bond | Pi (π) Bond |\n"
                    "|---|---|---|\n"
                    "| Nature of Overlap | Axial / Head-on overlap along the internuclear axis | Lateral / Sideways overlap perpendicular to axis |\n"
                    "| Orbitals Involved | s-s, s-p_z, or collinear p_z-p_z | Parallel unhybridized p_x-p_x or p_y-p_y |\n"
                    "| Extent of Overlap | Maximum (high orbital overlap) | Moderate to low (sideways overlap) |\n"
                    "| Bond Strength | Stronger (higher bond dissociation energy) | Weaker (easily cleaved in addition reactions) |\n"
                    "| Electron Cloud Symmetry | Cylindrically symmetrical around internuclear axis | Two lobes: one above and one below the internuclear plane |\n"
                    "| Free Rotation | Allows free rotation around the bond axis | Prevents free rotation (rotation breaks lateral overlap) |\n"
                    "| Existence | Can exist independently as single covalent bond | Exists only in combination with an existing sigma bond |"
                ),
                key_points=[
                    "Sigma bonds result from coaxial head-on overlap; pi bonds result from lateral sideways overlap.",
                    "Sigma bonds possess cylindrical symmetry and allow free rotation; pi bonds restrict rotation.",
                    "Single bond = 1 sigma; Double bond = 1 sigma + 1 pi; Triple bond = 1 sigma + 2 pi."
                ],
                examples=[
                    "**Problem**: Determine the number of sigma (σ) and pi (π) bonds in Ethyne (C2H2) and Benzene (C6H6).\n"
                    "**Given**: Molecular formulas C2H2 (linear alkyne) and C6H6 (planar aromatic ring).\n"
                    "**Concept**: Single covalent bond = 1 σ; Double bond = 1 σ + 1 π; Triple bond = 1 σ + 2 π.\n"
                    "**Step 1: Analyze Ethyne (H-C≡C-H)**: Two C-H single bonds contribute 2 σ bonds. One C≡C triple bond contributes 1 σ and 2 π bonds.\n"
                    "**Step 2: Total Ethyne Bonds**: Total σ bonds = 2 + 1 = 3; Total π bonds = 2.\n"
                    "**Step 3: Analyze Benzene (C6H6)**: Six C-H single bonds contribute 6 σ bonds. The 6-membered ring contains 6 C-C bonds (alternating single and double in Kekulé structures), contributing 6 σ and 3 π bonds.\n"
                    "**Step 4: Total Benzene Bonds**: Total σ bonds = 6 (C-H) + 6 (C-C) = 12; Total π bonds = 3.\n"
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
                callouts=[
                    CalloutItem(
                        type="tip",
                        title="Exam Alert: PCl5 Bond Length Asymmetry",
                        text="In PCl5 (sp³d), the two axial P-Cl bonds (240 pm) experience three 90° repulsions, making them longer and weaker than the three equatorial bonds (202 pm). Upon heating, PCl5 readily decomposes into PCl3 and Cl2."
                    )
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
        ]

    @classmethod
    def _chemical_bonding_practice(cls) -> List[Dict[str, Any]]:
        return [
            {
                "question": "State the Octet Rule and identify two stable chemical species that exist as exceptions with expanded octets.",
                "type": "recall",
                "category": "recall",
                "difficulty": "standard",
                "answer": "The Octet Rule states that atoms combine by gaining, losing, or sharing electrons to complete eight electrons in their valence shell. Two stable exceptions with expanded octets are PCl5 (10 valence electrons) and SF6 (12 valence electrons).",
                "explanation": "Period 3 elements utilize vacant 3d orbitals to accommodate more than 8 valence electrons, forming stable hypervalent compounds.",
                "target_concept": "Octet Rule and Lewis Structures"
            },
            {
                "question": "Using VSEPR theory, explain why Water (H2O) has a smaller bond angle (104.5°) than Ammonia (NH3, 107.0°) even though both have a steric number of 4.",
                "type": "conceptual",
                "category": "conceptual",
                "difficulty": "standard",
                "answer": "Both molecules have 4 total electron domains (tetrahedral electron geometry). However, NH3 has 1 lone pair, whereas H2O has 2 lone pairs. According to VSEPR, lone pair - lone pair repulsion is greater than lone pair - bond pair repulsion. The two lone pairs in H2O exert greater repulsive force, compressing the H-O-H bond angle to 104.5° compared to 107.0° in NH3.",
                "explanation": "Repulsion hierarchy: lp-lp > lp-bp > bp-bp. Greater number of lone pairs produces greater angular compression away from the ideal 109.5° tetrahedral angle.",
                "target_concept": "VSEPR Theory and Molecular Shapes"
            },
            {
                "question": "Calculate the total number of sigma (σ) and pi (π) bonds in a molecule of Propyne (CH3-C≡CH).",
                "type": "application",
                "category": "application",
                "difficulty": "standard",
                "answer": "Propyne contains 6 sigma (σ) bonds and 2 pi (π) bonds.",
                "explanation": "Breakdown: The -CH3 methyl group has 3 C-H single bonds (3 σ). The C-C single bond is 1 σ. The C≡C triple bond contains 1 σ and 2 π bonds. The terminal C-H bond is 1 σ. Total = 3 + 1 + 1 + 1 = 6 σ bonds, and 2 π bonds.",
                "target_concept": "Valence Bond Theory: Sigma and Pi Bonds"
            },
            {
                "question": "Determine the steric number, hybridization of the central atom, and observable molecular shape of Xenon Tetrafluoride (XeF4).",
                "type": "exam-style",
                "category": "exam-style",
                "difficulty": "standard",
                "answer": "Steric Number = 6; Hybridization = sp³d²; Molecular Shape = Square Planar.",
                "explanation": "Xenon has 8 valence electrons. It forms 4 single Xe-F bonds (4 bonding pairs) and retains 4 non-bonding electrons (2 lone pairs). Steric Number = 4 + 2 = 6, requiring sp³d² hybridization with octahedral electron geometry. To minimize repulsion, the two lone pairs occupy trans axial positions (180° apart), leaving the four fluorine atoms in a completely flat Square Planar geometry (all F-Xe-F angles 90°).",
                "target_concept": "Hybridization (sp, sp2, sp3, sp3d, sp3d2)"
            },
            {
                "question": "Explain why Water (H2O, boiling point 100°C) has a significantly higher boiling point than Hydrogen Fluoride (HF, boiling point 19.5°C), even though Fluorine is more electronegative than Oxygen.",
                "type": "challenge",
                "category": "challenge",
                "difficulty": "standard",
                "answer": "Although an individual H-F hydrogen bond is stronger than an individual H-O hydrogen bond due to the higher electronegativity of Fluorine, each H2O molecule can form on average 4 hydrogen bonds (2 donor H atoms, 2 lone pairs on Oxygen) creating an extensive 3D network. In contrast, HF has only 1 H atom per molecule and can form an average of only 2 hydrogen bonds per molecule (linear chains). The cumulative energy required to break the 3D tetrahedral network of liquid water is much greater than that required for HF chains, resulting in a much higher boiling point.",
                "explanation": "Boiling point depends on the total intermolecular cohesion per mole (network density × bond strength), not merely the strength of a single isolated hydrogen bond.",
                "target_concept": "Hydrogen Bonding"
            }
        ]

    # =========================================================================
    # 2. PHYSICS: NEWTON'S LAWS SECTIONS & PRACTICE
    # =========================================================================
    @classmethod
    def _newtons_laws_sections(cls, depth: NoteDepth, difficulty: NoteDifficulty) -> List[NoteSection]:
        return [
            NoteSection(
                id="sec_first_law",
                section_type="core_concept",
                title="First Law of Motion: Inertia and Frames of Reference",
                content=(
                    "### 1. Simple Idea\n"
                    "Objects are fundamentally lazy; they keep doing whatever they were already doing unless something forces them to change.\n\n"
                    "### 2. Intuition: Standing in a Braking Bus\n"
                    "When you stand in a moving bus that suddenly slams on the brakes, your feet stop with the floor due to friction, "
                    "but your upper body continues moving forward at the bus's previous speed. That resistance to change in velocity is inertia.\n\n"
                    "### 3. Formal Definition & Postulate\n"
                    "Newton's First Law states: Every body continues in its state of rest or of uniform motion in a straight line, "
                    "unless compelled to change that state by a net external force.\n"
                    "$$\\sum \\vec{F}_{ext} = 0 \\implies \\vec{a} = 0$$\n"
                    "Inertial frames are reference frames where Newton's first law holds without fictitious forces."
                ),
                key_points=[
                    "Inertia is the inherent property of a body to resist changes in its state of rest or motion.",
                    "Mass is the quantitative measure of inertia.",
                    "Net zero external force implies zero acceleration, not necessarily zero velocity."
                ],
                examples=[
                    "**Problem**: A 5 kg block rests on a smooth frictionless horizontal table. Find the net horizontal force required to maintain a constant velocity of 12 m/s.\n"
                    "**Given**: Mass m = 5 kg, velocity v = 12 m/s (constant), acceleration a = 0 m/s².\n"
                    "**Concept**: Newton's First Law (a = 0 implies net external force = 0).\n"
                    "**Step 1**: Identify the condition: constant velocity in a straight line means acceleration a = 0.\n"
                    "**Step 2**: Apply First Law: F_net = m * a = 5 * 0 = 0 N.\n"
                    "**Final Answer**: Net horizontal force required = 0 N.\n"
                    "**Why**: In the absence of friction, an object in motion requires zero force to sustain its constant velocity."
                ]
            ),
            NoteSection(
                id="sec_second_law",
                section_type="core_concept",
                title="Second Law of Motion: Momentum and Force (F = ma)",
                content=(
                    "### 1. Simple Idea\n"
                    "How fast an object changes its motion depends directly on how hard you push it and inversely on how heavy it is.\n\n"
                    "### 2. Intuition: Catching a Cricket Ball vs Tennis Ball\n"
                    "A fast-moving cricket ball hurts your hands much more than a tennis ball traveling at the same speed because the heavier cricket ball "
                    "carries more momentum. To stop it in a split second requires a massive opposing force.\n\n"
                    "### 3. Formal Principle & Mathematical Derivation\n"
                    "The rate of change of momentum of a body is directly proportional to the applied force and takes place in the direction of the force:\n"
                    "$$\\vec{F} = \\frac{d\\vec{p}}{dt} = \\frac{d(m\\vec{v})}{dt}$$\n"
                    "For constant mass $m$:\n"
                    "$$\\vec{F} = m\\vec{a}$$\n"
                    "SI unit of force is the Newton (1 N = 1 kg·m/s²)."
                ),
                key_points=[
                    "Force equals rate of change of linear momentum: F = dp/dt.",
                    "Impulse J = F * Δt = Δp (change in momentum).",
                    "Second law provides the quantitative definition of force."
                ],
                examples=[
                    "**Problem**: A constant horizontal force acts on a 1500 kg car, accelerating it from rest to 20 m/s in 10 seconds. Find the magnitude of the force.\n"
                    "**Given**: Mass m = 1500 kg, initial velocity u = 0 m/s, final velocity v = 20 m/s, time t = 10 s.\n"
                    "**Concept**: Newton's Second Law F = m * a, where a = (v - u) / t.\n"
                    "**Step 1: Calculate Acceleration**: a = (20 - 0) / 10 = 2 m/s².\n"
                    "**Step 2: Calculate Force**: F = m * a = 1500 kg * 2 m/s² = 3000 N.\n"
                    "**Final Answer**: Applied force = 3000 N (3.0 kN).\n"
                    "**Why**: A steady 3.0 kN force imparts the required rate of momentum change over the 10-second interval."
                ]
            ),
            NoteSection(
                id="sec_third_law",
                section_type="core_concept",
                title="Third Law of Motion: Action-Reaction Pairs and Friction",
                content=(
                    "### 1. Simple Idea\n"
                    "You cannot push something without it pushing you back equally hard.\n\n"
                    "### 2. Formal Principle & Comparison Matrix\n"
                    "To every action, there is always an equal and opposite reaction:\n"
                    "$$\\vec{F}_{AB} = -\\vec{F}_{BA}$$\n"
                    "Crucially, action and reaction forces act on **two different bodies**, so they never cancel each other out.\n\n"
                    "| Force Type | Direction | Magnitude | Action-Reaction Counterpart |\n"
                    "|---|---|---|---|\n"
                    "| Weight (mg) | Vertically downward | m * g | Gravitational pull of body on Earth |\n"
                    "| Normal Force (N) | Perpendicular to contact plane | Dependent on equilibrium | Contact push exerted by body on surface |\n"
                    "| Static Friction (f_s) | Opposing impending motion | 0 <= f_s <= μ_s * N | Tangential friction exerted on surface |\n"
                    "| Kinetic Friction (f_k) | Opposing actual relative slip | f_k = μ_k * N | Drag force on sliding interface |"
                ),
                key_points=[
                    "Action and reaction forces occur simultaneously on two different bodies.",
                    "Friction opposes impending (static) or actual (kinetic) relative sliding between surfaces.",
                    "Maximum static friction (limiting friction) f_max = μ_s * N, where μ_s > μ_k."
                ]
            )
        ]

    @classmethod
    def _newtons_laws_practice(cls) -> List[Dict[str, Any]]:
        return [
            {
                "question": "State Newton's Second Law of Motion in terms of momentum and show how it reduces to F = ma for constant mass.",
                "type": "recall",
                "category": "recall",
                "difficulty": "standard",
                "answer": "Newton's Second Law states that the rate of change of linear momentum of a body is directly proportional to the applied force: F = dp/dt. Since p = mv, F = d(mv)/dt = m(dv/dt) + v(dm/dt). For constant mass, dm/dt = 0, giving F = m(dv/dt) = ma.",
                "explanation": "Momentum is the fundamental physical quantity; F = ma is a special case applicable when mass does not vary with time.",
                "target_concept": "Second Law of Motion"
            },
            {
                "question": "Why do action and reaction forces not cancel each other out to produce zero net acceleration?",
                "type": "conceptual",
                "category": "conceptual",
                "difficulty": "standard",
                "answer": "Action and reaction forces act on two completely different bodies. Forces can only cancel if they act simultaneously on the exact same body. For example, when a horse pulls a cart (force on cart), the cart pulls back on the horse (force on horse).",
                "explanation": "Equilibrium requires the vector sum of forces acting on a single isolated system to be zero.",
                "target_concept": "Third Law of Motion"
            },
            {
                "question": "A 10 kg box is pushed across a horizontal floor with a horizontal force of 50 N. The coefficient of kinetic friction between box and floor is μ_k = 0.3. Calculate the acceleration of the box. (Take g = 9.8 m/s²).",
                "type": "application",
                "category": "application",
                "difficulty": "standard",
                "answer": "Acceleration a = 2.06 m/s².",
                "explanation": "Normal force N = mg = 10 * 9.8 = 98 N. Kinetic friction f_k = μ_k * N = 0.3 * 98 = 29.4 N. Net horizontal force F_net = F_applied - f_k = 50 - 29.4 = 20.6 N. By Second Law, a = F_net / m = 20.6 / 10 = 2.06 m/s².",
                "target_concept": "Second Law and Friction"
            },
            {
                "question": "A cricket player lowers their hands backward while catching a fast ball. Using the concept of impulse and momentum, explain why this prevents injury.",
                "type": "exam-style",
                "category": "exam-style",
                "difficulty": "standard",
                "answer": "Impulse is equal to change in momentum: J = F * Δt = Δp. Stopping the ball requires a fixed change in momentum (from initial velocity to zero). By pulling hands backward, the player increases the time duration Δt of the catch. Since F = Δp / Δt, increasing Δt substantially reduces the average impact force F exerted on the player's palms.",
                "explanation": "Force is inversely proportional to collision duration for a given momentum change.",
                "target_concept": "Impulse and Momentum"
            },
            {
                "question": "Two masses m1 = 4 kg and m2 = 6 kg are connected by a light inextensible string passing over a frictionless pulley (Atwood machine). Calculate the acceleration of the system and the tension in the string. (Take g = 9.8 m/s²).",
                "type": "challenge",
                "category": "challenge",
                "difficulty": "standard",
                "answer": "Acceleration a = 1.96 m/s²; Tension T = 47.04 N.",
                "explanation": "For m2 (moving down): m2*g - T = m2*a -> 6*9.8 - T = 6a. For m1 (moving up): T - m1*g = m1*a -> T - 4*9.8 = 4a. Adding equations: (6 - 4)*9.8 = (6 + 4)*a -> 19.6 = 10a -> a = 1.96 m/s². Substitute a into tension: T = 4(9.8 + 1.96) = 4 * 11.76 = 47.04 N.",
                "target_concept": "Connected Bodies and Tension"
            }
        ]

    # =========================================================================
    # 3. MATHEMATICS: QUADRATIC EQUATIONS SECTIONS & PRACTICE
    # =========================================================================
    @classmethod
    def _quadratic_equations_sections(cls, depth: NoteDepth, difficulty: NoteDifficulty) -> List[NoteSection]:
        return [
            NoteSection(
                id="sec_quad_standard",
                section_type="core_concept",
                title="Standard Form and Solution by Factorization",
                content=(
                    "### 1. Simple Idea\n"
                    "A quadratic equation describes relationships where a quantity scales with the square of another, geometrically forming a parabolic curve.\n\n"
                    "### 2. Standard Form & Factorization Method\n"
                    "A quadratic equation in variable $x$ has the standard canonical form:\n"
                    "$$ax^2 + bx + c = 0 \\quad (a \\neq 0)$$\n"
                    "By the Zero-Product Property, if $A \\cdot B = 0$, then $A = 0$ or $B = 0$. Factorization splits the middle term $bx$ into two terms whose product is $a \\cdot c$."
                ),
                key_points=[
                    "Standard form: ax² + bx + c = 0 where a, b, c are real numbers and a ≠ 0.",
                    "Zero-product principle: (x - α)(x - β) = 0 implies roots x = α and x = β.",
                    "Roots represent the x-intercepts of the parabola y = ax² + bx + c."
                ]
            ),
            NoteSection(
                id="sec_quad_formula",
                section_type="core_concept",
                title="Quadratic Formula and Discriminant Analysis",
                content=(
                    "### 1. The Quadratic Formula\n"
                    "For any quadratic equation $ax^2 + bx + c = 0$, the roots are given by:\n"
                    "$$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$$\n\n"
                    "### 2. Comparison: Discriminant ($D = b^2 - 4ac$) and Nature of Roots\n\n"
                    "| Discriminant Value | Nature of Roots | Parabola Geometric Behavior | Solution Multiplicity |\n"
                    "|---|---|---|---|\n"
                    "| D > 0 (perfect square) | Two real and rational roots | Crosses x-axis at two distinct rational points | 2 distinct roots |\n"
                    "| D > 0 (non-perfect square) | Two real, irrational conjugate roots | Crosses x-axis at two distinct irrational points | 2 distinct roots |\n"
                    "| D = 0 | Two real and equal roots (-b / 2a) | Touches x-axis tangentially at its vertex | 1 repeated root |\n"
                    "| D < 0 | Two complex conjugate roots | Does not intersect or touch the x-axis | 2 complex roots |"
                ),
                key_points=[
                    "Quadratic formula: x = (-b ± √(b² - 4ac)) / (2a).",
                    "Discriminant D = b² - 4ac determines the nature of the roots.",
                    "Vieta's relations: Sum of roots α + β = -b/a; Product of roots αβ = c/a."
                ],
                examples=[
                    "**Problem**: Solve 2x² - 5x + 3 = 0 using the quadratic formula and analyze the nature of its roots.\n"
                    "**Given**: Coefficients a = 2, b = -5, c = 3.\n"
                    "**Concept**: Discriminant D = b² - 4ac and Quadratic Formula x = (-b ± √D) / (2a).\n"
                    "**Step 1: Compute Discriminant**: D = (-5)² - 4(2)(3) = 25 - 24 = 1.\n"
                    "**Step 2: Determine Nature of Roots**: Since D = 1 > 0 and 1 is a perfect square, roots are real, distinct, and rational.\n"
                    "**Step 3: Apply Quadratic Formula**: x = (-(-5) ± √1) / (2 * 2) = (5 ± 1) / 4.\n"
                    "**Step 4: Compute Both Roots**: x₁ = (5 + 1) / 4 = 6/4 = 3/2; x₂ = (5 - 1) / 4 = 4/4 = 1.\n"
                    "**Final Answer**: Roots are x = 3/2 and x = 1.\n"
                    "**Why**: Verification via Vieta: Sum = 3/2 + 1 = 5/2 = -b/a; Product = (3/2)(1) = 3/2 = c/a."
                ]
            )
        ]

    @classmethod
    def _quadratic_equations_practice(cls) -> List[Dict[str, Any]]:
        return [
            {
                "question": "State the standard form of a quadratic equation and write the formula for its discriminant.",
                "type": "recall",
                "category": "recall",
                "difficulty": "standard",
                "answer": "The standard form is ax² + bx + c = 0, where a, b, c are real numbers and a ≠ 0. The discriminant is D = b² - 4ac.",
                "explanation": "The condition a ≠ 0 is mandatory because if a = 0, the equation reduces to a linear equation bx + c = 0.",
                "target_concept": "Standard Form and Discriminant"
            },
            {
                "question": "For what values of k does the equation 2x² + kx + 2 = 0 have equal and real roots?",
                "type": "conceptual",
                "category": "conceptual",
                "difficulty": "standard",
                "answer": "k = 4 or k = -4.",
                "explanation": "For equal roots, discriminant D = b² - 4ac = 0. Here a = 2, b = k, c = 2. D = k² - 4(2)(2) = k² - 16 = 0. k² = 16 implies k = ±4.",
                "target_concept": "Nature of Roots"
            },
            {
                "question": "Solve the quadratic equation x² - 7x + 12 = 0 by factoring.",
                "type": "application",
                "category": "application",
                "difficulty": "standard",
                "answer": "x = 3 and x = 4.",
                "explanation": "Find two numbers whose sum is -7 and product is 12: -3 and -4. Factor as (x - 3)(x - 4) = 0. Setting each factor to zero gives x = 3 and x = 4.",
                "target_concept": "Solution by Factorization"
            },
            {
                "question": "If α and β are the roots of x² - 5x + 6 = 0, calculate the value of α² + β² without finding α and β individually.",
                "type": "exam-style",
                "category": "exam-style",
                "difficulty": "standard",
                "answer": "α² + β² = 13.",
                "explanation": "By Vieta's formulas: α + β = -(-5)/1 = 5, and αβ = 6/1 = 6. Use the algebraic identity: α² + β² = (α + β)² - 2αβ = (5)² - 2(6) = 25 - 12 = 13.",
                "target_concept": "Vieta's Relations"
            },
            {
                "question": "Solve the equation 3x² - 2√6x + 2 = 0 using the quadratic formula.",
                "type": "challenge",
                "category": "challenge",
                "difficulty": "standard",
                "answer": "x = √(2/3) (repeated root).",
                "explanation": "Here a = 3, b = -2√6, c = 2. D = (-2√6)² - 4(3)(2) = 24 - 24 = 0. Since D = 0, roots are real and equal: x = -b / (2a) = (2√6) / (2 * 3) = √6 / 3 = √(6/9) = √(2/3).",
                "target_concept": "Quadratic Formula with Radicals"
            }
        ]

    # =========================================================================
    # 4. BIOLOGY: CELL STRUCTURE SECTIONS & PRACTICE
    # =========================================================================
    @classmethod
    def _cell_structure_sections(cls, depth: NoteDepth, difficulty: NoteDifficulty) -> List[NoteSection]:
        return [
            NoteSection(
                id="sec_cell_overview",
                section_type="core_concept",
                title="Cell Theory and Prokaryotic vs Eukaryotic Architecture",
                content=(
                    "### 1. Simple Idea\n"
                    "The cell is the smallest independent structural and functional unit capable of carrying out all processes of life.\n\n"
                    "### 2. Cell Theory Postulates\n"
                    "Formulated by Matthias Schleiden and Theodor Schwann, completed by Rudolf Virchow (1855):\n"
                    "1. All living organisms are composed of cells and products of cells.\n"
                    "2. All cells arise from pre-existing cells (*Omnis cellula-e cellula*).\n\n"
                    "### 3. Comparison: Prokaryotic vs Eukaryotic Cells\n\n"
                    "| Feature | Prokaryotic Cell | Eukaryotic Cell |\n"
                    "|---|---|---|\n"
                    "| Nuclear Membrane | Absent (genetic material in nucleoid) | Present (true membrane-bound nucleus) |\n"
                    "| Membrane-Bound Organelles | Absent (no ER, Golgi, Mitochondria) | Present (ER, Golgi, Mitochondria, Lysosomes) |\n"
                    "| Ribosome Type | 70S (50S + 30S subunits) | 80S in cytoplasm (60S + 40S), 70S in organelles |\n"
                    "| Genetic Material | Single circular naked DNA molecule | Multiple linear chromosomes associated with histones |\n"
                    "| Cell Division | Binary fission or budding | Mitosis and Meiosis |"
                ),
                key_points=[
                    "Cell theory states all life is cellular and new cells arise from pre-existing cells.",
                    "Prokaryotes lack membrane-bound organelles and have 70S ribosomes.",
                    "Eukaryotes feature compartmentalized cytoplasm with 80S cytosolic ribosomes."
                ]
            ),
            NoteSection(
                id="sec_organelles",
                section_type="core_concept",
                title="Plasma Membrane, Endomembrane System, and Energy Organelles",
                content=(
                    "### 1. Plasma Membrane: Fluid Mosaic Model\n"
                    "Proposed by Singer and Nicolson (1972): A phospholipid bilayer with protein icebergs floating in a lipid sea. "
                    "Lipids provide quasi-fluid flexibility, while integral and peripheral proteins enable selective permeability and transport.\n\n"
                    "### 2. Endomembrane System & Energy Converters\n"
                    "Coordinated functional organelles:\n"
                    "1. **Endoplasmic Reticulum (ER)**: Rough ER (protein synthesis via attached ribosomes); Smooth ER (lipid and steroid synthesis).\n"
                    "2. **Golgi Apparatus**: Modifies, packages, and sorts proteins received from ER into secretory vesicles.\n"
                    "3. **Mitochondria**: 'Powerhouses of the cell'; double-membrane organelle with inner cristae producing ATP via aerobic cellular respiration.\n"
                    "4. **Chloroplasts**: Found in plant cells; contains thylakoid stacks (grana) for light-driven ATP/NADPH synthesis and stroma for the Calvin cycle."
                ),
                key_points=[
                    "Fluid mosaic model describes membrane as a dynamic phospholipid bilayer with mobile proteins.",
                    "Endomembrane system includes ER, Golgi apparatus, lysosomes, and vacuoles.",
                    "Mitochondria and chloroplasts are semi-autonomous organelles with their own circular DNA and 70S ribosomes."
                ],
                examples=[
                    "**Problem**: Differentiate plant cells from animal cells regarding cell wall, plastids, vacuoles, and centrosomes.\n"
                    "**Given**: Plant and animal eukaryotic structural templates.\n"
                    "**Concept**: Plant vs Animal cell specialization.\n"
                    "**Step 1: Cell Wall**: Plant cells have a rigid outer cellulose cell wall; animal cells have only a flexible plasma membrane.\n"
                    "**Step 2: Plastids**: Plant cells contain chloroplasts and amyloplasts; animal cells have zero plastids.\n"
                    "**Step 3: Vacuoles**: Plant cells possess a large central permanent vacuole (occupying up to 90% volume); animal cells possess small transient vacuoles.\n"
                    "**Step 4: Centrosomes**: Centrioles are present in almost all animal cells (for spindle organization) but absent in higher plant cells.\n"
                    "**Final Answer**: Plant cells = cellulose wall + plastids + large central vacuole; Animal cells = centrosomes/centrioles + no wall."
                ]
            )
        ]

    @classmethod
    def _cell_structure_practice(cls) -> List[Dict[str, Any]]:
        return [
            {
                "question": "Name the scientists who formulated the Cell Theory and state Rudolf Virchow's classic contribution.",
                "type": "recall",
                "category": "recall",
                "difficulty": "standard",
                "answer": "Matthias Schleiden and Theodor Schwann formulated the cell theory. Rudolf Virchow contributed the principle 'Omnis cellula-e cellula', proving that new cells arise exclusively from the division of pre-existing cells.",
                "explanation": "Virchow modified the original hypothesis to eliminate spontaneous generation theories.",
                "target_concept": "Cell Theory"
            },
            {
                "question": "Why are mitochondria and chloroplasts described as semi-autonomous organelles?",
                "type": "conceptual",
                "category": "conceptual",
                "difficulty": "standard",
                "answer": "Mitochondria and chloroplasts possess their own circular double-stranded DNA and 70S ribosomes, enabling them to synthesize some of their own structural proteins and self-replicate by fission, although they still depend on nuclear DNA for many essential enzymes.",
                "explanation": "This reflects their evolutionary origin via primary endosymbiosis from ancient prokaryotes.",
                "target_concept": "Mitochondria and Chloroplasts"
            },
            {
                "question": "Describe the arrangement of phospholipids in the Singer-Nicolson Fluid Mosaic Model of the plasma membrane.",
                "type": "application",
                "category": "application",
                "difficulty": "standard",
                "answer": "Phospholipids form a continuous bilayer where polar hydrophilic heads point outward toward the aqueous intra- and extra-cellular environments, while nonpolar hydrophobic fatty acid tails face inward toward the core, shielded from water.",
                "explanation": "This amphipathic arrangement maintains membrane structural integrity while allowing lateral fluidity.",
                "target_concept": "Plasma Membrane"
            },
            {
                "question": "Trace the path of a newly synthesized secretory enzyme from its translation site to its secretion outside the cell.",
                "type": "exam-style",
                "category": "exam-style",
                "difficulty": "standard",
                "answer": "Translated by ribosomes on the Rough Endoplasmic Reticulum (RER) -> Transport vesicles -> Cis-face of Golgi Apparatus -> Cisternal maturation and modification -> Trans-face of Golgi -> Secretory vesicles -> Fusion with plasma membrane (exocytosis).",
                "explanation": "The endomembrane system acts as a coordinated assembly and distribution pipeline.",
                "target_concept": "Endomembrane System"
            },
            {
                "question": "Compare prokaryotic 70S ribosomes with eukaryotic 80S ribosomes regarding their subunit sedimentation coefficients.",
                "type": "challenge",
                "category": "challenge",
                "difficulty": "standard",
                "answer": "Prokaryotic 70S ribosomes consist of a 50S large subunit and a 30S small subunit. Eukaryotic 80S cytosolic ribosomes consist of a 60S large subunit and a 40S small subunit. (S is the Svedberg unit measuring sedimentation rate).",
                "explanation": "Svedberg units are nonlinear functions of mass and surface shape, which is why subunit values do not add up arithmetically.",
                "target_concept": "Ribosome Subunits"
            }
        ]

    # =========================================================================
    # 5. COMPUTER SCIENCE: OOP BASICS SECTIONS & PRACTICE
    # =========================================================================
    @classmethod
    def _oop_basics_sections(cls, depth: NoteDepth, difficulty: NoteDifficulty) -> List[NoteSection]:
        return [
            NoteSection(
                id="sec_oop_paradigms",
                section_type="core_concept",
                title="Object-Oriented Paradigm: Classes and Objects",
                content=(
                    "### 1. Simple Idea\n"
                    "Rather than organizing programs as lists of procedural instructions, Object-Oriented Programming (OOP) models software "
                    "around self-contained entities (objects) that bundle data with the functions that operate on that data.\n\n"
                    "### 2. Intuition: Blueprint vs Actual House\n"
                    "A `class` is an architectural blueprint. It defines what attributes a house has (rooms, doors) and what it can do. "
                    "An `object` is the actual physical house built from that blueprint. You can build 50 houses from one blueprint, each with its own independent furniture and occupants.\n\n"
                    "### 3. Comparison: Procedural Programming vs Object-Oriented Programming\n\n"
                    "| Criterion | Procedural Programming (C, Pascal) | Object-Oriented Programming (Python, Java, C++) |\n"
                    "|---|---|---|\n"
                    "| Primary Focus | Functions and sequences of steps | Objects bundling data and behavior |\n"
                    "| Data Security | Global data accessible to any function | Data hidden inside objects via private access modifiers |\n"
                    "| Approach | Top-down decomposition | Bottom-up design and composition |\n"
                    "| Reusability | Limited (function libraries) | High (inheritance, polymorphism, mixins) |\n"
                    "| State Management | Passed explicitly through arguments | Encapsulated inside object instances (`self` / `this`) |"
                ),
                key_points=[
                    "A class is a user-defined template; an object is an instantiated runtime instance of a class.",
                    "State is represented by instance variables (attributes); behavior is represented by methods.",
                    "OOP improves code maintainability, modularity, and reusability."
                ]
            ),
            NoteSection(
                id="sec_oop_pillars",
                section_type="core_concept",
                title="The Four Pillars of OOP: Encapsulation, Abstraction, Inheritance, Polymorphism",
                content=(
                    "### 1. Encapsulation & Abstraction\n"
                    "**Encapsulation**: Bundles data with methods and restricts direct outside access to internal state using private variables. "
                    "Internal state is manipulated only through validated public interfaces (getters and setters).\n"
                    "**Abstraction**: Hides complex implementation details, exposing only clean essential features (e.g. driving a car by pressing the gas pedal without knowing fuel-injection mechanics).\n\n"
                    "### 2. Inheritance & Polymorphism\n"
                    "**Inheritance**: Enables a child class to inherit fields and methods from a parent class (`class Dog(Animal)`), establishing an `is-a` relationship and eliminating redundant code.\n"
                    "**Polymorphism**: 'Many forms'; allows uniform treatment of different subclasses through a common interface. "
                    "Method overriding allows child classes to provide specialized implementations of inherited methods."
                ),
                key_points=[
                    "Encapsulation protects object integrity by preventing unauthorized direct state mutation.",
                    "Abstraction presents high-level interfaces while hiding low-level complexity.",
                    "Inheritance models 'is-a' relationships; Polymorphism enables dynamic dispatch and method overriding."
                ],
                examples=[
                    "**Problem**: Design an encapsulated BankAccount class in Python that prevents negative balances and unauthorized withdrawals.\n"
                    "**Given**: BankAccount requirement with account holder name and balance.\n"
                    "**Concept**: Encapsulation with private attributes and validated public methods.\n"
                    "**Step 1: Define Constructor with Private Attributes**: Use `__balance` to prevent outside tampering.\n"
                    "```python\n"
                    "class BankAccount:\n"
                    "    def __init__(self, owner: str, initial_balance: float = 0.0):\n"
                    "        self.owner = owner\n"
                    "        self.__balance = max(0.0, initial_balance)\n"
                    "```\n"
                    "**Step 2: Implement Validated Deposit Method**: Ensure deposit amount > 0.\n"
                    "```python\n"
                    "    def deposit(self, amount: float) -> bool:\n"
                    "        if amount > 0:\n"
                    "            self.__balance += amount\n"
                    "            return True\n"
                    "        return False\n"
                    "```\n"
                    "**Step 3: Implement Validated Withdraw Method**: Guard against overdraft.\n"
                    "```python\n"
                    "    def withdraw(self, amount: float) -> bool:\n"
                    "        if 0 < amount <= self.__balance:\n"
                    "            self.__balance -= amount\n"
                    "            return True\n"
                    "        return False\n"
                    "```\n"
                    "**Step 4: Provide Read-Only Property**: Expose balance safely.\n"
                    "```python\n"
                    "    @property\n"
                    "    def balance(self) -> float:\n"
                    "        return self.__balance\n"
                    "```\n"
                    "**Final Answer**: Encapsulated class guarantees balance cannot be set directly to invalid states like -500.\n"
                    "**Why**: External callers cannot execute `account.__balance = -500`; all mutations must pass through validated methods."
                ]
            )
        ]

    @classmethod
    def _oop_basics_practice(cls) -> List[Dict[str, Any]]:
        return [
            {
                "question": "Define the relationship between a class and an object in Object-Oriented Programming.",
                "type": "recall",
                "category": "recall",
                "difficulty": "standard",
                "answer": "A class is an abstract template or blueprint that defines the attributes (data) and methods (behavior) common to all entities of its type. An object is a concrete, instantiated runtime instance of that class possessing its own independent state.",
                "explanation": "The class resides in bytecode/type definitions; objects occupy allocated heap memory at runtime.",
                "target_concept": "Classes and Objects"
            },
            {
                "question": "Explain the difference between method overloading (compile-time polymorphism) and method overriding (runtime polymorphism).",
                "type": "conceptual",
                "category": "conceptual",
                "difficulty": "standard",
                "answer": "Method overloading occurs within the same class when multiple methods share the same name but differ in signature (parameter types or count), resolved at compile time. Method overriding occurs across parent and child classes when a subclass provides a specific implementation for an already defined method, resolved dynamically at runtime based on the actual object instance.",
                "explanation": "Overloading provides syntactic flexibility; overriding provides polymorphic behavioral specialization.",
                "target_concept": "Polymorphism"
            },
            {
                "question": "How does Encapsulation improve software security and maintainability compared to public global variables?",
                "type": "application",
                "category": "application",
                "difficulty": "standard",
                "answer": "Encapsulation hides the internal representation of an object by making instance fields private and providing controlled public accessor/mutator methods. This prevents unauthorized direct mutation, enables input validation (e.g. rejecting negative ages), and allows internal data structures to change without breaking external client code.",
                "explanation": "Client code depends on stable method contracts rather than unstable internal data layouts.",
                "target_concept": "Encapsulation"
            },
            {
                "question": "Identify which OOP pillar is demonstrated when a GraphicEditor calls `shape.draw()` on a list containing Circle, Rectangle, and Triangle objects.",
                "type": "exam-style",
                "category": "exam-style",
                "difficulty": "standard",
                "answer": "Polymorphism (Dynamic Method Dispatch).",
                "explanation": "The client treats all items uniformly as instances of the Shape base class, while each specific subclass executes its own customized `draw()` implementation at runtime.",
                "target_concept": "Polymorphism in Practice"
            },
            {
                "question": "Explain the Diamond Problem in multiple inheritance and how modern languages (like Python or C++) resolve it.",
                "type": "challenge",
                "category": "challenge",
                "difficulty": "standard",
                "answer": "The Diamond Problem occurs when a child class D inherits from two parent classes B and C, which both inherit from a common grandparent A. If B and C override a method from A, ambiguity arises over which method D should inherit. Python resolves this deterministically using the C3 Linearization algorithm to produce a strict Method Resolution Order (MRO), accessible via `D.mro()`.",
                "explanation": "C3 linearization guarantees local precedence order and monotonicity without circular dependencies.",
                "target_concept": "Multiple Inheritance and MRO"
            }
        ]
