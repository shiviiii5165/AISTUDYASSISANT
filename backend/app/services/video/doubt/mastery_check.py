"""
Quick Mastery Check Generator
==============================
Generates ONE bite-sized, interactive understanding check question after resolving meaningful doubts.
Does NOT create annoying full quizzes.
Validates the learner's answer:
- If correct: acknowledges mastery and allows them to continue watching
- If incorrect: advises strategy escalation
"""
from typing import Optional, Dict, Any, List
from ..schemas import MasteryCheck


class QuickMasteryCheckGenerator:
    """Generates and evaluates 1-question concept checkpoints."""

    @classmethod
    def create_check_for_concept(cls, concept_key: str) -> Optional[MasteryCheck]:
        ck = concept_key.lower()

        if "linked_list" in ck or "insertion" in ck:
            return MasteryCheck(
                question="If we want to insert node X between node B and node C (B -> C), what should X.next point to first?",
                options=[
                    "X.next should point to node B",
                    "X.next should point to node C",
                    "X.next should point to NULL",
                    "B.next should point to NULL"
                ],
                correct_answer_index=1,
                explanation="X.next must connect to C first to maintain the reference to the rest of the list before modifying B.next!",
                target_concept_id="linked_list_insertion"
            )
        elif "integration" in ck:
            return MasteryCheck(
                question="In the formula int(u dv) = uv - int(v du), what mathematical operation generates the minus sign?",
                options=[
                    "Differentiating the constant of integration",
                    "Rearranging the product rule formula d(uv) = u dv + v du",
                    "Taking the reciprocal of dv",
                    "Applying the quotient rule"
                ],
                correct_answer_index=1,
                explanation="Subtracting int(v du) to isolate int(u dv) in the integrated product rule produces the minus sign.",
                target_concept_id="integration_by_parts"
            )
        elif "french_revolution" in ck:
            return MasteryCheck(
                question="Which Estate in pre-revolutionary France comprised 98% of the population yet carried almost all the tax burden?",
                options=[
                    "First Estate (Clergy)",
                    "Second Estate (Nobility)",
                    "Third Estate (Peasants, workers, bourgeoisie)",
                    "Royal Council"
                ],
                correct_answer_index=2,
                explanation="The Third Estate carried the entire tax burden with zero feudal privileges.",
                target_concept_id="french_revolution"
            )
        elif "photosynthesis" in ck:
            return MasteryCheck(
                question="What is the primary role of ATP produced during the light-dependent reactions in the thylakoid?",
                options=[
                    "Directly forming the cell wall",
                    "Supplying chemical energy to power carbon fixation in the Calvin cycle",
                    "Absorbing green photons from sunlight",
                    "Splitting carbon dioxide molecules"
                ],
                correct_answer_index=1,
                explanation="ATP and NADPH carry stored energy to the stroma to power the Calvin cycle synthesis of glucose.",
                target_concept_id="photosynthesis"
            )

        return MasteryCheck(
            question="Based on this explanation, what is the most critical invariant to preserve?",
            options=[
                "Preserve correct operational order and dependencies",
                "Reverse the order of steps arbitrarily",
                "Ignore boundary conditions"
            ],
            correct_answer_index=0,
            explanation="Maintaining invariant operational order prevents errors.",
            target_concept_id=concept_key
        )

    @classmethod
    def evaluate_answer(cls, check: MasteryCheck, selected_index: int) -> Dict[str, Any]:
        """Evaluates student's answer selection."""
        is_correct = (selected_index == check.correct_answer_index)
        return {
            "is_correct": is_correct,
            "selected_index": selected_index,
            "correct_index": check.correct_answer_index,
            "feedback": "Correct! You've mastered this concept. Feel free to resume watching." if is_correct else f"Not quite. {check.explanation}",
            "recommended_action": "continue_video" if is_correct else "escalate_strategy"
        }
