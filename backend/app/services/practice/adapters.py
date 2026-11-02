"""
LearnByGenie — Domain Validation Adapters (Feature 6, §14)
==========================================================
Domain-specific answer validation adapters.
CRITICAL ARCHITECTURAL BOUNDARY:
- Adapters handle ONLY domain-specific answer validation and normalization.
- Adapters MUST NOT implement selection policy, mastery, Mistake DNA, or session state.
"""
from typing import Any, Tuple, Optional, Union
import re
import math
from app.services.practice.schemas import PracticeItem, QuestionType


class BaseDomainValidator:
    """Base validator for question answers."""

    def validate_answer(self, item: PracticeItem, student_response: Any) -> Tuple[bool, str]:
        if item.question_type == QuestionType.MCQ:
            return self.validate_mcq(item, student_response)
        elif item.question_type == QuestionType.NUMERIC:
            return self.validate_numeric(item, student_response)
        else:
            return self.validate_text(item, student_response)

    def validate_mcq(self, item: PracticeItem, student_response: Any) -> Tuple[bool, str]:
        """Validates MCQ response by comparing normalized choice text or option index."""
        raw_resp = str(student_response).strip()
        raw_correct = item.correct_answer

        # If correct answer is a list (e.g. multiple representations)
        correct_candidates = [raw_correct] if not isinstance(raw_correct, list) else raw_correct
        normalized_correct = [str(c).strip().lower() for c in correct_candidates]

        # 1. Direct text match
        if raw_resp.lower() in normalized_correct:
            return True, "Correct"

        # 2. Check if student passed an index (e.g. "0", "1") or option letter ("A", "B")
        if item.options:
            # Letter check (A, B, C, D)
            if len(raw_resp) == 1 and raw_resp.upper() in "ABCDEF":
                idx = ord(raw_resp.upper()) - ord("A")
                if 0 <= idx < len(item.options):
                    opt_text = str(item.options[idx]).strip().lower()
                    if opt_text in normalized_correct:
                        return True, "Correct"

            # Numeric index check
            if raw_resp.isdigit():
                idx = int(raw_resp)
                if 0 <= idx < len(item.options):
                    opt_text = str(item.options[idx]).strip().lower()
                    if opt_text in normalized_correct:
                        return True, "Correct"

            # Check if correct answer was an index but student answered option text
            for cand in correct_candidates:
                if str(cand).isdigit():
                    c_idx = int(str(cand))
                    if 0 <= c_idx < len(item.options) and str(item.options[c_idx]).strip().lower() == raw_resp.lower():
                        return True, "Correct"

        return False, "Incorrect"

    def validate_numeric(self, item: PracticeItem, student_response: Any) -> Tuple[bool, str]:
        """Validates numeric responses with tolerance for floating-point / fraction inputs."""
        try:
            val_resp = self._parse_number(student_response)
            val_correct = self._parse_number(item.correct_answer)
            if val_resp is not None and val_correct is not None:
                # Tolerance check (absolute <= 1e-4 or relative <= 1%)
                if math.isclose(val_resp, val_correct, rel_tol=0.01, abs_tol=1e-4):
                    return True, "Correct"
        except Exception:
            pass

        # String fallback
        str_resp = str(student_response).strip().lower()
        str_correct = str(item.correct_answer).strip().lower()
        return (str_resp == str_correct), "Correct" if str_resp == str_correct else "Incorrect"

    def validate_text(self, item: PracticeItem, student_response: Any) -> Tuple[bool, str]:
        str_resp = str(student_response).strip().lower()
        str_correct = str(item.correct_answer).strip().lower()
        return (str_resp == str_correct), "Correct" if str_resp == str_correct else "Incorrect"

    def _parse_number(self, val: Any) -> Optional[float]:
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).strip()
        # Handle simple fractions like "3/4"
        if "/" in s:
            parts = s.split("/")
            if len(parts) == 2 and parts[0].strip().replace("-", "").isdigit() and parts[1].strip().isdigit():
                denom = float(parts[1].strip())
                if denom != 0:
                    return float(parts[0].strip()) / denom
        try:
            return float(s)
        except ValueError:
            return None


class GenericMCQValidator(BaseDomainValidator):
    """Domain-agnostic standard MCQ validator."""
    pass


class NumericValidator(BaseDomainValidator):
    """Domain-agnostic standard numeric validator."""
    pass


class MathAdapter(BaseDomainValidator):
    """Mathematics domain validation adapter."""
    def validate_numeric(self, item: PracticeItem, student_response: Any) -> Tuple[bool, str]:
        # Handle +/- spaces e.g. "x + 2" or clean fraction/expression
        resp_clean = re.sub(r"\s+", "", str(student_response).strip().lower())
        corr_clean = re.sub(r"\s+", "", str(item.correct_answer).strip().lower())
        if resp_clean == corr_clean:
            return True, "Correct"
        return super().validate_numeric(item, student_response)


class PhysicsAdapter(BaseDomainValidator):
    """Physics domain validation adapter (handles units / scientific notation)."""
    def validate_numeric(self, item: PracticeItem, student_response: Any) -> Tuple[bool, str]:
        # Strip common trailing units like "m/s", "N", "J", "V", "C", "kg"
        resp_str = re.sub(r"[a-zA-Z/^]+$", "", str(student_response).strip()).strip()
        corr_str = re.sub(r"[a-zA-Z/^]+$", "", str(item.correct_answer).strip()).strip()
        num_resp = self._parse_number(resp_str)
        num_corr = self._parse_number(corr_str)
        if num_resp is not None and num_corr is not None:
            if math.isclose(num_resp, num_corr, rel_tol=0.02, abs_tol=1e-3):
                return True, "Correct"
        return super().validate_numeric(item, student_response)


class ChemistryAdapter(BaseDomainValidator):
    """Chemistry domain validation adapter."""
    pass


class BiologyAdapter(BaseDomainValidator):
    """Biology domain validation adapter."""
    pass


class CSAdapter(BaseDomainValidator):
    """Computer Science domain validation adapter (handles boolean keywords & complexity syntax)."""
    def validate_text(self, item: PracticeItem, student_response: Any) -> Tuple[bool, str]:
        # Normalize O(n) notation vs O(N) vs o(n)
        r_norm = re.sub(r"\s+", "", str(student_response).strip().lower())
        c_norm = re.sub(r"\s+", "", str(item.correct_answer).strip().lower())
        if r_norm == c_norm:
            return True, "Correct"
        return super().validate_text(item, student_response)


# ─── DOMAIN ADAPTER REGISTRY ──────────────────────────────────────────────────

class DomainAdapterRegistry:
    """
    Registry for subject adapters (§14, §15).
    Guarantees subject-agnostic fallback: any unregistered subject uses BaseDomainValidator!
    """
    _adapters = {
        "mathematics": MathAdapter(),
        "math": MathAdapter(),
        "physics": PhysicsAdapter(),
        "chemistry": ChemistryAdapter(),
        "biology": BiologyAdapter(),
        "science": BaseDomainValidator(),
        "computer science": CSAdapter(),
        "cs": CSAdapter(),
    }

    @classmethod
    def get_adapter(cls, subject: str) -> BaseDomainValidator:
        s_lower = (subject or "").strip().lower()
        return cls._adapters.get(s_lower, BaseDomainValidator())

    @classmethod
    def register_adapter(cls, subject: str, adapter: BaseDomainValidator) -> None:
        cls._adapters[subject.strip().lower()] = adapter
