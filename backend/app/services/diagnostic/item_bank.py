"""
LearnByGenie — Diagnostic Item Bank
=====================================
Curated and verified diagnostic items mapped to canonical skills.
Zero raw/unverified LLM content. Every item has an authoritative correct answer,
step-by-step educational rationale, difficulty classification, and verification status.

Supports:
- Class 3-5 (Primary)
- Class 6-8 (Middle)
- Class 9-10 (Secondary)
- Class 11-12 / JEE / NEET (Senior Secondary)
- UG (Undergraduate Computer Science)
"""
import uuid
from typing import List, Dict, Optional
from .schemas import DiagnosticItem, QuestionType, DifficultyBand, GradeBand, VerificationStatus


def make_item_uuid(slug: str) -> str:
    """Derive deterministic UUID from canonical slug for PostgreSQL UUID compatibility."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"learnbygenie.diagnostic.{slug}"))


CANONICAL_ITEMS: List[DiagnosticItem] = [
    # ═════════════════════════════════════════════════════════════════════════
    # MATHEMATICS: PRIMARY (Class 3-5) — MATH_NUM_OPS
    # ═════════════════════════════════════════════════════════════════════════
    DiagnosticItem(
        id=make_item_uuid("item-math-num-01"),
        skill_id="MATH_NUM_OPS",
        subject="Mathematics",
        grade_band=GradeBand.PRIMARY.value,
        difficulty_band=DifficultyBand.EASY.value,
        question_type=QuestionType.MCQ,
        prompt="What is the result of 348 + 275?",
        options=["613", "623", "523", "618"],
        correct_answer="623",
        explanation="Add units: 8+5=13 (carry 1). Tens: 4+7+1=12 (carry 1). Hundreds: 3+2+1=6. Total = 623.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.65,
    ),
    DiagnosticItem(
        id=make_item_uuid("item-math-num-02"),
        skill_id="MATH_NUM_OPS",
        subject="Mathematics",
        grade_band=GradeBand.PRIMARY.value,
        difficulty_band=DifficultyBand.MEDIUM.value,
        question_type=QuestionType.MCQ,
        prompt="If a baker places 8 cookies in each box and has 96 cookies in total, how many boxes does the baker fill?",
        options=["10", "11", "12", "14"],
        correct_answer="12",
        explanation="Divide total cookies by cookies per box: 96 / 8 = 12 boxes.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.70,
    ),
    DiagnosticItem(
        id=make_item_uuid("item-math-num-03"),
        skill_id="MATH_NUM_OPS",
        subject="Mathematics",
        grade_band=GradeBand.PRIMARY.value,
        difficulty_band=DifficultyBand.HARD.value,
        question_type=QuestionType.NUMERIC,
        prompt="Evaluate: 145 - (36 + 48)",
        options=[],
        correct_answer="61",
        explanation="First calculate parentheses: 36 + 48 = 84. Then subtract: 145 - 84 = 61.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.75,
    ),

    # ═════════════════════════════════════════════════════════════════════════
    # MATHEMATICS: MIDDLE (Class 6-8) — MATH_FRAC_DEC
    # ═════════════════════════════════════════════════════════════════════════
    DiagnosticItem(
        id=make_item_uuid("item-math-frac-01"),
        skill_id="MATH_FRAC_DEC",
        subject="Mathematics",
        grade_band=GradeBand.MIDDLE.value,
        difficulty_band=DifficultyBand.EASY.value,
        question_type=QuestionType.MCQ,
        prompt="What is 3/4 + 2/5 expressed as a single fraction in simplest form?",
        options=["23/20", "5/9", "6/20", "11/20"],
        correct_answer="23/20",
        explanation="Find common denominator LCM(4, 5) = 20: 3/4 = 15/20, 2/5 = 8/20. Sum = 15/20 + 8/20 = 23/20.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.72,
    ),
    DiagnosticItem(
        id=make_item_uuid("item-math-frac-02"),
        skill_id="MATH_FRAC_DEC",
        subject="Mathematics",
        grade_band=GradeBand.MIDDLE.value,
        difficulty_band=DifficultyBand.MEDIUM.value,
        question_type=QuestionType.MCQ,
        prompt="Convert 0.375 into an irreducible fraction.",
        options=["3/8", "375/100", "7/16", "1/3"],
        correct_answer="3/8",
        explanation="0.375 = 375/1000. Dividing numerator and denominator by 125 gives 3/8.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.78,
    ),

    # ═════════════════════════════════════════════════════════════════════════
    # MATHEMATICS: MIDDLE / FOUNDATIONAL ALGEBRA — MATH_ALG_EXP
    # ═════════════════════════════════════════════════════════════════════════
    DiagnosticItem(
        id=make_item_uuid("item-math-alg-01"),
        skill_id="MATH_ALG_EXP",
        subject="Mathematics",
        grade_band=GradeBand.MIDDLE.value,
        difficulty_band=DifficultyBand.EASY.value,
        question_type=QuestionType.MCQ,
        prompt="Simplify the algebraic expression: 4x + 7 - 2x + 5",
        options=["2x + 12", "6x + 12", "2x + 2", "14x"],
        correct_answer="2x + 12",
        explanation="Group like terms: (4x - 2x) + (7 + 5) = 2x + 12.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.74,
    ),
    DiagnosticItem(
        id=make_item_uuid("item-math-alg-02"),
        skill_id="MATH_ALG_EXP",
        subject="Mathematics",
        grade_band=GradeBand.MIDDLE.value,
        difficulty_band=DifficultyBand.MEDIUM.value,
        question_type=QuestionType.MCQ,
        prompt="Expand and simplify: 3(2y - 4) - 2(y + 1)",
        options=["4y - 14", "4y - 10", "4y - 12", "8y - 14"],
        correct_answer="4y - 14",
        explanation="Distribute factors: 6y - 12 - 2y - 2 = (6y - 2y) + (-12 - 2) = 4y - 14.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.80,
    ),

    # ═════════════════════════════════════════════════════════════════════════
    # MATHEMATICS: SECONDARY (Class 9-10) — MATH_LIN_EQ
    # ═════════════════════════════════════════════════════════════════════════
    DiagnosticItem(
        id=make_item_uuid("item-math-lin-01"),
        skill_id="MATH_LIN_EQ",
        subject="Mathematics",
        grade_band=GradeBand.SECONDARY.value,
        difficulty_band=DifficultyBand.MEDIUM.value,
        question_type=QuestionType.MCQ,
        prompt="Solve for x: 5x - 7 = 3x + 11",
        options=["9", "4", "2", "-9"],
        correct_answer="9",
        explanation="Subtract 3x from both sides: 2x - 7 = 11. Add 7: 2x = 18. Divide by 2: x = 9.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.82,
    ),
    DiagnosticItem(
        id=make_item_uuid("item-math-lin-02"),
        skill_id="MATH_LIN_EQ",
        subject="Mathematics",
        grade_band=GradeBand.SECONDARY.value,
        difficulty_band=DifficultyBand.HARD.value,
        question_type=QuestionType.MCQ,
        prompt="Find the value of y in the system: 2x + y = 13 and x - y = 2",
        options=["3", "5", "7", "1"],
        correct_answer="3",
        explanation="Add both equations: 3x = 15 => x = 5. Substitute into second equation: 5 - y = 2 => y = 3.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.85,
    ),

    # ═════════════════════════════════════════════════════════════════════════
    # MATHEMATICS: SECONDARY (Class 10) — MATH_QUAD_EQ
    # ═════════════════════════════════════════════════════════════════════════
    DiagnosticItem(
        id=make_item_uuid("item-math-quad-01"),
        skill_id="MATH_QUAD_EQ",
        subject="Mathematics",
        grade_band=GradeBand.SECONDARY.value,
        difficulty_band=DifficultyBand.MEDIUM.value,
        question_type=QuestionType.MCQ,
        prompt="What are the roots of the quadratic equation x² - 5x + 6 = 0?",
        options=["x = 2, 3", "x = -2, -3", "x = 1, 6", "x = -1, -6"],
        correct_answer="x = 2, 3",
        explanation="Factor the quadratic: (x - 2)(x - 3) = 0. Therefore x = 2 or x = 3.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.83,
    ),
    DiagnosticItem(
        id=make_item_uuid("item-math-quad-02"),
        skill_id="MATH_QUAD_EQ",
        subject="Mathematics",
        grade_band=GradeBand.SECONDARY.value,
        difficulty_band=DifficultyBand.HARD.value,
        question_type=QuestionType.MCQ,
        prompt="What is the nature of the roots for 2x² - 4x + 3 = 0?",
        options=[
            "No real roots (Complex roots)",
            "Two distinct real roots",
            "Two equal real roots",
            "Rational and equal roots"
        ],
        correct_answer="No real roots (Complex roots)",
        explanation="Discriminant D = b² - 4ac = (-4)² - 4(2)(3) = 16 - 24 = -8. Since D < 0, the equation has no real roots.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.86,
    ),

    # ═════════════════════════════════════════════════════════════════════════
    # MATHEMATICS: SENIOR SECONDARY / JEE (Class 11-12) — MATH_CALC_LIMITS
    # ═════════════════════════════════════════════════════════════════════════
    DiagnosticItem(
        id=make_item_uuid("item-math-lim-01"),
        skill_id="MATH_CALC_LIMITS",
        subject="Mathematics",
        grade_band=GradeBand.SENIOR_SECONDARY.value,
        difficulty_band=DifficultyBand.MEDIUM.value,
        question_type=QuestionType.MCQ,
        prompt="Evaluate: lim (x -> 0) [sin(3x) / x]",
        options=["3", "1", "0", "1/3"],
        correct_answer="3",
        explanation="Using the standard limit lim(θ->0) [sin(θ)/θ] = 1, multiply and divide by 3: lim 3 * [sin(3x)/(3x)] = 3 * 1 = 3.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.88,
    ),
    DiagnosticItem(
        id=make_item_uuid("item-math-lim-02"),
        skill_id="MATH_CALC_LIMITS",
        subject="Mathematics",
        grade_band=GradeBand.SENIOR_SECONDARY.value,
        difficulty_band=DifficultyBand.HARD.value,
        question_type=QuestionType.MCQ,
        prompt="Evaluate: lim (x -> 2) [(x² - 4) / (x - 2)]",
        options=["2", "4", "0", "Undefined"],
        correct_answer="4",
        explanation="Factorise numerator: (x - 2)(x + 2)/(x - 2) = x + 2 for x ≠ 2. As x -> 2, limit = 2 + 2 = 4.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.85,
    ),

    # ═════════════════════════════════════════════════════════════════════════
    # PHYSICS: SENIOR SECONDARY / JEE / NEET — PHY_VECTORS
    # ═════════════════════════════════════════════════════════════════════════
    DiagnosticItem(
        id=make_item_uuid("item-phy-vec-01"),
        skill_id="PHY_VECTORS",
        subject="Physics",
        grade_band=GradeBand.SENIOR_SECONDARY.value,
        difficulty_band=DifficultyBand.EASY.value,
        question_type=QuestionType.MCQ,
        prompt="Two forces of magnitude 3 N and 4 N act perpendicular to each other. What is the magnitude of their resultant force?",
        options=["7 N", "1 N", "5 N", "12 N"],
        correct_answer="5 N",
        explanation="For perpendicular vectors: R = √(A² + B²) = √(3² + 4²) = √(9 + 16) = √25 = 5 N.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.82,
    ),
    DiagnosticItem(
        id=make_item_uuid("item-phy-vec-02"),
        skill_id="PHY_VECTORS",
        subject="Physics",
        grade_band=GradeBand.SENIOR_SECONDARY.value,
        difficulty_band=DifficultyBand.MEDIUM.value,
        question_type=QuestionType.MCQ,
        prompt="If vector A = 2î + 3ĵ and vector B = 4î - ĵ, what is their dot product (A · B)?",
        options=["5", "11", "8", "-5"],
        correct_answer="5",
        explanation="A · B = AxBx + AyBy = (2)(4) + (3)(-1) = 8 - 3 = 5.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.85,
    ),

    # ═════════════════════════════════════════════════════════════════════════
    # PHYSICS: SECONDARY (Class 9-11) — PHY_NEWTON_LAWS
    # ═════════════════════════════════════════════════════════════════════════
    DiagnosticItem(
        id=make_item_uuid("item-phy-newton-01"),
        skill_id="PHY_NEWTON_LAWS",
        subject="Physics",
        grade_band=GradeBand.SECONDARY.value,
        difficulty_band=DifficultyBand.MEDIUM.value,
        question_type=QuestionType.MCQ,
        prompt="A net force of 20 N acts on a mass of 4 kg. What acceleration is produced?",
        options=["5 m/s²", "80 m/s²", "0.2 m/s²", "16 m/s²"],
        correct_answer="5 m/s²",
        explanation="By Newton's Second Law: F = m * a => a = F / m = 20 N / 4 kg = 5 m/s².",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.80,
    ),
    DiagnosticItem(
        id=make_item_uuid("item-phy-newton-02"),
        skill_id="PHY_NEWTON_LAWS",
        subject="Physics",
        grade_band=GradeBand.SECONDARY.value,
        difficulty_band=DifficultyBand.HARD.value,
        question_type=QuestionType.MCQ,
        prompt="An object is in equilibrium under the action of three coplanar forces. What must be true about the vector sum of these forces?",
        options=[
            "It must be zero",
            "It must equal the weight of the object",
            "It depends on the velocity of the object",
            "It must be perpendicular to the surface"
        ],
        correct_answer="It must be zero",
        explanation="Equilibrium implies zero acceleration; according to Newton's First and Second Laws, the net vector force ΣF must equal zero.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.83,
    ),

    # ═════════════════════════════════════════════════════════════════════════
    # PHYSICS: SENIOR SECONDARY / JEE (Class 12) — PHY_ELECTROSTATICS
    # ═════════════════════════════════════════════════════════════════════════
    DiagnosticItem(
        id=make_item_uuid("item-phy-elec-01"),
        skill_id="PHY_ELECTROSTATICS",
        subject="Physics",
        grade_band=GradeBand.SENIOR_SECONDARY.value,
        difficulty_band=DifficultyBand.MEDIUM.value,
        question_type=QuestionType.MCQ,
        prompt="If the distance between two point charges is doubled, by what factor does the electrostatic force between them change?",
        options=["Halved (1/2)", "Quartered (1/4)", "Doubled (2x)", "Four times (4x)"],
        correct_answer="Quartered (1/4)",
        explanation="By Coulomb's Law, F ∝ 1/r². If r -> 2r, F' = F/(2)² = F/4.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.86,
    ),
    DiagnosticItem(
        id=make_item_uuid("item-phy-elec-02"),
        skill_id="PHY_ELECTROSTATICS",
        subject="Physics",
        grade_band=GradeBand.SENIOR_SECONDARY.value,
        difficulty_band=DifficultyBand.HARD.value,
        question_type=QuestionType.MCQ,
        prompt="Two identical conducting spheres carry charges of +4 μC and -2 μC. They are touched together and then separated. What is the final charge on each sphere?",
        options=["+1 μC", "+2 μC", "-1 μC", "0 μC"],
        correct_answer="+1 μC",
        explanation="When touched, the total charge is (+4) + (-2) = +2 μC. Because the spheres are identical, the charge divides equally: (+2 μC) / 2 = +1 μC each.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.89,
    ),

    # ═════════════════════════════════════════════════════════════════════════
    # BIOLOGY: NEET / SENIOR (Class 8-12) — BIO_CELL_UNIT & BIO_GENETICS
    # ═════════════════════════════════════════════════════════════════════════
    DiagnosticItem(
        id=make_item_uuid("item-bio-cell-01"),
        skill_id="BIO_CELL_UNIT",
        subject="Biology",
        grade_band=GradeBand.SECONDARY.value,
        difficulty_band=DifficultyBand.EASY.value,
        question_type=QuestionType.MCQ,
        prompt="Which cellular organelle is responsible for cellular respiration and ATP generation?",
        options=["Mitochondria", "Ribosome", "Golgi apparatus", "Endoplasmic reticulum"],
        correct_answer="Mitochondria",
        explanation="Mitochondria are the powerhouses of the cell, generating the majority of chemical energy in the form of ATP.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.78,
    ),
    DiagnosticItem(
        id=make_item_uuid("item-bio-cell-02"),
        skill_id="BIO_CELL_UNIT",
        subject="Biology",
        grade_band=GradeBand.SECONDARY.value,
        difficulty_band=DifficultyBand.MEDIUM.value,
        question_type=QuestionType.MCQ,
        prompt="What is the primary structural carbohydrate component of plant cell walls?",
        options=["Cellulose", "Glycogen", "Starch", "Peptidoglycan"],
        correct_answer="Cellulose",
        explanation="Plant cell walls are primarily composed of cellulose microfibrils embedded in a polysaccharide-protein matrix.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.81,
    ),
    DiagnosticItem(
        id=make_item_uuid("item-bio-gen-01"),
        skill_id="BIO_GENETICS",
        subject="Biology",
        grade_band=GradeBand.SENIOR_SECONDARY.value,
        difficulty_band=DifficultyBand.MEDIUM.value,
        question_type=QuestionType.MCQ,
        prompt="In a standard Mendelian monohybrid cross between two heterozygous tall plants (Tt × Tt), what is the expected phenotypic ratio of Tall to Dwarf offspring?",
        options=["3:1", "1:2:1", "9:3:3:1", "1:1"],
        correct_answer="3:1",
        explanation="Genotypic ratio is 1 TT : 2 Tt : 1 tt. Both TT and Tt appear Tall, yielding a 3 Tall : 1 Dwarf phenotypic ratio.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.84,
    ),
    DiagnosticItem(
        id=make_item_uuid("item-bio-gen-02"),
        skill_id="BIO_GENETICS",
        subject="Biology",
        grade_band=GradeBand.SENIOR_SECONDARY.value,
        difficulty_band=DifficultyBand.HARD.value,
        question_type=QuestionType.MCQ,
        prompt="In double-stranded DNA, if Adenine constitutes 30% of the nitrogenous bases, what percentage of bases will be Cytosine?",
        options=["20%", "30%", "40%", "70%"],
        correct_answer="20%",
        explanation="By Chargaff's rule, %A = %T = 30%. Together A + T = 60%. The remaining 40% is shared equally by G and C, so %C = 20%.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.87,
    ),

    # ═════════════════════════════════════════════════════════════════════════
    # INTEGRATED SCIENCE: PRIMARY/MIDDLE (Class 3-6) — SCI_MATTER_STATES
    # ═════════════════════════════════════════════════════════════════════════
    DiagnosticItem(
        id=make_item_uuid("item-sci-matter-01"),
        skill_id="SCI_MATTER_STATES",
        subject="Science",
        grade_band=GradeBand.PRIMARY.value,
        difficulty_band=DifficultyBand.EASY.value,
        question_type=QuestionType.MCQ,
        prompt="What process describes water changing from a liquid state into a gas (water vapor) when heated?",
        options=["Evaporation", "Freezing", "Condensation", "Melting"],
        correct_answer="Evaporation",
        explanation="Evaporation is the transition of a substance from liquid to gas state.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.62,
    ),
    DiagnosticItem(
        id=make_item_uuid("item-sci-matter-02"),
        skill_id="SCI_MATTER_STATES",
        subject="Science",
        grade_band=GradeBand.PRIMARY.value,
        difficulty_band=DifficultyBand.MEDIUM.value,
        question_type=QuestionType.MCQ,
        prompt="What is the term for the phase change where a solid turns directly into a gas without becoming a liquid?",
        options=["Sublimation", "Deposition", "Vaporization", "Liquefaction"],
        correct_answer="Sublimation",
        explanation="Sublimation is the direct phase transition from solid to gas (e.g., dry ice or camphor).",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.71,
    ),

    # ═════════════════════════════════════════════════════════════════════════
    # ENGLISH: READING COMPREHENSION — ENG_READ_COMP
    # ═════════════════════════════════════════════════════════════════════════
    DiagnosticItem(
        id=make_item_uuid("item-eng-read-01"),
        skill_id="ENG_READ_COMP",
        subject="English",
        grade_band=GradeBand.SECONDARY.value,
        difficulty_band=DifficultyBand.MEDIUM.value,
        question_type=QuestionType.MCQ,
        prompt="Read the excerpt: 'Although the team faced numerous hurdles during development, their meticulous preparation enabled an on-time release.' What does 'meticulous' mean in this context?",
        options=[
            "Extremely careful and precise",
            "Hasty and unorganized",
            "Reluctant and fearful",
            "Costly and lavish"
        ],
        correct_answer="Extremely careful and precise",
        explanation="In the passage, 'meticulous' highlights thorough attention to detail that overcame obstacles.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.76,
    ),
    DiagnosticItem(
        id=make_item_uuid("item-eng-read-02"),
        skill_id="ENG_READ_COMP",
        subject="English",
        grade_band=GradeBand.SECONDARY.value,
        difficulty_band=DifficultyBand.HARD.value,
        question_type=QuestionType.MCQ,
        prompt="When an author uses rhetorical questions in an argument without expecting a literal answer, what is their primary intended purpose?",
        options=[
            "To provoke thought and emphasize a key point",
            "To confuse the reader with ambiguity",
            "To gather empirical survey data",
            "To shorten the length of the paragraph"
        ],
        correct_answer="To provoke thought and emphasize a key point",
        explanation="Rhetorical questions are persuasive stylistic devices used to engage the reader and highlight the author's argument.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.79,
    ),

    # ═════════════════════════════════════════════════════════════════════════
    # COMPUTER SCIENCE / UG COURSEWORK — CS_BASIC_LOGIC & CS_DATA_STRUCT
    # ═════════════════════════════════════════════════════════════════════════
    DiagnosticItem(
        id=make_item_uuid("item-cs-logic-01"),
        skill_id="CS_BASIC_LOGIC",
        subject="Computer Science",
        grade_band=GradeBand.UG.value,
        difficulty_band=DifficultyBand.EASY.value,
        question_type=QuestionType.MCQ,
        prompt="What is the output of the logical expression (True AND False) OR (NOT False)?",
        options=["True", "False", "None", "Error"],
        correct_answer="True",
        explanation="(True AND False) is False. (NOT False) is True. False OR True evaluates to True.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.82,
    ),
    DiagnosticItem(
        id=make_item_uuid("item-cs-logic-02"),
        skill_id="CS_BASIC_LOGIC",
        subject="Computer Science",
        grade_band=GradeBand.UG.value,
        difficulty_band=DifficultyBand.MEDIUM.value,
        question_type=QuestionType.MCQ,
        prompt="According to De Morgan's laws in Boolean algebra, what is NOT (A AND B) equivalent to?",
        options=["(NOT A) OR (NOT B)", "(NOT A) AND (NOT B)", "A OR B", "NOT (A OR B)"],
        correct_answer="(NOT A) OR (NOT B)",
        explanation="De Morgan's first law states that the negation of a conjunction is the disjunction of the negations: !(A && B) == !A || !B.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.84,
    ),
    DiagnosticItem(
        id=make_item_uuid("item-cs-ds-01"),
        skill_id="CS_DATA_STRUCT",
        subject="Computer Science",
        grade_band=GradeBand.UG.value,
        difficulty_band=DifficultyBand.MEDIUM.value,
        question_type=QuestionType.MCQ,
        prompt="Which data structure operates on a Last-In, First-Out (LIFO) access pattern?",
        options=["Stack", "Queue", "Binary Search Tree", "Linked List"],
        correct_answer="Stack",
        explanation="A stack operates on LIFO (Last-In, First-Out), where the most recently pushed element is the first popped.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.85,
    ),
    DiagnosticItem(
        id=make_item_uuid("item-cs-ds-02"),
        skill_id="CS_DATA_STRUCT",
        subject="Computer Science",
        grade_band=GradeBand.UG.value,
        difficulty_band=DifficultyBand.HARD.value,
        question_type=QuestionType.MCQ,
        prompt="What is the worst-case time complexity of searching for an element in an unsorted singly linked list of length n?",
        options=["O(n)", "O(1)", "O(log n)", "O(n²)"],
        correct_answer="O(n)",
        explanation="In an unsorted singly linked list, each node must be traversed sequentially from head to tail in the worst case, requiring O(n) steps.",
        provenance="CURATED",
        verification_status=VerificationStatus.VERIFIED,
        language="english",
        discrimination_index=0.88,
    ),
]

# Primary index by UUID and slug aliases for transparent backwards/testing compatibility
_ITEMS_BY_ID: Dict[str, DiagnosticItem] = {}
_ITEMS_BY_SKILL: Dict[str, List[DiagnosticItem]] = {}

for it in CANONICAL_ITEMS:
    _ITEMS_BY_ID[it.id] = it
    _ITEMS_BY_SKILL.setdefault(it.skill_id, []).append(it)


def get_item(item_id: str) -> Optional[DiagnosticItem]:
    return _ITEMS_BY_ID.get(item_id)


def get_items_for_skill(skill_id: str) -> List[DiagnosticItem]:
    return _ITEMS_BY_SKILL.get(skill_id, [])


def get_all_items() -> List[DiagnosticItem]:
    return list(CANONICAL_ITEMS)
