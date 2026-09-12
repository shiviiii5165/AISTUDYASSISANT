"""
TeachGenie Notes Validation Engine — Core Engine (Step 4)
=========================================================
Central quality gate coordinating deterministic checks, plan compliance audits,
factual/formula verifications, curriculum alignment, and targeted AI semantic judging.
Strict Invariants:
1. Step 4 is 100% observational: never mutates context, plan, or document.
2. Zero decision leakage: does not alter mastery, change difficulty, or pick pedagogical strategy.
3. Deterministic first: fast arithmetic, formula, citation, and blueprint checks precede LLM judge.
4. Critical violations cannot be overridden by high numeric dimension scores.
5. Dimension statuses distinguish PASSED, FAILED, WARNING, UNAVAILABLE.
"""
import logging
import time
import copy
from typing import Optional, Dict, Any, List

from ..schemas import NotesDocument
from ..context.schemas import CanonicalNotesContext
from ..decision.schemas import NotesGenerationPlan
from ..generation.schemas import GroundedSources
from .schemas import (
    ValidationResult, ValidationStatus, ViolationSeverity,
    ValidationDimension, ValidationViolation, RepairRecommendation,
    RepairAction, RepairTarget, DimensionStatus
)
from .validators.plan_compliance import PlanComplianceValidator
from .validators.factual_and_formulas import FactualAndFormulaValidator
from .validators.source_grounding import SourceGroundingValidator
from .validators.curriculum import CurriculumValidator
from .validators.pedagogy_and_misconceptions import PedagogyAndMisconceptionValidator
from .validators.practice_and_visual import PracticeAndVisualValidator
from .validators.learning_flow import LearningFlowValidator
from .judge import SemanticJudge

logger = logging.getLogger("teachgenie.notes.validation.engine")


async def validate_notes(
    context: CanonicalNotesContext,
    plan: NotesGenerationPlan,
    document: NotesDocument,
    sources: Optional[GroundedSources] = None,
    enable_llm: bool = True
) -> ValidationResult:
    """
    Step 4 Core Quality Gate Pipeline.
    Evaluates a generated NotesDocument against canonical context, authoritative plan,
    and grounded sources. Step 4 is strictly observational and produces zero side-effects.
    """
    start_time = time.perf_counter()
    violations: List[ValidationViolation] = []
    warnings: List[str] = []
    dimension_scores: Dict[str, float] = {}
    dimension_statuses: Dict[str, DimensionStatus] = {}

    logger.info(f"[ValidationEngine] Initiating validation for doc '{document.id}' on topic '{document.topic}'")

    # ── 1. Structural & Schema Validation (Deterministic) ──
    schema_score = 100.0
    if not document.id:
        violations.append(ValidationViolation(
            code="SCHEMA_DOCUMENT_ID_MISSING",
            severity=ViolationSeverity.CRITICAL,
            dimension=ValidationDimension.SCHEMA,
            message="Document ID is missing or null.",
            expected="Valid document ID string",
            actual=None,
            repairable=False
        ))
        schema_score -= 30.0

    if not document.sections:
        violations.append(ValidationViolation(
            code="SCHEMA_SECTIONS_EMPTY",
            severity=ViolationSeverity.CRITICAL,
            dimension=ValidationDimension.SCHEMA,
            message="Document contains no content sections.",
            expected="At least one pedagogical section",
            actual="0 sections",
            repairable=True
        ))
        schema_score -= 50.0

    # Duplicate sections check
    seen_sigs = set()
    for s in document.sections:
        sig = f"{s.section_type}:{s.title.strip().lower()}"
        if sig in seen_sigs:
            violations.append(ValidationViolation(
                code="STRUCTURAL_DUPLICATE_SECTION",
                severity=ViolationSeverity.WARNING,
                dimension=ValidationDimension.STRUCTURAL,
                message=f"Duplicate section detected: '{s.title}' ({s.section_type}).",
                section_id=s.id,
                expected="Unique pedagogical sections",
                actual=sig,
                repairable=True
            ))
            schema_score -= 5.0
        seen_sigs.add(sig)

    # Empty sections check
    for s in document.sections:
        if len(s.content.strip()) < 15 and s.section_type != "quick_summary":
            violations.append(ValidationViolation(
                code="STRUCTURAL_SECTION_CONTENT_EMPTY",
                severity=ViolationSeverity.ERROR,
                dimension=ValidationDimension.STRUCTURAL,
                message=f"Section '{s.title}' contains virtually empty or stub content ({len(s.content.strip())} chars).",
                section_id=s.id,
                expected="Meaningful expository content",
                actual=s.content,
                repairable=True
            ))
            schema_score -= 15.0

    dimension_scores["schema"] = max(0.0, schema_score)

    # ── 2. Plan Compliance Validation ──
    plan_viols, plan_details, plan_score = PlanComplianceValidator.validate(document, plan, context)
    violations.extend(plan_viols)
    dimension_scores["plan_compliance"] = plan_score

    # ── 3. Source Grounding & Provenance Validation ──
    grounding_viols, grounding_details, grounding_score = SourceGroundingValidator.validate(document, context, sources)
    violations.extend(grounding_viols)
    dimension_scores["grounding"] = grounding_score

    # ── 4. Deterministic Factual & Formula Validation ──
    factual_viols, factual_details, factual_score = FactualAndFormulaValidator.validate(document, plan)
    violations.extend(factual_viols)
    dimension_scores["factual"] = factual_score

    # ── 5. Curriculum & Grade-Level Scope Validation ──
    curr_viols, curr_details, curr_score = CurriculumValidator.validate(document, plan, context)
    violations.extend(curr_viols)
    dimension_scores["curriculum"] = curr_score

    # ── 6. Pedagogical Strategy & Misconception Validation ──
    ped_viols, ped_details, ped_score = PedagogyAndMisconceptionValidator.validate(document, plan, context)
    violations.extend(ped_viols)
    dimension_scores["pedagogy"] = ped_score

    # ── 7. Practice Quality & Visual Integrity Validation ──
    prac_viols, prac_details, prac_score = PracticeAndVisualValidator.validate(document, plan, context)
    violations.extend(prac_viols)
    dimension_scores["practice_and_visual"] = prac_score

    # ── 7b. Learning Flow & Adaptation Validation ──
    flow_viols, flow_details, flow_score = LearningFlowValidator.validate(document, plan, context)
    violations.extend(flow_viols)
    if getattr(plan, "learning_flow_plan", None):
        dimension_scores["pedagogy"] = min(dimension_scores["pedagogy"], flow_score)

    # ── 8. Semantic AI Judge (Targeted, Prompt-Injection Defended) ──
    hallucination_details: Dict[str, Any] = {"status": "skipped"}
    if enable_llm:
        if document.sections:
            judge_viols, judge_details, judge_score = await SemanticJudge.evaluate_document(
                document, plan, context, sources
            )
            violations.extend(judge_viols)
            hallucination_details = judge_details
            dimension_scores["factual"] = min(dimension_scores["factual"], judge_details.get("factual_score", 100.0))
            dimension_scores["pedagogy"] = min(dimension_scores["pedagogy"], judge_details.get("pedagogical_score", 100.0))

    # ── 9. Dimension Status Categorization (Spec 14 & 15) ──
    dim_map = {
        "schema": [ValidationDimension.SCHEMA, ValidationDimension.STRUCTURAL],
        "plan_compliance": [ValidationDimension.PLAN_COMPLIANCE],
        "grounding": [ValidationDimension.GROUNDING],
        "factual": [ValidationDimension.FACTUAL, ValidationDimension.FORMULA],
        "curriculum": [ValidationDimension.CURRICULUM],
        "pedagogy": [ValidationDimension.PEDAGOGY, ValidationDimension.MISCONCEPTION],
        "practice_and_visual": [ValidationDimension.PRACTICE, ValidationDimension.VISUAL]
    }

    for dim_name, dim_enums in dim_map.items():
        if dim_name == "curriculum" and curr_details.get("status") == "unavailable":
            dimension_statuses[dim_name] = DimensionStatus.UNAVAILABLE
            continue

        dim_viols = [v for v in violations if v.dimension in dim_enums]
        if any(v.severity in (ViolationSeverity.CRITICAL, ViolationSeverity.ERROR) for v in dim_viols):
            dimension_statuses[dim_name] = DimensionStatus.FAILED
        elif any(v.severity == ViolationSeverity.WARNING for v in dim_viols):
            dimension_statuses[dim_name] = DimensionStatus.WARNING
        else:
            dimension_statuses[dim_name] = DimensionStatus.PASSED

    # ── 10. Scoring & Critical Violation Gating (Spec 39, 40, 58) ──
    weights = {
        "schema": 0.15,
        "plan_compliance": 0.25,
        "grounding": 0.15,
        "factual": 0.20,
        "curriculum": 0.10,
        "pedagogy": 0.15
    }

    # If curriculum is unavailable, exclude it from the active denominator (Spec 14 & 15)
    is_curr_unavailable = (dimension_statuses.get("curriculum") == DimensionStatus.UNAVAILABLE)
    active_weights = {k: v for k, v in weights.items() if not (k == "curriculum" and is_curr_unavailable)}
    total_active_weight = sum(active_weights.values())

    overall_score = 0.0
    for dim, weight in active_weights.items():
        score_val = dimension_scores.get(dim, 100.0)
        overall_score += score_val * (weight / total_active_weight)
    overall_score = round(max(0.0, min(100.0, overall_score)), 2)

    # Collect warnings from non-blocking violation messages
    for v in violations:
        if v.severity == ViolationSeverity.WARNING:
            warnings.append(v.message)
    warnings.extend(document.generation_warnings)
    warnings = list(dict.fromkeys(warnings))

    # Determine Gate Status
    critical_errors = [v for v in violations if v.severity == ViolationSeverity.CRITICAL]
    errors = [v for v in violations if v.severity == ViolationSeverity.ERROR]
    warning_viols = [v for v in violations if v.severity == ViolationSeverity.WARNING]

    if any(v.code == "VALIDATOR_INTERNAL_FAILURE" for v in violations):
        final_status = ValidationStatus.VALIDATION_FAILED
        is_valid = False
    elif critical_errors:
        final_status = ValidationStatus.INVALID
        is_valid = False
    elif errors:
        if all(v.repairable for v in errors):
            final_status = ValidationStatus.REPAIRABLE
            is_valid = False
        else:
            final_status = ValidationStatus.INVALID
            is_valid = False
    elif warning_viols or warnings:
        final_status = ValidationStatus.VALID_WITH_WARNINGS
        is_valid = True
    else:
        final_status = ValidationStatus.VALID
        is_valid = True

    # ── 11. Construct Actionable Repair Recommendation (Spec 29) ──
    repair_rec: Optional[RepairRecommendation] = None
    if final_status == ValidationStatus.REPAIRABLE:
        repair_targets = []
        for err in errors:
            repair_targets.append(RepairTarget(
                section_id=err.section_id,
                reason=err.message,
                violation_code=err.code,
                expected=str(err.expected) if err.expected else None,
                repair_prompt=f"Fix {err.code}: {err.message} (Expected: {err.expected})"
            ))
        repair_rec = RepairRecommendation(
            action=RepairAction.REPAIR,
            targets=repair_targets
        )
    elif final_status == ValidationStatus.INVALID:
        repair_rec = RepairRecommendation(
            action=RepairAction.REJECT,
            targets=[
                RepairTarget(
                    section_id=c.section_id,
                    reason=c.message,
                    violation_code=c.code,
                    expected=str(c.expected) if c.expected else None
                )
                for c in critical_errors
            ]
        )
    elif final_status in (ValidationStatus.VALID, ValidationStatus.VALID_WITH_WARNINGS):
        repair_rec = RepairRecommendation(action=RepairAction.ACCEPT)

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return ValidationResult(
        schema_version="1.0",
        valid=is_valid,
        status=final_status,
        overall_score=overall_score,
        dimension_scores={k: round(v, 2) for k, v in dimension_scores.items()},
        dimension_statuses=dimension_statuses,
        violations=violations,
        warnings=warnings,
        evidence={
            "total_violations": len(violations),
            "critical_count": len(critical_errors),
            "error_count": len(errors),
            "warning_count": len(warning_viols),
            "execution_duration_ms": duration_ms
        },
        section_results=[{"id": s.id, "title": s.title, "type": s.section_type} for s in document.sections],
        source_grounding_results=grounding_details,
        plan_compliance_results=plan_details,
        factual_results=factual_details,
        curriculum_results=curr_details,
        pedagogical_results=ped_details,
        hallucination_results=hallucination_details,
        repair_recommendation=repair_rec,
        validator_metadata={
            "validator_version": "1.0.0",
            "plan_schema_version": plan.schema_version,
            "document_id": document.id,
            "execution_duration_ms": duration_ms,
            "llm_judge_enabled": enable_llm
        }
    )
