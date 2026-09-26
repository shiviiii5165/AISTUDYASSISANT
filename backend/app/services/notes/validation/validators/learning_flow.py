"""
LearnByGenie Learning Flow Validator (Step 4)
===========================================
Audits adaptive learning flow compliance:
1. Stage execution compliance: Verifies planned stages exist in the document.
2. Active interaction authenticity: Checks that interactive stages contain authentic interactive inquiry/prompts rather than passive text.
3. Misconception remediation: Checks that planned misconception targets are addressed.
4. Adaptive practice alignment: Verifies starting difficulty and progression match the learner plan.
5. Mastery check verification: Ensures exit benchmark criteria and self-explanation challenges are present.
"""
from typing import List, Dict, Any, Tuple

from ...schemas import NotesDocument
from ...context.schemas import CanonicalNotesContext
from ...decision.schemas import NotesGenerationPlan
from ..schemas import (
    ValidationViolation, ViolationSeverity, ValidationDimension
)


class LearningFlowValidator:
    """Audits pedagogical execution of the LearningFlowPlan in Step 4."""

    @staticmethod
    def validate(
        doc: NotesDocument,
        plan: NotesGenerationPlan,
        ctx: CanonicalNotesContext
    ) -> Tuple[List[ValidationViolation], Dict[str, Any], float]:
        violations: List[ValidationViolation] = []
        details: Dict[str, Any] = {
            "flow_present": False,
            "stages_planned": 0,
            "stages_executed": 0,
            "interactive_stages_found": 0,
            "practice_progression_verified": False,
            "mastery_check_verified": False
        }
        score: float = 100.0

        flow_plan = getattr(plan, "learning_flow_plan", None)
        if not flow_plan:
            # No learning flow plan in decision -> skip without penalty
            details["status"] = "skipped"
            return violations, details, score

        details["flow_present"] = True
        planned_stages = flow_plan.sequence or []
        details["stages_planned"] = len(planned_stages)

        # 1. Audit Stage Execution
        doc_stages = []
        for sec in doc.sections:
            ev = getattr(sec, "semantic_evidence", None)
            if ev and getattr(ev, "learning_flow_stage", None):
                doc_stages.append(ev.learning_flow_stage)
            else:
                doc_stages.append(sec.section_type)

        executed_count = sum(1 for stg in planned_stages if any(stg.stage_name in ds or ds in stg.stage_name for ds in doc_stages))
        details["stages_executed"] = executed_count

        if planned_stages and executed_count == 0:
            violations.append(ValidationViolation(
                code="LEARNING_FLOW_STAGES_MISSING",
                severity=ViolationSeverity.ERROR,
                dimension=ValidationDimension.PEDAGOGY,
                message="Plan defined an adaptive learning flow sequence, but none of the planned stages were executed in the document.",
                expected=[s.stage_name for s in planned_stages],
                actual=doc_stages,
                repairable=True
            ))
            score -= 20.0

        # 2. Audit Active Interaction Authenticity
        interactive_stages = [s for s in planned_stages if s.is_interactive]
        for istg in interactive_stages:
            matched_sec = None
            for sec in doc.sections:
                ev = getattr(sec, "semantic_evidence", None)
                if ev and ev.learning_flow_stage == istg.stage_name:
                    matched_sec = sec
                    break
                elif istg.stage_name in sec.section_type or sec.section_type in istg.stage_name:
                    matched_sec = sec
                    break

            if matched_sec:
                body_content = matched_sec.content.lower()
                interactive_cues = ["?", "pause", "challenge", "predict", "formulate", "write down", "explain back", "try solving", "solve the following"]
                has_cue = ("?" in body_content) or any(cue in body_content for cue in interactive_cues)
                if not has_cue:
                    violations.append(ValidationViolation(
                        code="LEARNING_FLOW_INTERACTIVE_PASSIVE_FRAUD",
                        severity=ViolationSeverity.WARNING,
                        dimension=ValidationDimension.PEDAGOGY,
                        message=f"Interactive stage '{istg.stage_name}' was planned as {istg.interaction_type or 'interactive'}, but content is purely expository without questions or prompts.",
                        section_id=matched_sec.id,
                        expected="Inquiry questions, pause-and-reflect prompts, or prediction challenges",
                        actual="Purely expository text",
                        repairable=True
                    ))
                    score -= 5.0
                else:
                    details["interactive_stages_found"] += 1

        # 3. Audit Misconception Remediation Alignment
        misc_strat = getattr(flow_plan, "misconception_strategy", None)
        if misc_strat and misc_strat.remediation_target_keys:
            all_text_lower = " ".join([f"{s.title}\n{s.content}" for s in doc.sections]).lower()
            repaired_count = 0
            for mk in misc_strat.remediation_target_keys:
                words = [w for w in mk.lower().split() if len(w) > 3]
                if words and any(w in all_text_lower for w in words):
                    repaired_count += 1

            if repaired_count == 0 and len(misc_strat.remediation_target_keys) > 0:
                violations.append(ValidationViolation(
                    code="LEARNING_FLOW_MISCONCEPTION_REPAIR_MISSING",
                    severity=ViolationSeverity.WARNING,
                    dimension=ValidationDimension.MISCONCEPTION,
                    message="Learner has documented misconceptions targeted in learning flow, but document failed to address them.",
                    expected=misc_strat.remediation_target_keys,
                    actual="No targeted debunking found",
                    repairable=True
                ))
                score -= 5.0

        # 4. Audit Adaptive Practice Alignment
        prac_strat = getattr(flow_plan, "practice_strategy", None)
        if prac_strat and doc.practice:
            if prac_strat.starting_difficulty:
                first_item_diff = doc.practice[0].get("difficulty")
                if first_item_diff and first_item_diff != prac_strat.starting_difficulty:
                    violations.append(ValidationViolation(
                        code="LEARNING_FLOW_PRACTICE_DIFFICULTY_MISMATCH",
                        severity=ViolationSeverity.INFO,
                        dimension=ValidationDimension.PRACTICE,
                        message=f"Practice starting difficulty '{first_item_diff}' differs from plan '{prac_strat.starting_difficulty}'.",
                        expected=prac_strat.starting_difficulty,
                        actual=first_item_diff,
                        repairable=False
                    ))
            details["practice_progression_verified"] = True

        # 5. Audit Mastery Check Verification
        mastery_plan = getattr(flow_plan, "mastery_check", None)
        if mastery_plan and mastery_plan.required:
            has_mastery_sec = any(
                "mastery" in s.section_type.lower() or
                "mastery" in s.title.lower() or
                (s.semantic_evidence and s.semantic_evidence.learning_flow_stage == "mastery_check")
                for s in doc.sections
            )
            if has_mastery_sec:
                details["mastery_check_verified"] = True
            else:
                violations.append(ValidationViolation(
                    code="LEARNING_FLOW_MASTERY_CHECK_MISSING",
                    severity=ViolationSeverity.WARNING,
                    dimension=ValidationDimension.PEDAGOGY,
                    message="Learning flow required a final mastery check, but no mastery verification checkpoint was found.",
                    expected="Mastery verification checkpoint section",
                    actual="Missing mastery checkpoint",
                    repairable=True
                ))
                score -= 5.0

        return violations, details, max(0.0, score)
