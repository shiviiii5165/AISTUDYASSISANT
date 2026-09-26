"""
LearnByGenie Notes Decision Engine — Configurable Pedagogical Policies
====================================================================
Pure Python deterministic policy definitions for:
- Student mastery thresholds (Low < 0.40, Medium 0.40–0.75, High >= 0.75)
- Topic structural categories
- Grade-level scaffolding brackets (Classes 3–12)
- Remediation and misconception priorities
"""
import re
from enum import Enum
from typing import Dict, List, Any


class MasteryBracket(str, Enum):
    LOW = "low"          # 0.00 <= mastery < 0.40
    MEDIUM = "medium"    # 0.40 <= mastery < 0.75
    HIGH = "high"        # 0.75 <= mastery <= 1.00
    UNKNOWN = "unknown"  # mastery is null or not provided


class TopicCategory(str, Enum):
    PROCESS = "process"
    COMPARISON = "comparison"
    FORMULA_HEAVY = "formula_heavy"
    CONCEPTUAL = "conceptual"
    PROCEDURAL = "procedural"
    DEFINITION_HEAVY = "definition_heavy"
    CHRONOLOGICAL = "chronological"
    CAUSE_EFFECT = "cause_effect"
    PROBLEM_SOLVING = "problem_solving"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class MasteryPolicy:
    LOW_THRESHOLD: float = 0.40
    HIGH_THRESHOLD: float = 0.75

    @classmethod
    def get_bracket(cls, mastery: float | None) -> MasteryBracket:
        if mastery is None:
            return MasteryBracket.UNKNOWN
        if mastery < cls.LOW_THRESHOLD:
            return MasteryBracket.LOW
        if mastery < cls.HIGH_THRESHOLD:
            return MasteryBracket.MEDIUM
        return MasteryBracket.HIGH


class GradePolicy:
    @staticmethod
    def parse_class_number(class_level: str) -> int:
        """Extracts integer class number from strings like 'Class 7', 'Grade 10', 'Primary 4', etc."""
        match = re.search(r'(\d+)', class_level)
        if match:
            return int(match.group(1))
        lower = class_level.lower()
        if "primary" in lower:
            return 4
        if "middle" in lower:
            return 7
        if "high" in lower:
            return 10
        if "senior" in lower or "b.tech" in lower or "college" in lower:
            return 12
        return 10

    @staticmethod
    def get_bracket(class_num: int) -> str:
        """Returns grade bracket: 'primary', 'middle', 'secondary', 'senior_secondary'."""
        if class_num <= 5:
            return "primary"
        elif class_num <= 8:
            return "middle"
        elif class_num <= 10:
            return "secondary"
        return "senior_secondary"


class DecisionPrecedence:
    """
    Controls decision resolution order across competing pedagogical signals.
    1. explicit user intent
    2. explicit exam/revision state
    3. severe misconception / severe weakness
    4. student mastery
    5. lesson pedagogy
    6. topic structure
    7. curriculum structure
    8. supporting TeachMe / PPT signals
    9. neutral defaults
    """
    EXPLICIT_USER_INTENT = 1
    EXPLICIT_EXAM_STATE = 2
    SEVERE_MISCONCEPTION = 3
    STUDENT_MASTERY = 4
    LESSON_PEDAGOGY = 5
    TOPIC_STRUCTURE = 6
    CURRICULUM_STRUCTURE = 7
    SUPPORTING_SIGNALS = 8
    NEUTRAL_DEFAULTS = 9

