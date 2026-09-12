"""
Dedicated Prerequisite Gap Detector (Decision #3)
=================================================
Analyzes student question and context to detect if comprehension failure
stems from a missing foundational prerequisite rather than the active concept itself.
If detected, triggers temporary prerequisite repair before returning to the core topic.
"""
from typing import Optional, Dict, Any, List
import re
from ..schemas import DoubtContext, PrerequisiteGapResult


PREREQUISITE_INDICATORS = [
    "what is", "kya hota hai", "meaning of", "never heard of", "basic", "basics",
    "pehle kya", "what does", "dont know", "samajh nahi aaya pointer", "address kya hai",
    "derivative kya hota", "estates kya the", "atp kya hota hai", "what is primary key"
]


class PrerequisiteGapDetector:
    """Detects if learner is blocked by an unmastered prerequisite concept."""

    @classmethod
    def detect_gap(cls, context: DoubtContext) -> PrerequisiteGapResult:
        question = context.student_question.lower().strip()
        prereqs = context.prerequisites or []

        # 1. Check if the question explicitly asks about one of the prerequisites
        for p in prereqs:
            p_lower = p.lower()
            # E.g. "pointer" in "pointer kya hota hai"
            p_tokens = [t for t in re.split(r'\W+', p_lower) if len(t) > 3]
            for token in p_tokens:
                if token in question:
                    return PrerequisiteGapResult(
                        has_gap=True,
                        missing_prerequisite=p,
                        repair_concept=f"Foundations of {p}",
                        brief_remedy=f"Before understanding {context.current_concept}, let's quickly review {p}."
                    )

        # 2. Check general prerequisite indicator expressions
        for ind in PREREQUISITE_INDICATORS:
            if ind in question and prereqs:
                return PrerequisiteGapResult(
                    has_gap=True,
                    missing_prerequisite=prereqs[0],
                    repair_concept=f"Foundations of {prereqs[0]}",
                    brief_remedy=f"To clarify {context.current_concept}, let's build intuition on its core prerequisite: {prereqs[0]}."
                )

        return PrerequisiteGapResult(has_gap=False)
