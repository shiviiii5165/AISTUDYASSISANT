"""
TeachGenie Notes Decision Engine — Mastery Policy Engine
========================================================
Translates student mastery scores into deterministic difficulty,
scaffolding, practice, and remediation requirements.
"""
from typing import Optional, Dict, Any, List, Tuple
from app.services.notes.schemas import NoteDifficulty, NoteDepth
from .policies import MasteryBracket, MasteryPolicy


class MasteryDecision:
    """Encapsulates deterministic decisions derived from student mastery."""
    def __init__(
        self,
        bracket: MasteryBracket,
        score: Optional[float],
        difficulty: NoteDifficulty,
        depth: NoteDepth,
        scaffolding: str,
        practice_difficulty: str,
        practice_types: List[str],
        features: List[str],
        remediation_required: bool,
        remediation_priority: str
    ):
        self.bracket = bracket
        self.score = score
        self.difficulty = difficulty
        self.depth = depth
        self.scaffolding = scaffolding
        self.practice_difficulty = practice_difficulty
        self.practice_types = practice_types
        self.features = features
        self.remediation_required = remediation_required
        self.remediation_priority = remediation_priority


class MasteryPolicyEngine:
    """Evaluates student mastery signals deterministically according to strict policy."""

    @classmethod
    def evaluate(
        cls,
        mastery_map: Dict[str, float],
        class_num: int,
        topic: str = "",
        explicit_depth: Optional[NoteDepth] = None
    ) -> MasteryDecision:
        """
        Evaluates student mastery without inventing data:
        - LOW: 0.00 <= score < 0.40
        - MEDIUM: 0.40 <= score < 0.75
        - HIGH: 0.75 <= score <= 1.00
        - UNKNOWN: score is None / unavailable
        """
        # Calculate topic-specific or overall average mastery
        score: Optional[float] = None
        if mastery_map:
            # Check for exact or substring topic match
            topic_lower = topic.lower()
            matched = [v for k, v in mastery_map.items() if k.lower() in topic_lower or topic_lower in k.lower()]
            if matched:
                score = sum(matched) / len(matched)
            else:
                score = sum(mastery_map.values()) / len(mastery_map)

        bracket = MasteryPolicy.get_bracket(score)

        if bracket == MasteryBracket.LOW:
            # Foundational difficulty, guided/intensive scaffolding, targeted remediation
            scaffolding = "intensive" if (score is not None and score < 0.25) else "guided"
            depth = explicit_depth or NoteDepth.DETAILED  # Struggling students need thorough clarity
            difficulty = NoteDifficulty.FOUNDATIONAL
            practice_difficulty = "foundational"
            practice_types = ["recall", "diagnostic"]
            features = [
                "guided_explanation",
                "step_by_step_scaffolding",
                "worked_examples",
                "misconception_correction",
                "concrete_analogies"
            ]
            remediation_required = True
            remediation_priority = "high"

        elif bracket == MasteryBracket.MEDIUM:
            # Standard explanation, intermediate practice, moderate scaffolding
            scaffolding = "moderate"
            depth = explicit_depth or NoteDepth.STANDARD
            difficulty = NoteDifficulty.STANDARD
            practice_difficulty = "intermediate"
            practice_types = ["recall", "application"]
            features = [
                "standard_explanation",
                "examples",
                "key_points",
                "intermediate_practice"
            ]
            remediation_required = False
            remediation_priority = "medium"

        elif bracket == MasteryBracket.HIGH:
            # Concise explanation, advanced/application focus, tricky cases, reduced repetition
            scaffolding = "minimal"
            depth = explicit_depth or NoteDepth.CONCISE
            difficulty = NoteDifficulty.ADVANCED if class_num >= 9 else NoteDifficulty.STANDARD
            practice_difficulty = "advanced"
            practice_types = ["application", "tricky_cases"]
            features = [
                "concise_explanation",
                "application_focus",
                "tricky_cases",
                "advanced_practice",
                "reduced_repetition"
            ]
            remediation_required = False
            remediation_priority = "none"

        else:  # UNKNOWN
            # Neutral defaults - NEVER assume medium or fabricate mastery
            scaffolding = "moderate"
            depth = explicit_depth or NoteDepth.STANDARD
            if class_num <= 5:
                difficulty = NoteDifficulty.FOUNDATIONAL
                practice_difficulty = "basic"
            elif class_num <= 10:
                difficulty = NoteDifficulty.STANDARD
                practice_difficulty = "intermediate"
            else:
                difficulty = NoteDifficulty.ADVANCED
                practice_difficulty = "advanced"

            practice_types = ["recall", "application"]
            features = [
                "guided_explanation",
                "examples",
                "thinking_checkpoints",
                "key_points",
                "practice"
            ]
            remediation_required = False
            remediation_priority = "none"

        return MasteryDecision(
            bracket=bracket,
            score=score,
            difficulty=difficulty,
            depth=depth,
            scaffolding=scaffolding,
            practice_difficulty=practice_difficulty,
            practice_types=practice_types,
            features=features,
            remediation_required=remediation_required,
            remediation_priority=remediation_priority
        )
