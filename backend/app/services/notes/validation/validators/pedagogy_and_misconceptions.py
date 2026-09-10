"""
Pedagogical & Misconception Validator
=====================================
Audits teaching strategy compliance (active vs passive, remediation scaffolding)
and verifies that targeted misconceptions are scientifically corrected rather than
reinforced or omitted.
"""
from typing import List, Dict, Any, Tuple
import re

from ...schemas import NotesDocument
from ...context.schemas import CanonicalNotesContext
from ...decision.schemas import NotesGenerationPlan
from ..schemas import (
    ValidationViolation, ViolationSeverity, ValidationDimension
)


class PedagogyAndMisconceptionValidator:
    """Evaluates pedagogical strategies, scaffolding depth, and misconception debunking."""

    @staticmethod
    def validate(
        doc: NotesDocument,
        plan: NotesGenerationPlan,
        ctx: CanonicalNotesContext
    ) -> Tuple[List[ValidationViolation], Dict[str, Any], float]:
        violations: List[ValidationViolation] = []
        details: Dict[str, Any] = {"misconception_findings": [], "pedagogy_mode": None}
        score: float = 100.0

        all_text = " ".join([f"{s.title}\n{s.content}" for s in doc.sections])
        all_text_lower = all_text.lower()

        # ── 1. Teaching Strategy Validation ──
        strategy_mode = getattr(plan.teaching_strategy, "mode", "neutral")
        details["pedagogy_mode"] = strategy_mode

        if strategy_mode == "active":
            # Active learning requires interactive checkpoints, pause-and-reflect, or practice prompt checks
            has_active_elements = (
                any("checkpoint" in s.section_type or "checkpoint" in s.title.lower() or "practice" in s.section_type for s in doc.sections) or
                any("?" in s.content for s in doc.sections) or
                any(c.type in ("tip", "warning") for s in doc.sections for c in s.callouts)
            )
            if not has_active_elements:
                violations.append(ValidationViolation(
                    code="PEDAGOGY_ACTIVE_STRATEGY_MISMATCH",
                    severity=ViolationSeverity.ERROR,
                    dimension=ValidationDimension.PEDAGOGY,
                    message="Plan specifies 'active' teaching strategy, but document provides purely passive expository text with no checkpoints or interactive reflections.",
                    expected="Active checkpoints, prompt questions, or reflection exercises",
                    actual="Passive expository text",
                    repairable=True
                ))
                score -= 15.0

        elif strategy_mode == "passive":
            # Passive learning expects clear, structured, narrative exposition without excessive checkpoint interruption
            pass

        # ── 2. High Mastery Repetition Check (Spec 19) ──
        mastery_vals = []
        if getattr(ctx, "student", None) and getattr(ctx.student, "current_learning_state", None):
            cls_dict = ctx.student.current_learning_state.get("mastery", {})
            if isinstance(cls_dict, dict):
                mastery_vals.extend([float(v) for v in cls_dict.values() if isinstance(v, (int, float))])

        if not mastery_vals and getattr(ctx, "resolved_context", None) and getattr(ctx.resolved_context, "mastery_state", None):
            mastery_vals.extend([float(v) for v in ctx.resolved_context.mastery_state.values() if isinstance(v, (int, float))])

        if not mastery_vals and getattr(ctx, "student_mastery", None):
            mastery_vals.extend([float(v) for v in ctx.student_mastery.values() if isinstance(v, (int, float))])

        if mastery_vals and sum(mastery_vals)/len(mastery_vals) > 0.85:
            # High mastery student: check for redundant elementary definitions
            elementary_phrases = ["let us first define what a force is in everyday life", "as you know from simple basics"]
            if any(p in all_text_lower for p in elementary_phrases):
                violations.append(ValidationViolation(
                    code="HIGH_MASTERY_REPETITION_WARNING",
                    severity=ViolationSeverity.WARNING,
                    dimension=ValidationDimension.PEDAGOGY,
                    message="Student has high topic mastery, but notes contain repetitive elementary phrasing.",
                    expected="Concise or advanced direct exposition",
                    actual="Repetitive foundational analogies",
                    repairable=True
                ))
                score -= 5.0

        # ── 3. Remediation & Misconception Validation (Spec 10 & 18) ──
        target_misconceptions = []
        if plan.remediation_plan.required and plan.remediation_plan.target_concepts:
            target_misconceptions.extend(plan.remediation_plan.target_concepts)
        elif getattr(ctx, "student_misconceptions", None):
            target_misconceptions.extend(ctx.student_misconceptions)
        elif getattr(ctx, "resolved_context", None) and getattr(ctx.resolved_context, "misconceptions", None):
            target_misconceptions.extend(ctx.resolved_context.misconceptions)

        # Include canonical universal misconceptions if present in text
        canonical_misconceptions = [
            "inertia is a force",
            "heavier objects fall faster",
            "action and reaction forces cancel each other out",
            "action and reaction cancel"
        ]
        all_misconceptions_to_check = list(dict.fromkeys(target_misconceptions))
        for cm in canonical_misconceptions:
            if cm in all_text_lower and cm not in all_misconceptions_to_check:
                all_misconceptions_to_check.append(cm)

        for m in all_misconceptions_to_check:
            m_clean = m.strip().lower()
            if not m_clean:
                continue

            # Check if misconception is present in text
            m_words = [w for w in re.findall(r'\w+', m_clean) if len(w) > 3]
            words_present = sum(1 for w in m_words if w in all_text_lower)
            # Require all significant words of the misconception to be present
            addressed = (words_present == len(m_words)) or (m_clean in all_text_lower)

            if not addressed and m in target_misconceptions:
                violations.append(ValidationViolation(
                    code="REQUIRED_MISCONCEPTION_OMITTED",
                    severity=ViolationSeverity.ERROR,
                    dimension=ValidationDimension.MISCONCEPTION,
                    message=f"Mandatory misconception '{m}' was not addressed in the document.",
                    expected=f"Explicit debunking and correction of '{m}'",
                    actual="Not found in notes",
                    repairable=True
                ))
                score -= 20.0
                continue

            # Critical check: MISCONCEPTION REINFORCEMENT DETECTION!
            # Example: "Inertia is a force"
            # If text literally states "inertia is a force" without negation ("not", "never", "incorrect", "misconception", "mistakenly")
            if m_clean in all_text_lower:
                # Look for surrounding sentences
                reinforcing = False
                sentences = re.split(r'[\.\n;]', all_text)
                for sent in sentences:
                    s_low = sent.lower()
                    if m_clean in s_low:
                        # Check if negated or framed as misconception
                        negations = ["not", "never", "incorrect", "misconception", "false", "mistake", "mistakenly", "wrongly", "confuse", "rather than"]
                        if not any(neg in s_low for neg in negations):
                            reinforcing = True
                            violations.append(ValidationViolation(
                                code="MISCONCEPTION_REINFORCEMENT",
                                severity=ViolationSeverity.CRITICAL,
                                dimension=ValidationDimension.MISCONCEPTION,
                                message=f"CRITICAL PEDAGOGICAL ERROR: Document reinforces the known misconception '{m}' as a factual truth: \"{sent.strip()}\".",
                                evidence=sent.strip(),
                                expected=f"Correction clarifying that '{m}' is false",
                                actual=sent.strip(),
                                repairable=True
                            ))
                            score -= 35.0
                            break
                if not reinforcing and m in target_misconceptions:
                    details["misconception_findings"].append({
                        "misconception": m,
                        "status": "correctly_debunked"
                    })
            elif m in target_misconceptions:
                details["misconception_findings"].append({
                    "misconception": m,
                    "status": "addressed"
                })

        return violations, details, max(0.0, min(100.0, score))
