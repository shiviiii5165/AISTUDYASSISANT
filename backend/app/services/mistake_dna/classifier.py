"""
LearnByGenie — Feature 5: Mistake DNA Classifier Engine
=======================================================
Deterministic error detection authority first, structured rubric classification second.
Does NOT fabricate certainty: uncertain classifications resolve strictly to UNKNOWN.

Core architecture is generic and extensible across Mathematics, Physics, Chemistry,
Biology, and Computer Science (§2, §3, §6, §7).
"""
import re
from typing import Optional, List, Tuple
from app.core.logging import logger
from .schemas import (
    ErrorType, ConfidenceClass, ClassificationResult, MistakeCandidate
)


COMMON_UNITS = [
    "m/s^2", "m/s", "km/h", "cm/s", "kg*m/s", "n*s",
    "m^3", "m^2", "cm^3", "cm^2", "mm", "cm", "m", "km",
    "kg", "g", "mg", "n", "joule", "j", "watt", "w",
    "pascal", "pa", "hz", "rad/s", "deg", "celsius", "kelvin", "k",
    "coulomb", "c", "volt", "v", "ohm", "ampere", "a", "mol"
]


class MistakeClassifier:
    """
    Error Detection Authority (§6).
    Applies deterministic heuristics first before falling back to structured rubrics.
    """
    VERSION = "5.0.0"

    @classmethod
    def classify(cls, candidate: MistakeCandidate) -> ClassificationResult:
        """
        Classifies an error candidate into canonical taxonomy and domain subtype.
        """
        resp_clean = candidate.student_response.strip()
        exp_clean = (candidate.expected_answer or "").strip()
        prompt = (candidate.prompt_text or "").strip()
        feedback = (candidate.feedback_reason or "").strip()

        # ─── 1. DETERMINISTIC HEURISTIC CHECKS ────────────────────────────────

        # A. Incomplete Response Check
        if len(resp_clean) == 0 or resp_clean in ("?", "...", "idk", "i don't know", "skip"):
            return ClassificationResult(
                primary_error_type=ErrorType.INCOMPLETE_RESPONSE,
                error_subtype="unattempted_or_abandoned",
                error_summary="Response was incomplete or abandoned before completing the solution.",
                confidence=ConfidenceClass.HIGH,
                classifier_version=cls.VERSION,
                deterministic_rule="EMPTY_OR_GIVE_UP"
            )

        # B. Unit or Dimension Check
        unit_res = cls._check_unit_error(resp_clean, exp_clean, prompt)
        if unit_res:
            return unit_res

        # C. Sign or Notation Check
        sign_res = cls._check_sign_or_notation_error(resp_clean, exp_clean, prompt, feedback)
        if sign_res:
            return sign_res

        # D. Calculation / Arithmetic Check
        calc_res = cls._check_calculation_error(resp_clean, exp_clean)
        if calc_res:
            return calc_res

        # E. Formula Recall Check
        formula_res = cls._check_formula_recall(resp_clean, exp_clean, prompt, feedback)
        if formula_res:
            return formula_res

        # F. Misread Question Check
        misread_res = cls._check_misread_question(resp_clean, exp_clean, prompt, feedback)
        if misread_res:
            return misread_res

        # ─── 2. STRUCTURED RUBRIC / FEEDBACK REASON CHECKS ────────────────────

        rubric_res = cls._classify_via_rubric(candidate)
        if rubric_res:
            return rubric_res

        # ─── 3. SUBJECT-SPECIFIC FALLBACK PATTERNS ────────────────────────────
        subj_res = cls._check_subject_heuristics(candidate)
        if subj_res:
            return subj_res

        # ─── 4. UNKNOWN CLASSIFICATION (NO FABRICATION §7, §39) ────────────────
        return ClassificationResult(
            primary_error_type=ErrorType.UNKNOWN,
            secondary_error_types=[],
            error_subtype="",
            error_summary="Response mechanism could not be determined with high confidence.",
            confidence=ConfidenceClass.LOW,
            classifier_version=cls.VERSION,
            deterministic_rule="UNCLASSIFIED_FALLBACK"
        )

    # ─── DETERMINISTIC DETECTORS ──────────────────────────────────────────────

    @classmethod
    def _check_unit_error(cls, student: str, expected: str, prompt: str) -> Optional[ClassificationResult]:
        """Detects unit mismatch, missing units, or dimensional slips."""
        stu_lower = student.lower()
        exp_lower = expected.lower()

        # Find units in student and expected
        stu_unit = None
        exp_unit = None

        for u in sorted(COMMON_UNITS, key=len, reverse=True):
            if re.search(r'\b' + re.escape(u) + r'\b', stu_lower) and not stu_unit:
                stu_unit = u
            if re.search(r'\b' + re.escape(u) + r'\b', exp_lower) and not exp_unit:
                exp_unit = u

        # Case 1: Expected had a unit, student had no unit or different unit
        if exp_unit and not stu_unit and re.search(r'\d', student):
            return ClassificationResult(
                primary_error_type=ErrorType.UNIT_OR_DIMENSION,
                error_subtype="missing_unit",
                error_summary=f"Result omitted required physical unit ({exp_unit}).",
                confidence=ConfidenceClass.HIGH,
                classifier_version=cls.VERSION,
                deterministic_rule="UNIT_OMISSION"
            )

        if exp_unit and stu_unit and exp_unit != stu_unit:
            return ClassificationResult(
                primary_error_type=ErrorType.UNIT_OR_DIMENSION,
                error_subtype="unit_mismatch",
                error_summary=f"Unit mismatch: answered in '{stu_unit}' instead of expected '{exp_unit}'.",
                confidence=ConfidenceClass.HIGH,
                classifier_version=cls.VERSION,
                deterministic_rule="UNIT_MISMATCH"
            )

        return None

    @classmethod
    def _check_sign_or_notation_error(
        cls, student: str, expected: str, prompt: str, feedback: str
    ) -> Optional[ClassificationResult]:
        """Detects sign inversion, transposed plus/minus, or coordinate sign flips."""
        # 1. Feedback explicit signal
        if re.search(r'\b(sign\s+error|opposite\s+sign|sign\s+change|negative\s+instead\s+of\s+positive|positive\s+instead\s+of\s+negative)\b', feedback, re.I):
            return ClassificationResult(
                primary_error_type=ErrorType.SIGN_OR_NOTATION,
                error_subtype="sign_transposition",
                error_summary="Sign transposition or negative sign error.",
                confidence=ConfidenceClass.HIGH,
                classifier_version=cls.VERSION,
                deterministic_rule="FEEDBACK_EXPLICIT_SIGN"
            )

        # 2. Pure numerical opposite sign: expected 5, student -5
        s_nums = re.findall(r'[-+]?\d+(?:\.\d+)?', student)
        e_nums = re.findall(r'[-+]?\d+(?:\.\d+)?', expected)

        if len(s_nums) == 1 and len(e_nums) == 1:
            try:
                s_val = float(s_nums[0])
                e_val = float(e_nums[0])
                if s_val != 0 and s_val == -e_val:
                    return ClassificationResult(
                        primary_error_type=ErrorType.SIGN_OR_NOTATION,
                        error_subtype="sign_transposition",
                        error_summary=f"Answer had opposite sign ({s_val} instead of {e_val}).",
                        confidence=ConfidenceClass.HIGH,
                        classifier_version=cls.VERSION,
                        deterministic_rule="NUMERIC_OPPOSITE_SIGN"
                    )
            except ValueError:
                pass

        # 3. Factorization sign flip: (x-2)(x-3) vs (x+2)(x+3)
        if "(" in student and "(" in expected and ("+" in student or "-" in student):
            s_signs = [c for c in student if c in "+-"]
            e_signs = [c for c in expected if c in "+-"]
            if s_signs and e_signs and s_signs != e_signs and len(s_signs) == len(e_signs):
                return ClassificationResult(
                    primary_error_type=ErrorType.SIGN_OR_NOTATION,
                    error_subtype="sign_transposition",
                    error_summary="Signs were flipped during algebraic factorization or transposition.",
                    confidence=ConfidenceClass.HIGH,
                    classifier_version=cls.VERSION,
                    deterministic_rule="FACTOR_SIGN_FLIP"
                )

        return None

    @classmethod
    def _check_calculation_error(cls, student: str, expected: str) -> Optional[ClassificationResult]:
        """Detects arithmetic computation slip when sign and magnitude are close."""
        s_nums = re.findall(r'[-+]?\d+(?:\.\d+)?', student)
        e_nums = re.findall(r'[-+]?\d+(?:\.\d+)?', expected)

        if len(s_nums) == 1 and len(e_nums) == 1:
            try:
                s_val = float(s_nums[0])
                e_val = float(e_nums[0])
                # If they share the same sign and difference is small arithmetic deviation
                if (s_val > 0) == (e_val > 0) and s_val != e_val:
                    diff = abs(s_val - e_val)
                    rel_diff = diff / max(abs(e_val), 1.0)
                    # Off by small arithmetic slip (e.g. 1, 2, or < 25% computational error)
                    if diff <= 2.0 or rel_diff <= 0.25:
                        return ClassificationResult(
                            primary_error_type=ErrorType.CALCULATION,
                            error_subtype="arithmetic_slip",
                            error_summary=f"Minor arithmetic calculation slip (computed {s_val}, expected {e_val}).",
                            confidence=ConfidenceClass.HIGH,
                            classifier_version=cls.VERSION,
                            deterministic_rule="NUMERIC_ARITHMETIC_SLIP"
                        )
            except ValueError:
                pass

        return None

    @classmethod
    def _check_formula_recall(
        cls, student: str, expected: str, prompt: str, feedback: str
    ) -> Optional[ClassificationResult]:
        """Detects formula recall gaps (e.g. forgot 1/2 in kinetic energy, wrong constant)."""
        combined = f"{feedback} {prompt} {student}".lower()
        if any(k in combined for k in ("formula recall", "forgot formula", "wrong formula", "misremembered formula")):
            return ClassificationResult(
                primary_error_type=ErrorType.FORMULA_RECALL,
                error_subtype="formula_misuse",
                error_summary="Incorrect formula recalled or standard equation constant omitted.",
                confidence=ConfidenceClass.HIGH,
                classifier_version=cls.VERSION,
                deterministic_rule="FORMULA_RECALL_EXPLICIT"
            )

        # Kinetic energy 1/2 factor omission
        if "kinetic energy" in combined and "mv^2" in student.replace(" ", "") and "1/2" not in student:
            return ClassificationResult(
                primary_error_type=ErrorType.FORMULA_RECALL,
                secondary_error_types=[ErrorType.CONCEPTUAL],
                error_subtype="formula_constant_omission",
                error_summary="Omitted the 1/2 coefficient in kinetic energy formula.",
                confidence=ConfidenceClass.HIGH,
                classifier_version=cls.VERSION,
                deterministic_rule="KE_FORMULA_COEFFICIENT"
            )

        return None

    @classmethod
    def _check_misread_question(
        cls, student: str, expected: str, prompt: str, feedback: str
    ) -> Optional[ClassificationResult]:
        """Detects answering the wrong target (e.g., perimeter instead of area)."""
        combined = f"{feedback} {prompt}".lower()
        if any(k in combined for k in ("misread", "inverted target", "asked for", "read the question carefully")):
            return ClassificationResult(
                primary_error_type=ErrorType.MISREAD_QUESTION,
                error_subtype="target_inversion",
                error_summary="Misinterpreted the required target or problem constraints.",
                confidence=ConfidenceClass.MODERATE,
                classifier_version=cls.VERSION,
                deterministic_rule="MISREAD_TARGET"
            )
        return None

    # ─── RUBRIC / FEEDBACK CLASSIFIER ─────────────────────────────────────────

    @classmethod
    def _classify_via_rubric(cls, candidate: MistakeCandidate) -> Optional[ClassificationResult]:
        """
        Rubric classifier for open conceptual responses using feedback signals.
        """
        feedback = (candidate.feedback_reason or "").lower()
        resp = candidate.student_response.lower()

        # Conceptual mechanisms
        if any(k in feedback for k in ("conceptual", "concept mechanism", "underlying principle", "misconception", "misunderstanding")):
            return ClassificationResult(
                primary_error_type=ErrorType.CONCEPTUAL,
                secondary_error_types=[],
                error_subtype="principle_confusion",
                error_summary="Conceptual misunderstanding of underlying educational mechanism.",
                confidence=ConfidenceClass.MODERATE,
                classifier_version=cls.VERSION,
                deterministic_rule="RUBRIC_CONCEPTUAL"
            )

        # Procedural / step sequencing
        if any(k in feedback for k in ("procedural", "step order", "algorithm", "incorrect method", "steps", "transposition")):
            return ClassificationResult(
                primary_error_type=ErrorType.PROCEDURAL,
                secondary_error_types=[],
                error_subtype="step_sequencing",
                error_summary="Procedural execution error or invalid step order.",
                confidence=ConfidenceClass.MODERATE,
                classifier_version=cls.VERSION,
                deterministic_rule="RUBRIC_PROCEDURAL"
            )

        # Logical reasoning
        if any(k in feedback for k in ("reasoning", "logic", "premise", "assumption", "deduction", "fallacy")):
            return ClassificationResult(
                primary_error_type=ErrorType.REASONING,
                secondary_error_types=[],
                error_subtype="flawed_assumption",
                error_summary="Logical reasoning or deduction flaw.",
                confidence=ConfidenceClass.MODERATE,
                classifier_version=cls.VERSION,
                deterministic_rule="RUBRIC_REASONING"
            )

        # Memory / definition recall
        if any(k in feedback for k in ("definition", "terminology", "term", "name of", "fact", "recall")):
            return ClassificationResult(
                primary_error_type=ErrorType.MEMORY_RECALL,
                secondary_error_types=[],
                error_subtype="definition_recall",
                error_summary="Terminology or definition recall error.",
                confidence=ConfidenceClass.MODERATE,
                classifier_version=cls.VERSION,
                deterministic_rule="RUBRIC_MEMORY"
            )

        return None

    # ─── SUBJECT-SPECIFIC HEURISTICS ──────────────────────────────────────────

    @classmethod
    def _check_subject_heuristics(cls, candidate: MistakeCandidate) -> Optional[ClassificationResult]:
        """Subject-specific rules for Chemistry, Biology, CS, Math, and Physics (§3)."""
        subject = candidate.subject
        resp = candidate.student_response.lower()

        # Computer Science: off-by-one, condition inversion
        if subject in ("Computer Science", "Informatics Practices"):
            if any(k in resp for k in ("<=", ">=", "index", "+ 1", "- 1", "length")):
                return ClassificationResult(
                    primary_error_type=ErrorType.PROCEDURAL,
                    error_subtype="off_by_one",
                    error_summary="Off-by-one or boundary index condition error.",
                    confidence=ConfidenceClass.MODERATE,
                    classifier_version=cls.VERSION,
                    deterministic_rule="CS_BOUNDARY_HEURISTIC"
                )

        # Chemistry: reaction balancing / valency
        if subject == "Chemistry":
            if any(k in resp for k in ("valency", "charge", "stoichiometry", "ratio", "moles")):
                return ClassificationResult(
                    primary_error_type=ErrorType.CONCEPTUAL,
                    error_subtype="valency_or_charge_issue",
                    error_summary="Valency, charge, or stoichiometric ratio confusion.",
                    confidence=ConfidenceClass.MODERATE,
                    classifier_version=cls.VERSION,
                    deterministic_rule="CHEM_VALENCY_HEURISTIC"
                )

        # Biology: process order / term confusion
        if subject == "Biology":
            if any(k in resp for k in ("mitosis", "meiosis", "prophase", "metaphase", "stage", "phase")):
                return ClassificationResult(
                    primary_error_type=ErrorType.PROCEDURAL,
                    error_subtype="process_order_confusion",
                    error_summary="Cellular process order or phase sequence confusion.",
                    confidence=ConfidenceClass.MODERATE,
                    classifier_version=cls.VERSION,
                    deterministic_rule="BIO_PROCESS_HEURISTIC"
                )

        return None
