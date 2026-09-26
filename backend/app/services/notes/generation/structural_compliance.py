"""
LearnByGenie Notes Generation Engine — Structural Compliance Validator
=====================================================================
Validates and enforces structural fidelity of the generated NotesDocument
against the deterministic NotesGenerationPlan produced in Step 2.
Implements BOUNDED STRUCTURAL REPAIR: safe structural fixes are allowed;
unsafe semantic fabrication (fake filler stubs) is strictly forbidden.
"""
import logging
from typing import List, Dict, Any, Optional, Set
from app.services.notes.schemas import NotesDocument, NoteSection, VisualSpec, CalloutItem
from app.services.notes.context.schemas import CanonicalNotesContext
from app.services.notes.decision.schemas import NotesGenerationPlan
from .schemas import SemanticDeficit, GenerationMode

logger = logging.getLogger("learnbygenie.notes.generation.compliance")


class StructuralComplianceValidator:
    """Enforces structural conformance and identifies semantic deficits without inventing filler."""

    @classmethod
    def audit_deficits(
        cls,
        doc: NotesDocument,
        plan: NotesGenerationPlan,
        ctx: CanonicalNotesContext
    ) -> SemanticDeficit:
        """
        Audits the document against the plan to identify missing semantic requirements.
        Returns a SemanticDeficit object indicating which components need bounded regeneration.
        """
        existing_types = {s.section_type for s in doc.sections}

        # 1. Check required sections
        missing_sections = [
            sec_plan.type for sec_plan in plan.section_plan
            if sec_plan.required and sec_plan.type not in existing_types
        ]

        # 2. Check practice shortfall
        expected_practice = plan.practice_plan.count if plan.practice_plan.required else 0
        actual_practice = len(doc.practice)
        practice_shortfall = max(0, expected_practice - actual_practice)

        # 3. Check visual requirement
        missing_visual = False
        if plan.visual_plan.required:
            has_visuals = bool(doc.visuals) or any(
                s.visual_spec is not None and bool(s.visual_spec.nodes)
                for s in doc.sections
            )
            if not has_visuals:
                missing_visual = True

        # 4. Check remediation targeting
        unaddressed_misconceptions: List[str] = []
        if plan.remediation_plan.required and plan.remediation_plan.target_concepts:
            for target in plan.remediation_plan.target_concepts:
                target_lower = target.lower()
                covered = False
                for sec in doc.sections:
                    if (sec.target_concept and target_lower in sec.target_concept.lower()) or \
                       (target_lower in sec.title.lower()) or \
                       (target_lower in sec.content.lower()) or \
                       any(target_lower in c.text.lower() for c in sec.callouts):
                        covered = True
                        break
                if not covered:
                    unaddressed_misconceptions.append(target)

        return SemanticDeficit(
            missing_sections=missing_sections,
            practice_shortfall=practice_shortfall,
            missing_visual=missing_visual,
            unaddressed_misconceptions=unaddressed_misconceptions
        )

    @classmethod
    def apply_safe_structural_repairs(
        cls,
        doc: NotesDocument,
        plan: NotesGenerationPlan,
        ctx: CanonicalNotesContext
    ) -> List[str]:
        """
        Applies only SAFE structural repairs:
        - Reorders sections to match plan blueprint sequence.
        - Truncates excess practice questions to exact plan count.
        - Normalizes list fields and section IDs.
        - Identifies and warns about unexpected section types.
        Every repair performed is recorded in doc.structural_repairs.
        """
        repairs: List[str] = list(doc.structural_repairs or [])
        warnings: List[str] = list(doc.generation_warnings or [])

        # ── 1. Section Reordering to Match Plan Blueprint ──
        plan_order = [s.type for s in plan.section_plan]
        order_map = {stype: idx for idx, stype in enumerate(plan_order)}

        current_types = [s.section_type for s in doc.sections]
        expected_subset_types = [t for t in plan_order if t in current_types]

        # Check if reordering is needed
        current_subset_types = [t for t in current_types if t in order_map]
        if current_subset_types != expected_subset_types:
            # Sort sections by plan blueprint order, keeping unexpected sections at the end
            doc.sections.sort(key=lambda s: order_map.get(s.section_type, 999))
            repairs.append("section_order_normalized")
            logger.info("Normalized section order to match plan blueprint.")

        # ── 2. Truncate Excess Practice Questions ──
        expected_count = plan.practice_plan.count if plan.practice_plan.required else 0
        if len(doc.practice) > expected_count and expected_count > 0:
            doc.practice = doc.practice[:expected_count]
            repairs.append("practice_items_truncated")
            logger.info(f"Truncated practice items to plan count: {expected_count}.")

        # ── 3. Normalize List Fields & Deterministic IDs ──
        for idx, sec in enumerate(doc.sections):
            if not sec.id:
                sec.id = f"sec_{idx+1}_{doc.id}"
                repairs.append("section_id_normalized")
            if sec.key_points is None:
                sec.key_points = []
            if sec.examples is None:
                sec.examples = []
            if sec.formulas is None:
                sec.formulas = []
            if sec.common_mistakes is None:
                sec.common_mistakes = []
            if sec.callouts is None:
                sec.callouts = []

        # ── 4. Unexpected Sections Audit ──
        allowed_types: Set[str] = set(plan_order)
        for s in doc.sections:
            if s.section_type not in allowed_types:
                warning_msg = f"Unexpected section type: '{s.section_type}'"
                if warning_msg not in warnings:
                    warnings.append(warning_msg)

        # Update document state
        unique_repairs = []
        for r in repairs:
            if r not in unique_repairs:
                unique_repairs.append(r)

        doc.structural_repairs = unique_repairs
        doc.generation_metadata["structural_repairs"] = unique_repairs
        doc.generation_warnings = warnings
        return unique_repairs

    @classmethod
    def validate_and_repair(
        cls,
        doc: NotesDocument,
        plan: NotesGenerationPlan,
        ctx: CanonicalNotesContext
    ) -> List[str]:
        """
        Entrypoint for structural compliance.
        Applies safe structural repairs, audits semantic deficits, and updates status.
        Does NOT silently synthesize fake generic prose stubs.
        """
        # 1. Apply safe structural repairs
        cls.apply_safe_structural_repairs(doc, plan, ctx)

        # 2. Audit remaining semantic deficits
        deficit = cls.audit_deficits(doc, plan, ctx)

        # 3. If deficits exist, record explicit warnings and flag as incomplete
        warnings = list(doc.generation_warnings or [])
        if deficit.missing_sections:
            for s in deficit.missing_sections:
                warnings.append(f"Missing required section type: '{s}'")
        if deficit.practice_shortfall > 0:
            expected = plan.practice_plan.count
            actual = len(doc.practice)
            warnings.append(f"Practice count shortfall: expected {expected}, got {actual}")
        if deficit.missing_visual:
            warnings.append(f"Visual specification missing for required visual type: '{plan.visual_plan.type}'")
        if deficit.unaddressed_misconceptions:
            warnings.append(f"Remediation targets not explicitly covered: {deficit.unaddressed_misconceptions}")

        # Deduplicate warnings
        unique_warnings = []
        for w in warnings:
            if w not in unique_warnings:
                unique_warnings.append(w)

        doc.generation_warnings = unique_warnings
        doc.generation_metadata["generation_warnings"] = unique_warnings

        if deficit.has_deficits:
            # Mark generation incomplete if mandatory semantic content is missing
            doc.generation_mode = GenerationMode.GENERATION_INCOMPLETE.value
            doc.generation_metadata["generation_mode"] = GenerationMode.GENERATION_INCOMPLETE.value
        elif doc.structural_repairs:
            doc.generation_mode = GenerationMode.AI_GENERATED_REPAIRED.value
            doc.generation_metadata["generation_mode"] = GenerationMode.AI_GENERATED_REPAIRED.value
        else:
            doc.generation_mode = GenerationMode.AI_GENERATED.value
            doc.generation_metadata["generation_mode"] = GenerationMode.AI_GENERATED.value

        return unique_warnings
