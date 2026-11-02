"""
LearnByGenie — Canonical Practice Item Bank (Feature 6)
=========================================================
Curated, teacher-verified practice items mapped to canonical skills across:
- Class 3-5 Mathematics (Primary)
- Class 6-8 Science & Mathematics (Middle)
- Class 9-10 Mathematics & Science (Secondary)
- Class 11-12 JEE Physics & Chemistry (Senior Secondary)
- Class 11-12 NEET Biology (Senior Secondary)
- UG Computer Science & Algorithms
- Target mistake metadata for Mistake DNA repair loops (§9, §29)
- Structured pedagogical hint ladders (§25)
"""
import uuid
from typing import List, Dict, Optional
from .schemas import (
    PracticeItem, QuestionType, DifficultyBand,
    ProvenanceType, VerificationStatus
)


def make_practice_uuid(slug: str) -> str:
    """Derive deterministic UUID from slug."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"learnbygenie.practice.{slug}"))


CANONICAL_PRACTICE_ITEMS: List[PracticeItem] = [
    # ═════════════════════════════════════════════════════════════════════════
    # 1. CLASS 5 MATHEMATICS — NUMBER OPERATIONS (MATH_NUM_OPS)
    # ═════════════════════════════════════════════════════════════════════════
    PracticeItem(
        id=make_practice_uuid("math-num-f-01"),
        skill_id="MATH_NUM_OPS",
        subject="Mathematics",
        grade_band="primary",
        difficulty_band=DifficultyBand.FOUNDATIONAL,
        question_type=QuestionType.MCQ,
        prompt="What is 45 + 37?",
        options=["72", "82", "81", "92"],
        correct_answer="82",
        explanation="Add units: 5 + 7 = 12 (write 2, carry 1). Tens: 4 + 3 + 1 = 8. Total is 82.",
        hints=[
            "Add the one's place first: 5 + 7 = 12.",
            "Remember to carry over the 1 ten to 4 + 3."
        ],
        target_mistake_types=["CALCULATION"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),
    PracticeItem(
        id=make_practice_uuid("math-num-s-01"),
        skill_id="MATH_NUM_OPS",
        subject="Mathematics",
        grade_band="primary",
        difficulty_band=DifficultyBand.STANDARD,
        question_type=QuestionType.MCQ,
        prompt="A toy store has 144 marbles and divides them equally into 12 pouches. How many marbles are in each pouch?",
        options=["10", "11", "12", "14"],
        correct_answer="12",
        explanation="Divide 144 by 12: 144 / 12 = 12 marbles per pouch.",
        hints=[
            "Recall your multiplication tables for 12.",
            "12 times what number equals 144?"
        ],
        target_mistake_types=["CALCULATION", "PROCEDURAL"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),
    PracticeItem(
        id=make_practice_uuid("math-num-a-01"),
        skill_id="MATH_NUM_OPS",
        subject="Mathematics",
        grade_band="primary",
        difficulty_band=DifficultyBand.ADVANCED,
        question_type=QuestionType.NUMERIC,
        prompt="Evaluate: 250 - (45 + 55) + 30",
        options=[],
        correct_answer="180",
        explanation="Calculate parentheses first: 45 + 55 = 100. Then: 250 - 100 + 30 = 150 + 30 = 180.",
        hints=[
            "Solve the part inside the parentheses (45 + 55) first.",
            "Subtract 100 from 250, then add 30."
        ],
        target_mistake_types=["ORDER_OF_OPERATIONS", "CALCULATION"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),

    # ═════════════════════════════════════════════════════════════════════════
    # 2. CLASS 5 / 6 MATHEMATICS — FRACTIONS & DECIMALS (MATH_FRAC_DEC)
    # ═════════════════════════════════════════════════════════════════════════
    PracticeItem(
        id=make_practice_uuid("math-frac-f-01"),
        skill_id="MATH_FRAC_DEC",
        subject="Mathematics",
        grade_band="primary",
        difficulty_band=DifficultyBand.FOUNDATIONAL,
        question_type=QuestionType.MCQ,
        prompt="What is 1/4 + 2/4 in simplest form?",
        options=["3/4", "3/8", "2/4", "1/2"],
        correct_answer="3/4",
        explanation="With identical denominators, add numerators directly: (1 + 2)/4 = 3/4.",
        hints=[
            "The denominators are already the same (4).",
            "Simply add the top numbers: 1 + 2."
        ],
        target_mistake_types=["CONCEPTUAL"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),
    PracticeItem(
        id=make_practice_uuid("math-frac-s-01"),
        skill_id="MATH_FRAC_DEC",
        subject="Mathematics",
        grade_band="middle",
        difficulty_band=DifficultyBand.STANDARD,
        question_type=QuestionType.MCQ,
        prompt="What is 2/3 + 1/4 expressed as an irreducible fraction?",
        options=["11/12", "3/7", "8/12", "9/12"],
        correct_answer="11/12",
        explanation="LCM of 3 and 4 is 12. 2/3 = 8/12 and 1/4 = 3/12. 8/12 + 3/12 = 11/12.",
        hints=[
            "Find the Least Common Multiple (LCM) of 3 and 4.",
            "Convert both fractions to have denominator 12: 2/3 = 8/12 and 1/4 = 3/12."
        ],
        target_mistake_types=["PROCEDURAL", "CALCULATION"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),
    PracticeItem(
        id=make_practice_uuid("math-frac-a-01"),
        skill_id="MATH_FRAC_DEC",
        subject="Mathematics",
        grade_band="middle",
        difficulty_band=DifficultyBand.ADVANCED,
        question_type=QuestionType.MCQ,
        prompt="Convert 0.625 into an irreducible fraction.",
        options=["5/8", "625/100", "3/5", "7/12"],
        correct_answer="5/8",
        explanation="0.625 = 625/1000. Dividing both by 125 yields 5/8.",
        hints=[
            "Write 0.625 as 625 / 1000.",
            "Divide top and bottom by their common factor 125."
        ],
        target_mistake_types=["PROCEDURAL"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),

    # ═════════════════════════════════════════════════════════════════════════
    # 3. CLASS 8 PHYSICS / FORCES — NEWTON'S LAWS (PHY_NEWTON_LAWS)
    # ═════════════════════════════════════════════════════════════════════════
    PracticeItem(
        id=make_practice_uuid("sci-force-f-01"),
        skill_id="PHY_NEWTON_LAWS",
        subject="Physics",
        grade_band="middle",
        difficulty_band=DifficultyBand.FOUNDATIONAL,
        question_type=QuestionType.MCQ,
        prompt="What is the SI unit of force?",
        options=["Newton", "Joule", "Watt", "Pascal"],
        correct_answer="Newton",
        explanation="The SI unit of force is the Newton (N), named after Sir Isaac Newton.",
        hints=[
            "Think of the scientist famous for gravity and laws of motion.",
            "It is abbreviated as N."
        ],
        target_mistake_types=["MEMORY_RECALL"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),
    PracticeItem(
        id=make_practice_uuid("sci-force-s-01"),
        skill_id="PHY_NEWTON_LAWS",
        subject="Physics",
        grade_band="middle",
        difficulty_band=DifficultyBand.STANDARD,
        question_type=QuestionType.MCQ,
        prompt="Two forces of 15 N and 10 N act on an object in opposite directions along a straight line. What is the net force?",
        options=["5 N in the direction of the 15 N force", "25 N in the direction of the 15 N force", "5 N in the direction of the 10 N force", "0 N"],
        correct_answer="5 N in the direction of the 15 N force",
        explanation="Since opposite forces oppose each other, subtract magnitudes: 15 N - 10 N = 5 N along the larger force.",
        hints=[
            "Forces in opposite directions subtract from one another.",
            "Net force = 15 - 10 in the direction of the larger force."
        ],
        target_mistake_types=["CONCEPTUAL", "SIGN_OR_NOTATION"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),
    PracticeItem(
        id=make_practice_uuid("sci-force-a-01"),
        skill_id="PHY_NEWTON_LAWS",
        subject="Physics",
        grade_band="middle",
        difficulty_band=DifficultyBand.ADVANCED,
        question_type=QuestionType.NUMERIC,
        prompt="A constant net force causes a mass of 4 kg to accelerate at 3 m/s². What is the magnitude of the force in Newtons?",
        options=[],
        correct_answer="12",
        explanation="From Newton's second law, F = m * a = 4 kg * 3 m/s² = 12 N.",
        hints=[
            "Use Newton's Second Law: Force = mass × acceleration.",
            "Multiply mass (4) by acceleration (3)."
        ],
        target_mistake_types=["FORMULA_RECALL", "CALCULATION"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),

    # ═════════════════════════════════════════════════════════════════════════
    # 3B. CLASS 8 SCIENCE — STATES OF MATTER (SCI_MATTER_STATES)
    # ═════════════════════════════════════════════════════════════════════════
    PracticeItem(
        id=make_practice_uuid("sci-matter-f-01"),
        skill_id="SCI_MATTER_STATES",
        subject="Science",
        grade_band="middle",
        difficulty_band=DifficultyBand.FOUNDATIONAL,
        question_type=QuestionType.MCQ,
        prompt="Which state of matter has a definite volume but takes the shape of its container?",
        options=["Liquid", "Solid", "Gas", "Plasma"],
        correct_answer="Liquid",
        explanation="Liquids have a definite volume but no fixed shape, adopting the shape of their container.",
        hints=[
            "Think of water poured into a glass.",
            "It flows and has fixed volume."
        ],
        target_mistake_types=["MEMORY_RECALL"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),
    PracticeItem(
        id=make_practice_uuid("sci-matter-s-01"),
        skill_id="SCI_MATTER_STATES",
        subject="Science",
        grade_band="middle",
        difficulty_band=DifficultyBand.STANDARD,
        question_type=QuestionType.MCQ,
        prompt="What is the phase transition called when a solid changes directly into a gas without melting into a liquid?",
        options=["Sublimation", "Evaporation", "Condensation", "Deposition"],
        correct_answer="Sublimation",
        explanation="Sublimation is the transition directly from solid phase to gaseous phase (e.g., dry ice, camphor).",
        hints=[
            "Dry ice turns directly into fog/gas.",
            "The term starts with 'Sub-'."
        ],
        target_mistake_types=["CONCEPTUAL"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),
    PracticeItem(
        id=make_practice_uuid("sci-matter-a-01"),
        skill_id="SCI_MATTER_STATES",
        subject="Science",
        grade_band="middle",
        difficulty_band=DifficultyBand.ADVANCED,
        question_type=QuestionType.MCQ,
        prompt="Why does the temperature of a pure substance remain constant during boiling even though heat is continuously supplied?",
        options=[
            "Heat is used as latent heat to overcome intermolecular attraction",
            "The thermometer stops working at 100°C",
            "The surrounding air cools down the boiling container instantly",
            "The liquid loses mass so temperature cannot rise"
        ],
        correct_answer="Heat is used as latent heat to overcome intermolecular attraction",
        explanation="During a phase transition, added thermal energy is consumed as latent heat of vaporization to break intermolecular bonds rather than increasing kinetic energy.",
        hints=[
            "Consider latent heat of vaporization.",
            "Energy breaks bonds between molecules instead of increasing temperature."
        ],
        target_mistake_types=["CONCEPTUAL", "REASONING"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),

    # ═════════════════════════════════════════════════════════════════════════
    # 4. CLASS 10 MATHEMATICS — LINEAR EQUATIONS (MATH_LIN_EQ)
    # ═════════════════════════════════════════════════════════════════════════
    PracticeItem(
        id=make_practice_uuid("math-lin-f-01"),
        skill_id="MATH_LIN_EQ",
        subject="Mathematics",
        grade_band="secondary",
        difficulty_band=DifficultyBand.FOUNDATIONAL,
        question_type=QuestionType.MCQ,
        prompt="Solve for x: 2x - 6 = 10",
        options=["8", "2", "4", "16"],
        correct_answer="8",
        explanation="Add 6 to both sides: 2x = 16. Divide by 2: x = 8.",
        hints=[
            "Add 6 to both sides to isolate the 2x term.",
            "2x = 16. Now divide both sides by 2."
        ],
        target_mistake_types=["SIGN_OR_NOTATION", "PROCEDURAL"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),
    PracticeItem(
        id=make_practice_uuid("math-lin-s-sign-01"),
        skill_id="MATH_LIN_EQ",
        subject="Mathematics",
        grade_band="secondary",
        difficulty_band=DifficultyBand.STANDARD,
        question_type=QuestionType.MCQ,
        prompt="Solve for x: 5 - 3x = 14",
        options=["-3", "3", "-19/3", "19/3"],
        correct_answer="-3",
        explanation="Subtract 5 from both sides: -3x = 14 - 5 = 9. Divide by -3: x = 9 / (-3) = -3.",
        hints=[
            "Subtract 5 from both sides: -3x = 9.",
            "Careful with the negative sign! Divide 9 by -3."
        ],
        target_mistake_types=["SIGN_OR_NOTATION"],  # Targeted for sign error repair! (§9)
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),
    PracticeItem(
        id=make_practice_uuid("math-lin-a-01"),
        skill_id="MATH_LIN_EQ",
        subject="Mathematics",
        grade_band="secondary",
        difficulty_band=DifficultyBand.ADVANCED,
        question_type=QuestionType.MCQ,
        prompt="For what value of k will the system 2x + ky = 4 and 4x + 6y = 8 have infinitely many solutions?",
        options=["3", "6", "2", "-3"],
        correct_answer="3",
        explanation="For coincident lines, a1/a2 = b1/b2 = c1/c2. Here 2/4 = k/6 = 4/8 = 1/2. Thus k/6 = 1/2 => k = 3.",
        hints=[
            "Infinitely many solutions occur when both lines are coincident: a1/a2 = b1/b2 = c1/c2.",
            "Compare coefficients: 2/4 = k/6."
        ],
        target_mistake_types=["CONCEPTUAL", "PROCEDURAL"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),

    # ═════════════════════════════════════════════════════════════════════════
    # 5. CLASS 10 MATHEMATICS — QUADRATIC EQUATIONS (MATH_QUAD_EQ)
    # ═════════════════════════════════════════════════════════════════════════
    PracticeItem(
        id=make_practice_uuid("math-quad-f-01"),
        skill_id="MATH_QUAD_EQ",
        subject="Mathematics",
        grade_band="secondary",
        difficulty_band=DifficultyBand.FOUNDATIONAL,
        question_type=QuestionType.MCQ,
        prompt="What are the roots of the quadratic equation x² - 9 = 0?",
        options=["3 and -3", "3 only", "-3 only", "9 and -9"],
        correct_answer="3 and -3",
        explanation="x² = 9 => x = ±√9 = ±3.",
        hints=[
            "Add 9 to both sides: x² = 9.",
            "Remember that both positive and negative square roots satisfy x² = 9."
        ],
        target_mistake_types=["SIGN_OR_NOTATION", "CONCEPTUAL"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),
    PracticeItem(
        id=make_practice_uuid("math-quad-s-01"),
        skill_id="MATH_QUAD_EQ",
        subject="Mathematics",
        grade_band="secondary",
        difficulty_band=DifficultyBand.STANDARD,
        question_type=QuestionType.MCQ,
        prompt="Find the roots of x² - 5x + 6 = 0 by factoring.",
        options=["2 and 3", "-2 and -3", "1 and 6", "-1 and -6"],
        correct_answer="2 and 3",
        explanation="Factoring: (x - 2)(x - 3) = 0 => x = 2 or x = 3.",
        hints=[
            "Find two numbers that multiply to +6 and add to -5.",
            "The numbers are -2 and -3: (x - 2)(x - 3) = 0."
        ],
        target_mistake_types=["PROCEDURAL", "SIGN_OR_NOTATION"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),
    PracticeItem(
        id=make_practice_uuid("math-quad-a-01"),
        skill_id="MATH_QUAD_EQ",
        subject="Mathematics",
        grade_band="secondary",
        difficulty_band=DifficultyBand.ADVANCED,
        question_type=QuestionType.MCQ,
        prompt="What is the nature of the roots of the quadratic equation 2x² - 4x + 3 = 0?",
        options=["No real roots (complex conjugates)", "Two equal real roots", "Two distinct real roots", "Infinite roots"],
        correct_answer="No real roots (complex conjugates)",
        explanation="Discriminant Δ = b² - 4ac = (-4)² - 4(2)(3) = 16 - 24 = -8 < 0. Thus no real roots exist.",
        hints=[
            "Calculate the discriminant Δ = b² - 4ac.",
            "b² = 16, 4ac = 24. Since 16 - 24 < 0, check the root condition."
        ],
        target_mistake_types=["CONCEPTUAL", "FORMULA_RECALL"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),

    # ═════════════════════════════════════════════════════════════════════════
    # 6. CLASS 11 JEE PHYSICS — ELECTROSTATICS (PHY_ELECTROSTATICS)
    # ═════════════════════════════════════════════════════════════════════════
    PracticeItem(
        id=make_practice_uuid("jee-elec-f-01"),
        skill_id="PHY_ELECTROSTATICS",
        subject="Physics",
        grade_band="senior_secondary",
        difficulty_band=DifficultyBand.FOUNDATIONAL,
        question_type=QuestionType.MCQ,
        prompt="If the distance between two point charges is doubled, what happens to the electrostatic force between them?",
        options=["Decreases to 1/4 of original", "Halves (1/2)", "Doubles (2x)", "Decreases to 1/8"],
        correct_answer="Decreases to 1/4 of original",
        explanation="By Coulomb's law, F ∝ 1/r². When r -> 2r, F -> F / 2² = F/4.",
        hints=[
            "Recall Coulomb's inverse square law: F is proportional to 1/r².",
            "Square the factor of 2 in the denominator."
        ],
        target_mistake_types=["CONCEPTUAL", "FORMULA_RECALL"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),
    PracticeItem(
        id=make_practice_uuid("jee-elec-s-01"),
        skill_id="PHY_ELECTROSTATICS",
        subject="Physics",
        grade_band="senior_secondary",
        difficulty_band=DifficultyBand.STANDARD,
        question_type=QuestionType.MCQ,
        prompt="What is the electric field at the midpoint between two equal and opposite charges +q and -q separated by distance 2d?",
        options=["2kq / d² pointing towards -q", "0", "kq / d² pointing towards +q", "4kq / d² pointing towards +q"],
        correct_answer="2kq / d² pointing towards -q",
        explanation="At midpoint, field from +q is kq/d² towards -q. Field from -q is kq/d² towards -q. Vector sum = 2kq/d² towards -q.",
        hints=[
            "Determine the direction of the electric field caused by +q at the midpoint.",
            "Determine the direction of the field caused by -q. Note they point in the SAME direction."
        ],
        target_mistake_types=["CONCEPTUAL", "SIGN_OR_NOTATION"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),
    PracticeItem(
        id=make_practice_uuid("jee-elec-a-01"),
        skill_id="PHY_ELECTROSTATICS",
        subject="Physics",
        grade_band="senior_secondary",
        difficulty_band=DifficultyBand.ADVANCED,
        question_type=QuestionType.MCQ,
        prompt="A parallel-plate capacitor with air between plates has capacitance C. If a dielectric of constant k=4 is inserted filling half the gap between plates (series configuration), what is the new capacitance?",
        options=["(8/5) C", "2 C", "(5/8) C", "4 C"],
        correct_answer="(8/5) C",
        explanation="Two capacitors in series of thickness d/2: C1 = 2ε0A/d = 2C, C2 = 2kε0A/d = 8C. C_eq = (2C * 8C)/(2C + 8C) = 16C/10 = (8/5)C.",
        hints=[
            "Treat the setup as two capacitors in series, each having plate separation d/2.",
            "One has air (k=1) and capacitance 2C; the other has dielectric (k=4) and capacitance 8C."
        ],
        target_mistake_types=["PROCEDURAL", "CONCEPTUAL"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),

    # ═════════════════════════════════════════════════════════════════════════
    # 7. CLASS 12 NEET BIOLOGY — GENETICS (BIO_GENETICS)
    # ═════════════════════════════════════════════════════════════════════════
    PracticeItem(
        id=make_practice_uuid("neet-gen-f-01"),
        skill_id="BIO_GENETICS",
        subject="Biology",
        grade_band="senior_secondary",
        difficulty_band=DifficultyBand.FOUNDATIONAL,
        question_type=QuestionType.MCQ,
        prompt="What is the expected phenotypic ratio in the F2 generation of a classic Mendelian monohybrid cross?",
        options=["3:1", "1:2:1", "9:3:3:1", "1:1"],
        correct_answer="3:1",
        explanation="In a monohybrid cross between heterozygotes (Tt x Tt), 3 display dominant phenotype and 1 displays recessive.",
        hints=[
            "Distinguish phenotypic (visible traits) from genotypic (gene alleles).",
            "Dominant to recessive ratio is 3 to 1."
        ],
        target_mistake_types=["MEMORY_RECALL", "CONCEPTUAL"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),
    PracticeItem(
        id=make_practice_uuid("neet-gen-s-01"),
        skill_id="BIO_GENETICS",
        subject="Biology",
        grade_band="senior_secondary",
        difficulty_band=DifficultyBand.STANDARD,
        question_type=QuestionType.MCQ,
        prompt="A cross between a homozygous red-flowered plant (RR) and homozygous white-flowered plant (rr) produces all pink flowers in F1. This phenomenon is an example of:",
        options=["Incomplete dominance", "Co-dominance", "Pleiotropy", "Polygenic inheritance"],
        correct_answer="Incomplete dominance",
        explanation="In incomplete dominance, neither allele is completely dominant, resulting in an intermediate blended phenotype (pink).",
        hints=[
            "Notice that neither parent trait completely masks the other.",
            "The heterozygous offspring show an intermediate blend."
        ],
        target_mistake_types=["CONCEPTUAL"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),
    PracticeItem(
        id=make_practice_uuid("neet-gen-a-01"),
        skill_id="BIO_GENETICS",
        subject="Biology",
        grade_band="senior_secondary",
        difficulty_band=DifficultyBand.ADVANCED,
        question_type=QuestionType.MCQ,
        prompt="In a dihybrid test cross between AaBb and aabb, what is the expected phenotypic ratio assuming independent assortment?",
        options=["1:1:1:1", "9:3:3:1", "1:2:1", "3:1"],
        correct_answer="1:1:1:1",
        explanation="A test cross of a double heterozygote (AaBb) with a double recessive tester (aabb) yields four offspring types in equal frequency (1:1:1:1).",
        hints=[
            "Remember that this is a TEST cross (crossing with homozygous recessive aabb), not an F1 self-cross.",
            "Each of the 4 gametes from AaBb pairs with ab, giving 4 equal classes."
        ],
        target_mistake_types=["MISREAD_QUESTION", "CONCEPTUAL"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),

    # ═════════════════════════════════════════════════════════════════════════
    # 8. CHEMISTRY — CHEMICAL BONDING (CHEM_BONDING)
    # ═════════════════════════════════════════════════════════════════════════
    PracticeItem(
        id=make_practice_uuid("chem-bond-f-01"),
        skill_id="CHEM_BONDING",
        subject="Chemistry",
        grade_band="secondary",
        difficulty_band=DifficultyBand.FOUNDATIONAL,
        question_type=QuestionType.MCQ,
        prompt="Which type of chemical bond is formed by the sharing of electron pairs between two atoms?",
        options=["Covalent bond", "Ionic bond", "Metallic bond", "Hydrogen bond"],
        correct_answer="Covalent bond",
        explanation="A covalent bond consists of the mutual sharing of one or more pairs of electrons between two nonmetal atoms.",
        hints=[
            "Sharing electrons vs transferring electrons.",
            "Covalent means co-valence of electrons."
        ],
        target_mistake_types=["MEMORY_RECALL"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),
    PracticeItem(
        id=make_practice_uuid("chem-bond-s-01"),
        skill_id="CHEM_BONDING",
        subject="Chemistry",
        grade_band="senior_secondary",
        difficulty_band=DifficultyBand.STANDARD,
        question_type=QuestionType.MCQ,
        prompt="According to VSEPR theory, what is the geometric shape of a water molecule (H₂O)?",
        options=["Bent (V-shaped)", "Linear", "Tetrahedral", "Trigonal planar"],
        correct_answer="Bent (V-shaped)",
        explanation="Oxygen has 2 bonding pairs and 2 lone pairs. The electron geometry is tetrahedral, but the molecular geometry is bent (approx 104.5°).",
        hints=[
            "Oxygen has 2 lone pairs of electrons in addition to the 2 single bonds.",
            "The lone pair repulsion pushes the hydrogen atoms into an angle."
        ],
        target_mistake_types=["CONCEPTUAL"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),
    PracticeItem(
        id=make_practice_uuid("chem-bond-a-01"),
        skill_id="CHEM_BONDING",
        subject="Chemistry",
        grade_band="senior_secondary",
        difficulty_band=DifficultyBand.ADVANCED,
        question_type=QuestionType.MCQ,
        prompt="What is the hybridization of the central sulfur atom in sulfur hexafluoride (SF₆)?",
        options=["sp³d²", "sp³d", "sp³", "dsp²"],
        correct_answer="sp³d²",
        explanation="Sulfur in SF₆ has 6 bonding pairs and 0 lone pairs (steric number 6), requiring sp³d² hybridization with octahedral geometry.",
        hints=[
            "Count the steric number: 6 bond pairs + 0 lone pairs = 6.",
            "6 hybrid orbitals require 1 s + 3 p + 2 d orbitals."
        ],
        target_mistake_types=["CONCEPTUAL", "FORMULA_RECALL"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),

    # ═════════════════════════════════════════════════════════════════════════
    # 9. UNDERGRADUATE COMPUTER SCIENCE — DATA STRUCTURES & LOGIC
    # ═════════════════════════════════════════════════════════════════════════
    PracticeItem(
        id=make_practice_uuid("cs-ds-f-01"),
        skill_id="CS_DATA_STRUCT",
        subject="Computer Science",
        grade_band="ug",
        difficulty_band=DifficultyBand.FOUNDATIONAL,
        question_type=QuestionType.MCQ,
        prompt="Which data structure operates on a First-In, First-Out (FIFO) principle?",
        options=["Queue", "Stack", "Binary Search Tree", "Max Heap"],
        correct_answer="Queue",
        explanation="A Queue operates on FIFO (First-In, First-Out), where the earliest inserted element is dequeued first.",
        hints=[
            "Think of a line of people waiting at a counter.",
            "The first person in line is served first."
        ],
        target_mistake_types=["CONCEPTUAL", "MEMORY_RECALL"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),
    PracticeItem(
        id=make_practice_uuid("cs-ds-s-01"),
        skill_id="CS_DATA_STRUCT",
        subject="Computer Science",
        grade_band="ug",
        difficulty_band=DifficultyBand.STANDARD,
        question_type=QuestionType.MCQ,
        prompt="In a singly linked list, what is the time complexity of deleting a node given only a pointer to that node (without previous pointer)?",
        options=["O(1) by copying data from the next node", "O(n) strictly", "O(log n)", "Cannot be deleted under any circumstance"],
        correct_answer="O(1) by copying data from the next node",
        explanation="Provided the node is not the tail, one can copy `node.next.data` into `node` and bypass `node.next` in O(1) time.",
        hints=[
            "Consider whether you can copy the contents of the successor node.",
            "Overwriting value with next node's value allows bypassing in constant time."
        ],
        target_mistake_types=["REASONING", "CONCEPTUAL"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),
    PracticeItem(
        id=make_practice_uuid("cs-ds-a-01"),
        skill_id="CS_DATA_STRUCT",
        subject="Computer Science",
        grade_band="ug",
        difficulty_band=DifficultyBand.ADVANCED,
        question_type=QuestionType.MCQ,
        prompt="Floyd's Cycle-Finding Algorithm (tortoise and hare) detects a cycle in a linked list in what time and auxiliary space complexity?",
        options=["O(n) time and O(1) space", "O(n log n) time and O(n) space", "O(n) time and O(n) space", "O(n²) time and O(1) space"],
        correct_answer="O(n) time and O(1) space",
        explanation="Floyd's algorithm uses two pointers advancing at speeds 1 and 2, guaranteeing meeting in O(n) steps with zero additional heap memory (O(1)).",
        hints=[
            "The algorithm requires only two pointer variables.",
            "Both pointers traverse the list, meeting in at most n steps."
        ],
        target_mistake_types=["CONCEPTUAL"],
        provenance=ProvenanceType.CURATED,
        verification_status=VerificationStatus.VERIFIED,
    ),
]

_PRACTICE_ITEMS_BY_ID: Dict[str, PracticeItem] = {it.id: it for it in CANONICAL_PRACTICE_ITEMS}
_PRACTICE_ITEMS_BY_SKILL: Dict[str, List[PracticeItem]] = {}
for it in CANONICAL_PRACTICE_ITEMS:
    _PRACTICE_ITEMS_BY_SKILL.setdefault(it.skill_id, []).append(it)


def get_practice_item(item_id: str) -> Optional[PracticeItem]:
    return _PRACTICE_ITEMS_BY_ID.get(item_id)


def get_practice_items_for_skill(skill_id: str) -> List[PracticeItem]:
    return list(_PRACTICE_ITEMS_BY_SKILL.get(skill_id, []))


def get_all_practice_items() -> List[PracticeItem]:
    return list(CANONICAL_PRACTICE_ITEMS)


def register_practice_item(item: PracticeItem) -> None:
    _PRACTICE_ITEMS_BY_ID[item.id] = item
    _PRACTICE_ITEMS_BY_SKILL.setdefault(item.skill_id, []).append(item)
    if not any(it.id == item.id for it in CANONICAL_PRACTICE_ITEMS):
        CANONICAL_PRACTICE_ITEMS.append(item)
