"""
Bounded Validation-Repair Orchestrator (Step 4)
==============================================
Coordinates a single bounded repair cycle when ValidationResult indicates
fixable defects (ValidationStatus.REPAIRABLE).
Strict Invariants:
1. Global Repair Budget: Maximum ONE repair attempt. Never creates an infinite retry loop.
2. Tracks repair metadata: repair_budget, repair_attempts, repair_source, repaired_sections.
3. Repaired document MUST be re-validated through the complete quality gate.
4. If re-validation still fails, the document is rejected or marked invalid.
"""
import logging
import copy
from typing import Optional, Tuple, List

from ..schemas import NotesDocument
from ..context.schemas import CanonicalNotesContext
from ..decision.schemas import NotesGenerationPlan
from ..generation.schemas import GroundedSources, GenerationMode
from ..generation.engine import _merge_repair_output
from ..generation.prompt_builder import PromptBuilder
from .schemas import (
    ValidationResult, ValidationStatus, RepairAction, RepairMetadata
)
from .engine import validate_notes
from app.services.ai.router import router as ai_router

logger = logging.getLogger("teachgenie.notes.validation.orchestrator")


async def validate_and_repair_notes(
    context: CanonicalNotesContext,
    plan: NotesGenerationPlan,
    document: NotesDocument,
    sources: Optional[GroundedSources] = None,
    enable_llm: bool = True,
    auto_repair: bool = True,
    repair_budget: int = 1,
    existing_repair_attempts: int = 0
) -> Tuple[NotesDocument, ValidationResult]:
    """
    Executes validation, and if repairable defects are detected and budget permits,
    orchestrates at most ONE bounded targeted repair cycle before final re-validation.
    """
    # Non-mutation guarantee on input document: work on a fresh copy if repairing
    doc_working = copy.deepcopy(document)
    repair_attempts = existing_repair_attempts
    repaired_sections: List[str] = []

    # 1. Initial Validation
    initial_result = await validate_notes(
        context=context,
        plan=plan,
        document=doc_working,
        sources=sources,
        enable_llm=enable_llm
    )
    initial_result.repair_metadata = RepairMetadata(
        repair_budget=repair_budget,
        repair_attempts=repair_attempts,
        repair_source="validation",
        repaired_sections=repaired_sections
    )

    # If valid, or if repair is disabled/not recommended, return immediately
    if initial_result.valid or not auto_repair:
        return doc_working, initial_result

    # If global repair budget is exhausted, do NOT attempt repair (Spec 3 & 5)
    if repair_attempts >= repair_budget:
        logger.warning(f"Global repair budget exhausted ({repair_attempts}/{repair_budget}). No further repair permitted.")
        return doc_working, initial_result

    if initial_result.status != ValidationStatus.REPAIRABLE or not initial_result.repair_recommendation:
        logger.info(f"Validation finished with status '{initial_result.status.value}'. No repair attempted.")
        return doc_working, initial_result

    # ── 2. Bounded Single Repair Attempt ──
    rec = initial_result.repair_recommendation
    if rec.action != RepairAction.REPAIR or not rec.targets:
        return doc_working, initial_result

    logger.info(f"Document is repairable ({len(initial_result.violations)} violations). Attempting bounded repair cycle (budget: {repair_attempts+1}/{repair_budget})...")
    repair_attempts += 1
    repaired_sections = [t.section_id or t.violation_code for t in rec.targets]

    # Build targeted repair prompt
    missing_items = [t.reason for t in rec.targets]
    repair_prompt = (
        f"You are repairing an educational study notes document for '{context.topic}'.\n"
        f"The following validation defects were detected and must be corrected:\n"
        + "\n".join([f"- {item}" for item in missing_items]) +
        f"\n\nProvide ONLY the corrected sections or practice questions as JSON matching the standard schema."
    )

    try:
        repair_raw = await ai_router.generate_json(
            system_instruction="You are TeachGenie's targeted notes repair assistant. Return corrected components only in valid JSON.",
            prompt=repair_prompt,
            model_name="gemini-2.5-flash",
            temperature=0.2
        )
        if isinstance(repair_raw, dict):
            _merge_repair_output(doc_working, repair_raw, plan, context)
            doc_working.generation_mode = GenerationMode.AI_GENERATED_REPAIRED.value
            doc_working.structural_repairs.append("validated_repair_applied")
    except Exception as e:
        logger.warning(f"Targeted repair generation failed: {e}", exc_info=True)

    # ── 3. Re-Validation (Never Assume Repair Succeeded) ──
    final_result = await validate_notes(
        context=context,
        plan=plan,
        document=doc_working,
        sources=sources,
        enable_llm=enable_llm
    )

    # Attach complete repair metadata
    final_result.repair_metadata = RepairMetadata(
        repair_budget=repair_budget,
        repair_attempts=repair_attempts,
        repair_source="validation",
        repaired_sections=repaired_sections
    )

    logger.info(f"Post-repair validation completed with status '{final_result.status.value}'.")
    return doc_working, final_result
