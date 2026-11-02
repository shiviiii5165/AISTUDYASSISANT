"""
LearnByGenie — Adaptive Practice Selection Policy (Feature 6)
==============================================================
Centralized, config-driven, versioned policy for:
- Difficulty transitions (§11)
- Recent-item exclusion and skill streak throttling (§19, §38)
- Candidate category ranking (§6, §8)
- Assistance and hint effects on progression (§11, §25)
- Session budgets (§47)
"""
from typing import Dict, Any, Optional, Tuple, Union
from pydantic import BaseModel, Field
from .schemas import DifficultyBand, AssistanceLevel, SelectionCategory, PracticeMode


class PracticePolicy(BaseModel):
    version: str = "1.0.0"
    description: str = "Canonical Deterministic Adaptive Practice Policy v1.0.0"

    # Anti-repetition & streak limits (§19, §38)
    recent_item_exclusion_window: int = 5
    max_repeated_skill_streak: int = 3

    # Deterministic difficulty transitions (§11)
    consecutive_correct_for_promotion: int = 2
    consecutive_incorrect_for_demotion: int = 2

    # Category candidate prioritization weights (§6)
    prerequisite_repair_priority: int = 100
    mistake_dna_repair_priority: int = 90
    developing_skill_priority: int = 70
    ready_next_skill_priority: int = 60
    exploratory_probe_priority: int = 50
    secure_concept_check_priority: int = 30

    # Session question budget presets (§47)
    budget_quick: int = 5
    budget_standard: int = 10
    budget_deep: int = 15

    # Content eligibility threshold (§50)
    min_validated_items_for_sufficiency: int = 2

    def resolve_budget(self, requested_budget: Optional[Union[int, str]]) -> int:
        if isinstance(requested_budget, int) and requested_budget > 0:
            return min(30, max(3, requested_budget))
        if isinstance(requested_budget, str):
            b_lower = requested_budget.lower()
            if "quick" in b_lower:
                return self.budget_quick
            if "deep" in b_lower:
                return self.budget_deep
        return self.budget_standard

    def adapt_difficulty(
        self,
        current_difficulty: DifficultyBand,
        consecutive_correct: int,
        consecutive_incorrect: int,
        assistance_level: AssistanceLevel,
        is_correct: bool
    ) -> Tuple[DifficultyBand, int, int]:
        """
        Deterministic difficulty adaptation (§11):
        - Repeated independent success -> increase difficulty (FOUNDATIONAL -> STANDARD -> ADVANCED)
        - Single failure does NOT instantly drop multiple levels
        - Repeated failure (>= consecutive_incorrect_for_demotion) -> step down (ADVANCED -> STANDARD -> FOUNDATIONAL)
        - Hint-assisted success does NOT trigger promotion!
        Returns (new_difficulty, new_consecutive_correct, new_consecutive_incorrect).
        """
        if is_correct:
            new_consec_incorrect = 0
            if assistance_level == AssistanceLevel.INDEPENDENT:
                new_consec_correct = consecutive_correct + 1
                if new_consec_correct >= self.consecutive_correct_for_promotion:
                    # Promote if possible
                    if current_difficulty == DifficultyBand.FOUNDATIONAL:
                        return DifficultyBand.STANDARD, 0, 0
                    elif current_difficulty == DifficultyBand.STANDARD:
                        return DifficultyBand.ADVANCED, 0, 0
                    else:
                        return DifficultyBand.ADVANCED, 0, 0
                return current_difficulty, new_consec_correct, 0
            else:
                # Assisted success preserves current level without inflating independent promotion streak
                return current_difficulty, 0, 0
        else:
            # Incorrect response
            new_consec_correct = 0
            new_consec_incorrect = consecutive_incorrect + 1
            if new_consec_incorrect >= self.consecutive_incorrect_for_demotion:
                # Demote by one tier
                if current_difficulty == DifficultyBand.ADVANCED:
                    return DifficultyBand.STANDARD, 0, 0
                elif current_difficulty == DifficultyBand.STANDARD:
                    return DifficultyBand.FOUNDATIONAL, 0, 0
                else:
                    return DifficultyBand.FOUNDATIONAL, 0, 0
            return current_difficulty, 0, new_consec_incorrect


# Canonical default policy singleton
DEFAULT_PRACTICE_POLICY_V1 = PracticePolicy()

_POLICY_REGISTRY: Dict[str, PracticePolicy] = {
    DEFAULT_PRACTICE_POLICY_V1.version: DEFAULT_PRACTICE_POLICY_V1
}


def get_policy(version: Optional[str] = None) -> PracticePolicy:
    if version and version in _POLICY_REGISTRY:
        return _POLICY_REGISTRY[version]
    return DEFAULT_PRACTICE_POLICY_V1


def register_policy(policy: PracticePolicy) -> None:
    _POLICY_REGISTRY[policy.version] = policy
