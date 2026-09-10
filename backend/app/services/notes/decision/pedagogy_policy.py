"""
TeachGenie Notes Decision Engine — Pedagogy Policy Engine
=========================================================
Formulates teaching strategies (active, passive, balanced) and
grade/curriculum-appropriate pedagogical tone instructions.
"""
from typing import List, Dict, Any, Optional
from app.services.notes.context.schemas import CanonicalNotesContext
from .schemas import TeachingStrategyPlan
from .policies import GradePolicy, MasteryBracket


class PedagogyPolicyEngine:
    """Constructs structured pedagogical plans and grade-appropriate tone directives."""

    @classmethod
    def evaluate(
        cls,
        ctx: CanonicalNotesContext,
        class_num: int,
        mastery_bracket: MasteryBracket,
        base_scaffolding: str
    ) -> TeachingStrategyPlan:
        """
        Determines pedagogical mode, scaffolding level, feature checklist,
        and rich tone instructions.
        """
        teaching_method = "unknown"
        if getattr(ctx, "resolved_context", None) and ctx.resolved_context.teaching_method and ctx.resolved_context.teaching_method != "unknown":
            teaching_method = ctx.resolved_context.teaching_method
        elif hasattr(ctx, "lesson") and ctx.lesson and ctx.lesson.teaching_method and ctx.lesson.teaching_method != "unknown":
            teaching_method = ctx.lesson.teaching_method

        method_lower = (teaching_method or "unknown").lower()

        # ── 1. Active vs Passive vs Balanced Mode ──
        if any(k in method_lower for k in ["active", "inquiry", "hands-on", "experiment", "interactive", "flipped", "discussion"]):
            mode = "active"
            features = [
                "thinking_checkpoints",
                "application",
                "practice",
                "misconception_reflection",
                "inquiry_prompts"
            ]
        elif any(k in method_lower for k in ["passive", "lecture", "direct_instruction", "traditional", "reading"]):
            mode = "passive"
            features = [
                "structured_explanation",
                "examples",
                "key_points",
                "summary"
            ]
        else:
            # UNKNOWN Context: Choose neutral balanced strategy. NEVER assume passive!
            mode = "balanced"
            features = [
                "guided_explanation",
                "examples",
                "thinking_checkpoints",
                "key_points",
                "practice"
            ]

        # Combine mode features with mastery scaffolding features
        combined_features = list(features)
        if mastery_bracket == MasteryBracket.LOW:
            combined_features.extend([
                "guided_explanation",
                "step_by_step_scaffolding",
                "worked_examples",
                "misconception_correction",
                "concrete_analogies"
            ])
        elif mastery_bracket == MasteryBracket.HIGH:
            combined_features.extend([
                "concise_explanation",
                "application_focus",
                "tricky_cases",
                "advanced_practice",
                "reduced_repetition"
            ])

        final_features = list(dict.fromkeys(combined_features))


        # ── 2. Scaffolding level ──
        # Can be guided/intensive if low mastery, minimal if high mastery, or base_scaffolding
        scaffolding = base_scaffolding

        # ── 3. Tone Instructions (Grade and Board Scaffolding) ──
        curriculum_str = (
            ctx.resolved_context.curriculum
            if getattr(ctx, "resolved_context", None) and ctx.resolved_context.curriculum
            else (ctx.curriculum.board if hasattr(ctx.curriculum, "board") and ctx.curriculum.board else str(ctx.curriculum or "CBSE"))
        )

        if class_num <= 5:
            tone = (
                f"Target audience is young children in {ctx.class_level} (ages 8-10). "
                "Use simple everyday vocabulary, friendly conversational tone, clear real-world analogies, "
                "and short engaging paragraphs. Avoid dense technical jargon."
            )
        elif class_num <= 8:
            tone = (
                f"Target audience is middle school students in {ctx.class_level} (ages 11-13). "
                "Explain concepts with clear step-by-step examples, relatable analogies, and structured bullet points. "
                "Define scientific/mathematical terms gently."
            )
        elif class_num <= 10:
            tone = (
                f"Target audience is secondary school students in {ctx.class_level} (Board: {curriculum_str}). "
                "Focus on crisp textbook definitions, board exam relevance, key formulas, and common student pitfalls. "
                "Ensure high academic accuracy."
            )
        else:  # Class 11-12
            tone = (
                f"Target audience is senior secondary students in {ctx.class_level} preparing for {curriculum_str} and competitive exams. "
                "Provide rigorous conceptual depth, formal definitions, step-by-step mathematical derivations, boundary conditions, "
                "and real-world application edge cases."
            )

        if mode == "active":
            tone += " Incorporate active thinking checkpoints and reflective questions to provoke critical reasoning."
        elif mode == "passive":
            tone += " Present knowledge sequentially with structured exposition and clear hierarchical headers."

        return TeachingStrategyPlan(
            mode=mode,
            scaffolding=scaffolding,
            features=final_features,
            tone_instructions=tone
        )
