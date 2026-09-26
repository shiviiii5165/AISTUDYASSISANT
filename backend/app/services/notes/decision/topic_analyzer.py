"""
LearnByGenie Notes Decision Engine — Deterministic Topic Analyzer
==============================================================
Pure Python deterministic classifier categorizing topics based on
structured curriculum metadata and deterministic pattern matching.
Zero LLM calls. Zero non-deterministic sampling.
"""
import re
from typing import Optional, List, Tuple
from app.services.notes.context.schemas import CanonicalNotesContext
from .policies import TopicCategory


class TopicAnalyzer:
    """Classifies learning topics into structural pedagogical categories."""

    @classmethod
    def classify(cls, ctx: CanonicalNotesContext) -> TopicCategory:
        """
        Determines the primary TopicCategory for a given CanonicalNotesContext.
        Prefers structured curriculum/lesson metadata before topic text matching.
        """
        # Collect candidate text sources
        topic_text = (ctx.topic or "").strip()
        raw_topic = (ctx.raw_topic or "").strip()
        subject_text = (ctx.subject or "").strip().lower()
        chapter_text = (ctx.curriculum.chapter or "") if hasattr(ctx, "curriculum") and ctx.curriculum else ""
        stage_title = (ctx.lesson.stage_title or "") if hasattr(ctx, "lesson") and ctx.lesson else ""

        full_search_text = f"{topic_text} {raw_topic} {chapter_text} {stage_title}".lower()

        # 1. Comparison: explicit comparison keywords take precedence
        comparison_patterns = [
            r"\bvs\b", r"\bvs\.\b", r"\bversus\b",
            r"\bdifference\b", r"\bdifferences\b",
            r"\bcompare\b", r"\bcomparison\b",
            r"\bdistinguish\b", r"\bcontrast\b",
            r"\btypes of\b", r"\btypes\b"
        ]
        if any(re.search(p, full_search_text) for p in comparison_patterns):
            return TopicCategory.COMPARISON

        # 2. Chronological: history, evolution, timelines
        chronological_patterns = [
            r"\btimeline\b", r"\bhistory\b", r"\bchronolog\w*\b",
            r"\bevolution\b", r"\bdynasty\b", r"\brevolution\b",
            r"\bperiod\b", r"\bcenturies\b", r"\bera\b"
        ]
        if any(re.search(p, full_search_text) for p in chronological_patterns):
            return TopicCategory.CHRONOLOGICAL

        # 3. Cause and Effect: environmental, impacts, consequences
        cause_effect_patterns = [
            r"\bcause\s+and\s+effect\b", r"\bcauses\s+of\b",
            r"\bimpact\s+of\b", r"\beffects\s+of\b", r"\bconsequences\b",
            r"\bglobal\s+warming\b", r"\bpollution\b", r"\bgreenhouse\s+effect\b",
            r"\bclimate\s+change\b"
        ]
        if any(re.search(p, full_search_text) for p in cause_effect_patterns):
            return TopicCategory.CAUSE_EFFECT

        # 4. Process: cyclical, biological, or biochemical mechanisms
        process_patterns = [
            r"\bcycle\b", r"\bphotosynthesis\b", r"\bdigestion\b",
            r"\brespiration\b", r"\bprocess\b", r"\bstages\b",
            r"\bsteps\s+of\b", r"\bpathway\b", r"\bmechanism\b",
            r"\bworkflow\b", r"\bwater\s+cycle\b", r"\bnitrogen\s+cycle\b",
            r"\bcarbon\s+cycle\b", r"\bkrebs\s+cycle\b", r"\btranscription\b",
            r"\btranslation\b", r"\breplication\b", r"\bmetamorphosis\b"
        ]
        if any(re.search(p, full_search_text) for p in process_patterns):
            return TopicCategory.PROCESS

        # 5. Formula-heavy: mathematical, physics kinematics/equations, chemical stoichiometry
        formula_patterns = [
            r"\bquadratic\s+equations?\b", r"\bkinematics\b",
            r"\bequations?\b", r"\bformulas?\b", r"\bderivations?\b",
            r"\btheorems?\b", r"\bcalculus\b", r"\btrigonometry\b",
            r"\balgebra\b", r"\bstoichiometry\b", r"\bvectors\b",
            r"\barithmetic\s+progression\b", r"\belectrostatics\b",
            r"\bcurrent\s+electricity\b", r"\bohms?\s+law\b"
        ]
        if any(re.search(p, full_search_text) for p in formula_patterns):
            return TopicCategory.FORMULA_HEAVY

        # 6. Conceptual: fundamental theories, laws, principles
        conceptual_patterns = [
            r"\bnewton's\s+laws?\b", r"\blaws?\s+of\s+motion\b",
            r"\btheory\b", r"\bconcept\s+of\b", r"\bnature\s+of\b",
            r"\bprinciple\s+of\b", r"\brelativity\b", r"\bquantum\b",
            r"\batomic\s+structure\b", r"\bgravity\b", r"\bgravitation\b",
            r"\binertia\b"
        ]
        if any(re.search(p, full_search_text) for p in conceptual_patterns):
            return TopicCategory.CONCEPTUAL

        # 7. Problem Solving: practice problems, numericals
        problem_solving_patterns = [
            r"\bword\s+problems?\b", r"\bproblem\s+solving\b",
            r"\bnumerical\s+problems?\b", r"\bnumericals?\b"
        ]
        if any(re.search(p, full_search_text) for p in problem_solving_patterns):
            return TopicCategory.PROBLEM_SOLVING

        # 8. Procedural: experiments, labs, algorithms
        procedural_patterns = [
            r"\blaboratory\b", r"\bexperiment\w*\b", r"\bprocedure\b",
            r"\bmethod\b", r"\balgorithm\b", r"\bprotocol\b"
        ]
        if any(re.search(p, full_search_text) for p in procedural_patterns):
            return TopicCategory.PROCEDURAL

        # 9. Definition-heavy: glossaries, nomenclature
        definition_patterns = [
            r"\bdefinitions?\b", r"\bglossary\b", r"\bterminology\b",
            r"\bnomenclature\b"
        ]
        if any(re.search(p, full_search_text) for p in definition_patterns):
            return TopicCategory.DEFINITION_HEAVY

        # Subject-based fallbacks for known quantitative subjects
        if subject_text in ["mathematics", "math"]:
            return TopicCategory.FORMULA_HEAVY

        # Default fallback
        return TopicCategory.UNKNOWN
