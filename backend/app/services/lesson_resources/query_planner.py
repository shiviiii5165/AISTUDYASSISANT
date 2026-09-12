"""
TeachGenie Lesson Planner — Resource Query Planner
==================================================
Deterministic, concept-dense query synthesis for search providers.
Avoids noisy sentence queries and enforces staged broadening.
"""

from typing import List, Dict
from .schemas import ResourceIntentProfile, StageIntent


class ResourceQueryPlanner:
    """
    Synthesizes provider-specific, precision queries based on ResourceIntentProfile.
    Deterministic first: avoids LLM latency/token costs while ensuring high keyword density.
    """

    @classmethod
    def plan_youtube_queries(cls, profile: ResourceIntentProfile) -> List[str]:
        """
        Builds 2-3 focused YouTube search queries based on stage intent and weaknesses.
        Pass 1: Exact concept + key subconcepts + intent cue (e.g. 'solved examples' or 'explained').
        Pass 2: Learner weakness / comparative deep dive (e.g. '2NF vs 3NF').
        Pass 3: Practice / foundational walkthrough.
        """
        topic = profile.canonical_topic
        concepts = profile.concept_names
        weaknesses = profile.learner_weaknesses
        intent = profile.stage_intent
        lang_suffix = " in hindi" if profile.preferred_language.lower() in ("hindi", "hinglish") else ""

        queries: List[str] = []

        # Query 1: Primary Concept & Subconcepts with Intent modifier
        if intent == StageIntent.REMEDIAL:
            concept_str = " ".join(concepts[:4]) if concepts else topic
            q1 = f"{topic} {concept_str} solved examples{lang_suffix}".strip()
        elif intent == StageIntent.PRACTICE:
            concept_str = " ".join(concepts[:3]) if concepts else topic
            q1 = f"{topic} {concept_str} practice problems walkthrough{lang_suffix}".strip()
        elif intent in (StageIntent.INTRODUCTION, StageIntent.CONCEPT_LEARNING):
            q1 = f"{topic} conceptual explanation visual tutorial{lang_suffix}".strip()
        else:
            concept_str = " ".join(concepts[:3]) if concepts else topic
            q1 = f"{topic} {concept_str} comprehensive lecture{lang_suffix}".strip()
        queries.append(q1)

        # Query 2: Target specific learner weaknesses or comparative concepts
        if weaknesses:
            w_text = weaknesses[0]
            q2 = f"{topic} {w_text} explained with examples{lang_suffix}".strip()
            queries.append(q2)
        elif len(concepts) >= 3:
            q2 = f"{concepts[0]} vs {concepts[1]} {topic} comparison{lang_suffix}".strip()
            queries.append(q2)
        else:
            q2 = f"{topic} worked example step by step{lang_suffix}".strip()
            queries.append(q2)

        # Query 3: Practice / Revision fallback
        if len(concepts) >= 2:
            q3 = f"{topic} {concepts[-1]} questions and solutions{lang_suffix}".strip()
            queries.append(q3)

        return queries[:3]

    @classmethod
    def plan_paper_queries(cls, profile: ResourceIntentProfile) -> List[str]:
        """
        Builds academic search queries for Semantic Scholar and arXiv.
        Focuses on foundational terms, formal concepts, and theory.
        """
        topic = profile.canonical_topic
        concepts = profile.concept_names
        
        q1 = f"{topic} {' '.join(concepts[:3])}".strip()
        if len(concepts) >= 4:
            q2 = f"{topic} {' '.join(concepts[2:5])}".strip()
            return [q1, q2]
        return [q1]

    @classmethod
    def plan_practice_queries(cls, profile: ResourceIntentProfile) -> List[str]:
        """
        Builds domain-constrained coding/practice queries for Tavily.
        """
        if not profile.is_programming_topic:
            # Theoretical or non-coding practice
            return [f"{profile.canonical_topic} practice problems questions with solutions"]
            
        topic = profile.canonical_topic
        concepts = profile.concept_names
        concept_slug = concepts[0] if concepts else topic
        
        return [
            f"{topic} {concept_slug} leetcode practice",
            f"{topic} {concept_slug} geeksforgeeks practice problems"
        ]

    @classmethod
    def plan_docs_queries(cls, profile: ResourceIntentProfile) -> List[str]:
        """
        Builds official documentation queries.
        """
        topic = profile.canonical_topic
        concepts = profile.concept_names
        first_concept = concepts[0] if concepts else ""
        return [f"{topic} {first_concept} official documentation manual".strip()]

    @classmethod
    def plan_wikipedia_queries(cls, profile: ResourceIntentProfile) -> List[str]:
        """
        Builds Wikipedia OpenSearch queries.
        """
        return [
            profile.canonical_topic,
            profile.concept_names[0] if profile.concept_names else profile.canonical_topic
        ]
