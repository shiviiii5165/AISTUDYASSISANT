"""
Universal Confusion Diagnosis Engine
====================================
Diagnoses learner confusion into 10 domain-independent canonical categories:
1. DEFINITION_CONFUSION
2. PREREQUISITE_GAP
3. RELATIONSHIP_CONFUSION
4. PROCESS_CONFUSION
5. VISUAL_CONFUSION
6. FORMULA_CONFUSION
7. EXAMPLE_CONFUSION
8. TERMINOLOGY_CONFUSION
9. MEMORY_CONFUSION
10. APPLICATION_CONFUSION
"""
import re
from typing import Optional, Dict, Any
from ..schemas import ConfusionType, ExplanationStrategy, ConfusionDiagnosis, DoubtContext
from .prerequisite_gap import PrerequisiteGapDetector


class ConfusionDiagnosisEngine:
    """Classifies question into exact confusion type and recommends strategy."""

    @classmethod
    def diagnose(cls, context: DoubtContext) -> ConfusionDiagnosis:
        question = context.student_question.lower().strip()

        # 1. First check for dedicated Prerequisite Gap
        gap_res = PrerequisiteGapDetector.detect_gap(context)
        if gap_res.has_gap:
            return ConfusionDiagnosis(
                confusion_type=ConfusionType.PREREQUISITE_GAP,
                confidence=0.92,
                detected_gap=gap_res.missing_prerequisite,
                recommended_strategy=ExplanationStrategy.PREREQUISITE_REPAIR,
                reasoning=f"Question indicates unfamiliarity with foundational prerequisite: {gap_res.missing_prerequisite}"
            )

        # 2. Formula or Symbol Confusion
        if any(w in question for w in ["minus", "formula", "symbol", "sign", "equation", "derivation", "square", "integral", "dx", "f = ma"]):
            return ConfusionDiagnosis(
                confusion_type=ConfusionType.FORMULA_CONFUSION,
                confidence=0.90,
                recommended_strategy=ExplanationStrategy.FORMULA_BREAKDOWN,
                reasoning="Learner is questioning specific mathematical or symbolic transformations."
            )

        # 3. Process / Operational Order Confusion (e.g. "20.next ko 25 kyu kiya", "pehle kyu", "order")
        if any(w in question for w in [".next", "kyu kiya", "why did we connect", "order", "step", "first", "pehle", "sequence", "how does it move"]):
            return ConfusionDiagnosis(
                confusion_type=ConfusionType.PROCESS_CONFUSION,
                confidence=0.95,
                recommended_strategy=ExplanationStrategy.STEP_BY_STEP,
                reasoning="Learner is questioning the specific sequence or necessity of an operational step."
            )

        # 4. Relationship / Causal Confusion (e.g. "ye war start kyu hui", "cause", "kisse connected", "why did X cause Y")
        if any(w in question for w in ["start kyu", "cause", "reason", "kyun hui", "kiske karan", "why did", "relation", "dependency"]):
            return ConfusionDiagnosis(
                confusion_type=ConfusionType.RELATIONSHIP_CONFUSION,
                confidence=0.88,
                recommended_strategy=ExplanationStrategy.REAL_WORLD_ANALOGY,
                reasoning="Learner is seeking the causal driver or underlying relationship."
            )

        # 5. Visual / Diagram Confusion (e.g. "screen pe kya dikh raha hai", "diagram", "arrow", "box", "color")
        if any(w in question for w in ["arrow", "diagram", "box", "color", "screen", "visual", "arrow points"]):
            return ConfusionDiagnosis(
                confusion_type=ConfusionType.VISUAL_CONFUSION,
                confidence=0.85,
                recommended_strategy=ExplanationStrategy.VISUAL,
                reasoning="Learner requires clarification of visual symbols or graphical layout."
            )

        # 6. Real-World Analogy Request (e.g. "real life example se bata", "analogy", "daily life")
        if any(w in question for w in ["real life", "analogy", "metaphor", "daily life", "practical life", "asli zindagi"]):
            return ConfusionDiagnosis(
                confusion_type=ConfusionType.RELATIONSHIP_CONFUSION,
                confidence=0.95,
                recommended_strategy=ExplanationStrategy.REAL_WORLD_ANALOGY,
                reasoning="Learner explicitly requested an intuitive real-world analogy."
            )

        # 7. Exam / Structured Writing Request (e.g. "exam me kaise likhu", "marks", "how to write in exam", "paper me")
        if any(w in question for w in ["exam", "marks", "likhu", "likhein", "write in exam", "paper me", "answer format"]):
            return ConfusionDiagnosis(
                confusion_type=ConfusionType.APPLICATION_CONFUSION,
                confidence=0.95,
                recommended_strategy=ExplanationStrategy.EXAM_STYLE,
                reasoning="Learner explicitly requested an exam-oriented structured answer format."
            )

        # 8. Example / Application Confusion
        if any(w in question for w in ["example", "real world", "kahape use", "where used", "practical", "industry"]):
            return ConfusionDiagnosis(
                confusion_type=ConfusionType.APPLICATION_CONFUSION,
                confidence=0.88,
                recommended_strategy=ExplanationStrategy.SECOND_EXAMPLE,
                reasoning="Learner is requesting practical real-world instantiation."
            )

        # 9. Definition Confusion (Default if general "samajh nahi aaya")
        return ConfusionDiagnosis(
            confusion_type=ConfusionType.DEFINITION_CONFUSION,
            confidence=0.80,
            recommended_strategy=ExplanationStrategy.SIMPLE,
            reasoning="Learner requires an intuitive, simplified re-explanation of the core concept."
        )

    @classmethod
    def diagnose_confusion(cls, question: str, context: DoubtContext) -> ConfusionDiagnosis:
        """Alias accepting question string and context."""
        context.student_question = question
        return cls.diagnose(context)
