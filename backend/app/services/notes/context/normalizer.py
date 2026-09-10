"""
TeachGenie Notes Context Engine — Context Normalizer
===================================================
Normalizes equivalent educational representations deterministically
without distorting or changing their underlying semantic meaning.
"""
import re
from typing import Optional, Tuple, Any, Dict


class ContextNormalizer:
    """Deterministic normalization helpers for grades, boards, languages, topics, and mastery."""

    @staticmethod
    def normalize_grade(val: Optional[Any]) -> Tuple[Optional[int], Optional[str]]:
        """
        Normalizes grade/class expressions into (numeric_grade, display_string).
        Examples:
            "class 7" -> (7, "Class 7")
            "Grade 7" -> (7, "Class 7")
            "7" -> (7, "Class 7")
            7 -> (7, "Class 7")
            "B.Tech" -> (12, "B.Tech")
            "College" -> (12, "College")
        """
        if val is None:
            return None, None

        raw = str(val).strip()
        if not raw:
            return None, None

        lower = raw.lower()

        # Check Higher Ed keywords
        if "b.tech" in lower or "btech" in lower or "engineering" in lower:
            return 12, "B.Tech"
        if "college" in lower or "university" in lower or "higher ed" in lower:
            return 12, "Higher Ed"

        # Match numbers: e.g. "Class 9", "grade 9", "9th", "9"
        match = re.search(r'\b(\d{1,2})\b', raw)
        if match:
            grade_num = int(match.group(1))
            if 1 <= grade_num <= 12:
                return grade_num, f"Class {grade_num}"

        # Heuristic keywords for primary/middle/high school
        if "primary" in lower:
            return 4, "Class 4"
        if "middle" in lower:
            return 7, "Class 7"
        if "high" in lower:
            return 10, "Class 10"

        return None, raw

    @staticmethod
    def normalize_curriculum(board: Optional[str]) -> Optional[str]:
        """
        Normalizes curriculum and board expressions.
        Examples:
            "cbse" | "C.B.S.E." | "CBSE Board" -> "CBSE"
            "icse" | "I.C.S.E." -> "ICSE"
            "state board" | "stateboard" -> "State Board"
            "ib" -> "IB"
            "igcse" -> "IGCSE"
        Never invents or assumes a curriculum if missing.
        """
        if not board:
            return None

        cleaned = re.sub(r'[\.\s\-_]+', ' ', str(board).strip().lower())
        tokens = set(cleaned.split())

        if "cbse" in tokens or "c b s e" in cleaned:
            return "CBSE"
        if "icse" in tokens or "i c s e" in cleaned or "isc" in tokens:
            return "ICSE"
        if "state" in tokens or "stateboard" in cleaned:
            return "State Board"
        if "igcse" in tokens or "cambridge" in tokens:
            return "IGCSE"
        if "ib" in tokens or "international baccalaureate" in cleaned:
            return "IB"

        # Return stripped original if recognized as custom valid string
        trimmed = str(board).strip()
        return trimmed if trimmed else None

    @staticmethod
    def normalize_language(lang: Optional[str]) -> str:
        """
        Normalizes language codes/names to canonical lowercase string.
        Examples:
            "English", "EN", "en-US" -> "english"
            "Hindi", "HI" -> "hindi"
            "Hinglish" -> "hinglish"
        """
        if not lang:
            return "english"

        raw = str(lang).strip().lower()
        if raw in ("en", "eng", "english", "en-us", "en-in", "en-gb"):
            return "english"
        if raw in ("hi", "hin", "hindi"):
            return "hindi"
        if raw in ("hinglish", "hi-en"):
            return "hinglish"

        return raw

    @staticmethod
    def normalize_mastery(val: Any) -> Optional[float]:
        """
        Normalizes percentage strings, integers, or floats into decimal (0.0 to 1.0).
        Examples:
            "73%" -> 0.73
            73 -> 0.73
            0.73 -> 0.73
            "0.85" -> 0.85
        """
        if val is None:
            return None

        try:
            if isinstance(val, str):
                cleaned = val.replace('%', '').strip()
                numeric_val = float(cleaned)
            else:
                numeric_val = float(val)

            # If represented as percentage (1.0 < val <= 100.0)
            if numeric_val > 1.0 and numeric_val <= 100.0:
                numeric_val = numeric_val / 100.0

            # Clamp between 0.0 and 1.0
            return max(0.0, min(1.0, round(numeric_val, 4)))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def normalize_topic(raw_topic: str) -> Tuple[str, str]:
        """
        Lightly normalizes topic strings without destroying domain specificity.
        Preserves rawTopic and returns (rawTopic, normalizedTopic).
        Example:
            "newton's laws of motion" -> ("newton's laws of motion", "Newton's Laws of Motion")
            "Newton's First Law" -> ("Newton's First Law", "Newton's First Law")
        """
        raw = (raw_topic or "").strip()
        if not raw:
            return "", ""

        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', raw)

        # Title case tokens while preserving connecting words, apostrophes, and acronyms
        words = cleaned.split(' ')
        normalized_words = []
        LOWERCASE_WORDS = {"of", "the", "and", "in", "on", "at", "to", "for", "a", "an"}

        for i, w in enumerate(words):
            w_lower = w.lower()
            if w.isupper() and len(w) > 1:
                # Acronym like "DNA", "ATP", "CBSE"
                normalized_words.append(w)
            elif i > 0 and w_lower in LOWERCASE_WORDS:
                normalized_words.append(w_lower)
            elif "'" in w:
                parts = w.split("'")
                normalized_words.append(f"{parts[0].capitalize()}'{parts[1].lower()}")
            elif w_lower.startswith("newton") and w_lower.endswith("s") and "'" not in w:
                normalized_words.append("Newton's")
            else:
                normalized_words.append(w.capitalize())

        normalized = " ".join(normalized_words)
        return raw, normalized
