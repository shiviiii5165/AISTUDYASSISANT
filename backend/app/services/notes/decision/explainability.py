"""
LearnByGenie Notes Decision Engine — Explainability & Traceability Engine
======================================================================
Produces deterministic decision explanations, aggregated evidence summaries,
competing candidate traces with winning precedence, and decision confidence.
"""
from typing import Dict, Any, List, Optional
from app.services.notes.context.schemas import CanonicalNotesContext
from .schemas import DecisionReason, DecisionTraceItem
from .policies import MasteryBracket, TopicCategory, DecisionPrecedence


class ExplainabilityEngine:
    """Builds transparent explainability records and decision traces."""

    @classmethod
    def compile_evidence(
        cls,
        ctx: CanonicalNotesContext,
        topic_category: TopicCategory,
        avg_mastery: Optional[float],
        exam_state: Optional[str] = None
    ) -> Dict[str, Any]:
        """Collects all resolved pedagogical signals into a single structured evidence dictionary."""
        return {
            "topic": ctx.topic,
            "raw_topic": ctx.raw_topic,
            "class_level": ctx.class_level,
            "subject": ctx.subject,
            "curriculum": (
                ctx.resolved_context.curriculum
                if getattr(ctx, "resolved_context", None) and ctx.resolved_context.curriculum
                else str(ctx.curriculum)
            ),
            "mastery": avg_mastery,
            "misconceptions": list(dict.fromkeys(ctx.student_misconceptions + ctx.expected_misconceptions)),
            "weak_concepts": list(dict.fromkeys(ctx.weak_concepts)),
            "teaching_method": (
                ctx.resolved_context.teaching_method
                if getattr(ctx, "resolved_context", None) and ctx.resolved_context.teaching_method
                else (ctx.lesson.teaching_method if hasattr(ctx, "lesson") and ctx.lesson else "unknown")
            ),
            "topic_category": topic_category.value,
            "user_instructions": ctx.explicit_user_instructions,
            "exam_state": exam_state
        }

    @classmethod
    def compute_decision_confidence(
        cls,
        ctx: CanonicalNotesContext,
        avg_mastery: Optional[float]
    ) -> float:
        """
        Calculates how strongly the available evidence supports the decision.
        Deterministic score from 0.0 to 1.0, separate from Step 1 source reliability.
        """
        score = 0.50  # Base confidence for minimum viable topic
        if ctx.topic:
            score += 0.15
        if ctx.class_level:
            score += 0.10
        if ctx.subject and ctx.subject.lower() != "general":
            score += 0.05
        if avg_mastery is not None:
            score += 0.10
        if ctx.student_misconceptions or ctx.expected_misconceptions:
            score += 0.05
        if hasattr(ctx, "lesson") and ctx.lesson and ctx.lesson.learning_objectives:
            score += 0.05

        return round(min(1.0, max(0.1, score)), 2)

    @classmethod
    def build_trace_and_reasons(
        cls,
        ctx: CanonicalNotesContext,
        topic_category: TopicCategory,
        mastery_bracket: MasteryBracket,
        avg_mastery: Optional[float],
        primary_purpose: str,
        secondary_purposes: List[str],
        difficulty: str,
        depth: str,
        mode: str,
        remediation_required: bool,
        remediation_priority: str,
        exam_state: Optional[str] = None
    ) -> tuple[List[DecisionReason], List[DecisionTraceItem]]:
        """Constructs deterministic decision reasons and precedence traces."""
        reasons: List[DecisionReason] = []
        trace: List[DecisionTraceItem] = []

        # ── 1. Purpose Decision & Trace ──
        purpose_candidates = ["learning"]
        if avg_mastery is not None and avg_mastery < 0.40:
            purpose_candidates.append("remediation")
        if exam_state or "exam" in (ctx.topic + " " + (ctx.explicit_user_instructions or "")).lower():
            purpose_candidates.append("exam_preparation")
        if "revision" in (ctx.topic + " " + (ctx.explicit_user_instructions or "")).lower():
            purpose_candidates.append("revision")

        purpose_candidates = sorted(list(dict.fromkeys(purpose_candidates)))

        purpose_evidence = [{"source": "explicit_input", "field": "topic", "value": ctx.topic}]
        if avg_mastery is not None:
            purpose_evidence.append({"source": "assessment", "field": "mastery", "value": avg_mastery})
        if exam_state:
            purpose_evidence.append({"source": "assessment", "field": "exam_state", "value": exam_state})
        if ctx.explicit_user_instructions:
            purpose_evidence.append({"source": "explicit_input", "field": "instructions", "value": ctx.explicit_user_instructions})

        if primary_purpose == "exam_preparation":
            purpose_reason = "Explicit exam state or exam request takes precedence over general learning."
        elif primary_purpose == "remediation":
            purpose_reason = f"Student mastery is {avg_mastery if avg_mastery is not None else 'low'}, requiring targeted remediation."
        elif primary_purpose == "revision":
            purpose_reason = "Revision intent specified in context or user instruction."
        else:
            purpose_reason = "Standard learning purpose selected as neutral default for curriculum mastery."

        reasons.append(DecisionReason(
            decision=f"purpose_{primary_purpose}",
            reason=purpose_reason,
            evidence=purpose_evidence
        ))

        trace.append(DecisionTraceItem(
            decision="primary_purpose",
            candidates=purpose_candidates,
            winning_candidate=primary_purpose,
            reason=purpose_reason,
            evidence=purpose_evidence
        ))

        # ── 2. Difficulty Decision & Trace ──
        difficulty_candidates = ["foundational", "standard", "advanced"]
        diff_evidence = [{"source": "explicit_input", "field": "class_level", "value": ctx.class_level}]
        if avg_mastery is not None:
            diff_evidence.append({"source": "assessment", "field": "mastery", "value": avg_mastery})

        if mastery_bracket == MasteryBracket.LOW:
            diff_reason = f"Mastery is {avg_mastery}, requiring foundational scaffolding."
        elif mastery_bracket == MasteryBracket.HIGH:
            diff_reason = f"Mastery is {avg_mastery} (>= 0.75), supporting advanced application."
        else:
            diff_reason = f"Grade level {ctx.class_level} and neutral context support standard difficulty."

        reasons.append(DecisionReason(
            decision=f"difficulty_{difficulty}",
            reason=diff_reason,
            evidence=diff_evidence
        ))

        trace.append(DecisionTraceItem(
            decision="difficulty",
            candidates=difficulty_candidates,
            winning_candidate=difficulty,
            reason=diff_reason,
            evidence=diff_evidence
        ))

        # ── 3. Teaching Strategy Mode ──
        strat_candidates = ["active", "passive", "balanced"]
        strat_evidence = [{
            "source": "lesson",
            "field": "teaching_method",
            "value": (
                ctx.resolved_context.teaching_method
                if getattr(ctx, "resolved_context", None) and ctx.resolved_context.teaching_method
                else (ctx.lesson.teaching_method if hasattr(ctx, "lesson") and ctx.lesson else "unknown")
            )
        }]

        if mode == "active":
            strat_reason = "Lesson teaching method indicates active inquiry, requiring thinking checkpoints and application."
        elif mode == "passive":
            strat_reason = "Lesson context indicates direct lecture, selecting structured sequential exposition."
        else:
            strat_reason = "Teaching method unknown; selected balanced pedagogical strategy."

        reasons.append(DecisionReason(
            decision=f"teaching_mode_{mode}",
            reason=strat_reason,
            evidence=strat_evidence
        ))

        trace.append(DecisionTraceItem(
            decision="teaching_mode",
            candidates=strat_candidates,
            winning_candidate=mode,
            reason=strat_reason,
            evidence=strat_evidence
        ))

        # ── 4. Remediation Decision ──
        if remediation_required:
            rem_evidence = []
            if ctx.student_misconceptions:
                rem_evidence.append({"source": "student", "field": "misconceptions", "value": ctx.student_misconceptions})
            if ctx.expected_misconceptions:
                rem_evidence.append({"source": "lesson", "field": "expected_misconceptions", "value": ctx.expected_misconceptions})
            if avg_mastery is not None:
                rem_evidence.append({"source": "assessment", "field": "mastery", "value": avg_mastery})

            rem_reason = f"Remediation enabled with {remediation_priority} priority due to diagnosed misconceptions or low mastery."
            reasons.append(DecisionReason(
                decision="remediation_enabled",
                reason=rem_reason,
                evidence=rem_evidence
            ))

        return reasons, trace
