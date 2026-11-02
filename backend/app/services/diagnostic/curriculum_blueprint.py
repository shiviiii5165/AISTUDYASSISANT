"""
LearnByGenie — Diagnostic Curriculum Blueprint
================================================
Canonical educational domain, skill, and prerequisite taxonomy across:
- Class 3–12 (Primary, Middle, Secondary, Senior Secondary)
- Competitive tracks: Boards, JEE, NEET, Foundation
- Undergrad/Higher Ed: Computer Science & Data Structures
"""
from typing import List, Dict, Optional
from .schemas import DiagnosticDomain, DiagnosticSkill, GradeBand

# ─── CANONICAL DOMAINS ────────────────────────────────────────────────────────

CANONICAL_DOMAINS: List[DiagnosticDomain] = [
    # Mathematics
    DiagnosticDomain(id="MATH_NUM_DOMAIN", subject="Mathematics", domain_name="Numbers & Operations", education_stage="primary", order_index=1),
    DiagnosticDomain(id="MATH_ALG_DOMAIN", subject="Mathematics", domain_name="Algebra & Equations", education_stage="middle_secondary", order_index=2),
    DiagnosticDomain(id="MATH_CALC_DOMAIN", subject="Mathematics", domain_name="Calculus & Analysis", education_stage="senior_secondary", order_index=3),
    # Physics
    DiagnosticDomain(id="PHY_MECH_DOMAIN", subject="Physics", domain_name="Mechanics & Kinematics", education_stage="all", order_index=4),
    DiagnosticDomain(id="PHY_ELEC_DOMAIN", subject="Physics", domain_name="Electrodynamics", education_stage="senior_secondary", order_index=5),
    # Chemistry
    DiagnosticDomain(id="CHEM_STRUCT_DOMAIN", subject="Chemistry", domain_name="Atomic & Molecular Structure", education_stage="secondary_senior", order_index=6),
    # Biology
    DiagnosticDomain(id="BIO_CELL_DOMAIN", subject="Biology", domain_name="Cellular Biology & Genetics", education_stage="secondary_senior", order_index=7),
    # Integrated Science
    DiagnosticDomain(id="SCI_FOUNDATION_DOMAIN", subject="Science", domain_name="Foundational Science", education_stage="primary_middle", order_index=8),
    # English
    DiagnosticDomain(id="ENG_COMP_DOMAIN", subject="English", domain_name="Reading Comprehension & Language", education_stage="all", order_index=9),
    # Computer Science / UG
    DiagnosticDomain(id="CS_ALGO_DOMAIN", subject="Computer Science", domain_name="Data Structures & Algorithms", education_stage="ug", order_index=10),
]

# ─── CANONICAL SKILLS ─────────────────────────────────────────────────────────

CANONICAL_SKILLS: List[DiagnosticSkill] = [
    # ── Mathematics (Class 3 to 12) ──
    DiagnosticSkill(
        id="MATH_NUM_OPS",
        domain_id="MATH_NUM_DOMAIN",
        subject="Mathematics",
        skill_code="MATH_P_01",
        skill_name="Number Operations & Arithmetic",
        grade_band="Class 3-5",
        min_grade=3,
        max_grade=5,
        curriculum_context="all",
        prerequisite_skill_ids=[],
        topic="Basic Arithmetic",
        description="Addition, subtraction, multiplication, and division of whole numbers"
    ),
    DiagnosticSkill(
        id="MATH_FRAC_DEC",
        domain_id="MATH_NUM_DOMAIN",
        subject="Mathematics",
        skill_code="MATH_M_01",
        skill_name="Fractions & Decimals",
        grade_band="Class 6-8",
        min_grade=6,
        max_grade=8,
        curriculum_context="all",
        prerequisite_skill_ids=["MATH_NUM_OPS"],
        topic="Fractions",
        description="Fraction arithmetic, equivalent fractions, decimals conversion"
    ),
    DiagnosticSkill(
        id="MATH_RATIO_PROP",
        domain_id="MATH_NUM_DOMAIN",
        subject="Mathematics",
        skill_code="MATH_M_02",
        skill_name="Ratios & Proportions",
        grade_band="Class 6-8",
        min_grade=6,
        max_grade=8,
        curriculum_context="all",
        prerequisite_skill_ids=["MATH_FRAC_DEC"],
        topic="Ratios",
        description="Ratios, rates, unitary method, and direct proportion"
    ),
    DiagnosticSkill(
        id="MATH_ALG_EXP",
        domain_id="MATH_ALG_DOMAIN",
        subject="Mathematics",
        skill_code="MATH_M_03",
        skill_name="Algebraic Expressions",
        grade_band="Class 6-8",
        min_grade=6,
        max_grade=8,
        curriculum_context="all",
        prerequisite_skill_ids=["MATH_NUM_OPS"],
        topic="Introductory Algebra",
        description="Variables, terms, simplifying algebraic expressions, signs and coefficients"
    ),
    DiagnosticSkill(
        id="MATH_LIN_EQ",
        domain_id="MATH_ALG_DOMAIN",
        subject="Mathematics",
        skill_code="MATH_S_01",
        skill_name="Linear Equations",
        grade_band="Class 9-10",
        min_grade=9,
        max_grade=10,
        curriculum_context="all",
        prerequisite_skill_ids=["MATH_ALG_EXP"],
        topic="Linear Equations",
        description="Solving single and simultaneous linear equations, graph interpretation"
    ),
    DiagnosticSkill(
        id="MATH_QUAD_EQ",
        domain_id="MATH_ALG_DOMAIN",
        subject="Mathematics",
        skill_code="MATH_S_02",
        skill_name="Quadratic Equations & Polynomials",
        grade_band="Class 9-10",
        min_grade=9,
        max_grade=10,
        curriculum_context="all",
        prerequisite_skill_ids=["MATH_LIN_EQ", "MATH_ALG_EXP"],
        topic="Quadratics",
        description="Roots of quadratic equations, factorisation, quadratic formula"
    ),
    DiagnosticSkill(
        id="MATH_CALC_LIMITS",
        domain_id="MATH_CALC_DOMAIN",
        subject="Mathematics",
        skill_code="MATH_SS_01",
        skill_name="Limits & Continuity",
        grade_band="Class 11-12",
        min_grade=11,
        max_grade=12,
        curriculum_context="jee",
        prerequisite_skill_ids=["MATH_QUAD_EQ"],
        topic="Calculus Basics",
        description="Evaluation of indeterminate limits, standard trigonometric limits, continuity"
    ),
    DiagnosticSkill(
        id="MATH_DIFF_CALC",
        domain_id="MATH_CALC_DOMAIN",
        subject="Mathematics",
        skill_code="MATH_SS_02",
        skill_name="Differential Calculus",
        grade_band="Class 11-12",
        min_grade=11,
        max_grade=12,
        curriculum_context="jee",
        prerequisite_skill_ids=["MATH_CALC_LIMITS"],
        topic="Derivatives",
        description="Product rule, chain rule, slope of tangent, rates of change"
    ),

    # ── Physics (Class 9 to 12 / JEE / NEET) ──
    DiagnosticSkill(
        id="PHY_VECTORS",
        domain_id="PHY_MECH_DOMAIN",
        subject="Physics",
        skill_code="PHY_SS_01",
        skill_name="Vectors & Mathematical Tools",
        grade_band="Class 11-12",
        min_grade=11,
        max_grade=12,
        curriculum_context="jee",
        prerequisite_skill_ids=[],
        topic="Vectors",
        description="Vector addition, resolution of components, dot and cross products"
    ),
    DiagnosticSkill(
        id="PHY_MOTION_BASIC",
        domain_id="PHY_MECH_DOMAIN",
        subject="Physics",
        skill_code="PHY_S_01",
        skill_name="Kinematics Basics",
        grade_band="Class 9-10",
        min_grade=9,
        max_grade=10,
        curriculum_context="all",
        prerequisite_skill_ids=[],
        topic="Motion",
        description="Speed, velocity, acceleration, distance-time graphs"
    ),
    DiagnosticSkill(
        id="PHY_NEWTON_LAWS",
        domain_id="PHY_MECH_DOMAIN",
        subject="Physics",
        skill_code="PHY_S_02",
        skill_name="Newton's Laws of Motion",
        grade_band="Class 9-11",
        min_grade=9,
        max_grade=11,
        curriculum_context="all",
        prerequisite_skill_ids=["PHY_MOTION_BASIC"],
        topic="Forces & Dynamics",
        description="Force, inertia, action-reaction pairs, free-body diagrams"
    ),
    DiagnosticSkill(
        id="PHY_ELECTROSTATICS",
        domain_id="PHY_ELEC_DOMAIN",
        subject="Physics",
        skill_code="PHY_SS_02",
        skill_name="Electrostatics & Electric Fields",
        grade_band="Class 12",
        min_grade=12,
        max_grade=12,
        curriculum_context="jee",
        prerequisite_skill_ids=["PHY_VECTORS", "PHY_NEWTON_LAWS"],
        topic="Electrostatics",
        description="Coulomb's law, electric field superposition, electrostatic potential"
    ),

    # ── Chemistry (Class 9 to 12) ──
    DiagnosticSkill(
        id="CHEM_ATOMIC_STRUCT",
        domain_id="CHEM_STRUCT_DOMAIN",
        subject="Chemistry",
        skill_code="CHEM_S_01",
        skill_name="Atomic Structure",
        grade_band="Class 9-11",
        min_grade=9,
        max_grade=11,
        curriculum_context="all",
        prerequisite_skill_ids=[],
        topic="Atomic Theory",
        description="Protons, neutrons, electrons, Bohr model, electronic configuration"
    ),
    DiagnosticSkill(
        id="CHEM_BONDING",
        domain_id="CHEM_STRUCT_DOMAIN",
        subject="Chemistry",
        skill_code="CHEM_SS_01",
        skill_name="Chemical Bonding",
        grade_band="Class 11-12",
        min_grade=11,
        max_grade=12,
        curriculum_context="all",
        prerequisite_skill_ids=["CHEM_ATOMIC_STRUCT"],
        topic="Bonding",
        description="Ionic and covalent bonds, Lewis structures, polarity, octet rule"
    ),

    # ── Biology (Class 8 to 12 / NEET) ──
    DiagnosticSkill(
        id="BIO_CELL_UNIT",
        domain_id="BIO_CELL_DOMAIN",
        subject="Biology",
        skill_code="BIO_S_01",
        skill_name="Cell - Structure & Function",
        grade_band="Class 8-10",
        min_grade=8,
        max_grade=10,
        curriculum_context="all",
        prerequisite_skill_ids=[],
        topic="Cell Biology",
        description="Prokaryotic vs eukaryotic cells, cell organelles, plasma membrane"
    ),
    DiagnosticSkill(
        id="BIO_GENETICS",
        domain_id="BIO_CELL_DOMAIN",
        subject="Biology",
        skill_code="BIO_SS_01",
        skill_name="Principles of Inheritance & Genetics",
        grade_band="Class 11-12",
        min_grade=11,
        max_grade=12,
        curriculum_context="neet",
        prerequisite_skill_ids=["BIO_CELL_UNIT"],
        topic="Genetics",
        description="Mendelian inheritance, monohybrid/dihybrid crosses, DNA replication basics"
    ),

    # ── Integrated Science (Class 3 to 8) ──
    DiagnosticSkill(
        id="SCI_MATTER_STATES",
        domain_id="SCI_FOUNDATION_DOMAIN",
        subject="Science",
        skill_code="SCI_P_01",
        skill_name="States of Matter & Changes",
        grade_band="Class 3-6",
        min_grade=3,
        max_grade=6,
        curriculum_context="all",
        prerequisite_skill_ids=[],
        topic="Matter",
        description="Solids, liquids, gases, melting, evaporation, condensation"
    ),

    # ── English ──
    DiagnosticSkill(
        id="ENG_READ_COMP",
        domain_id="ENG_COMP_DOMAIN",
        subject="English",
        skill_code="ENG_ALL_01",
        skill_name="Reading Comprehension & Inference",
        grade_band="Class 3-12",
        min_grade=3,
        max_grade=12,
        curriculum_context="all",
        prerequisite_skill_ids=[],
        topic="Reading",
        description="Identifying main idea, contextual vocabulary, fact vs inference"
    ),

    # ── Computer Science / UG Coursework ──
    DiagnosticSkill(
        id="CS_BASIC_LOGIC",
        domain_id="CS_ALGO_DOMAIN",
        subject="Computer Science",
        skill_code="CS_UG_01",
        skill_name="Control Flow & Boolean Logic",
        grade_band="UG",
        min_grade=11,
        max_grade=16,
        curriculum_context="ug",
        prerequisite_skill_ids=[],
        topic="Programming Logic",
        description="Loops, conditionals, truth tables, iteration invariants"
    ),
    DiagnosticSkill(
        id="CS_DATA_STRUCT",
        domain_id="CS_ALGO_DOMAIN",
        subject="Computer Science",
        skill_code="CS_UG_02",
        skill_name="Linear Data Structures",
        grade_band="UG",
        min_grade=13,
        max_grade=16,
        curriculum_context="ug",
        prerequisite_skill_ids=["CS_BASIC_LOGIC"],
        topic="Data Structures",
        description="Arrays, singly/doubly linked lists, stack LIFO and queue FIFO mechanics"
    ),
]

_SKILLS_BY_ID: Dict[str, DiagnosticSkill] = {s.id: s for s in CANONICAL_SKILLS}
_SKILLS_BY_SUBJECT: Dict[str, List[DiagnosticSkill]] = {}
for s in CANONICAL_SKILLS:
    _SKILLS_BY_SUBJECT.setdefault(s.subject.lower(), []).append(s)


def get_skill(skill_id: str) -> Optional[DiagnosticSkill]:
    return _SKILLS_BY_ID.get(skill_id)


def get_skills_for_subject(subject: str) -> List[DiagnosticSkill]:
    norm = subject.lower().strip()
    return _SKILLS_BY_SUBJECT.get(norm, [])


def get_prerequisites(skill_id: str) -> List[DiagnosticSkill]:
    sk = get_skill(skill_id)
    if not sk:
        return []
    res = []
    for pid in sk.prerequisite_skill_ids:
        psk = get_skill(pid)
        if psk:
            res.append(psk)
    return res
