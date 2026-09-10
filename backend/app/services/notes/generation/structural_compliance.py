"""
TeachGenie Notes Generation Engine — Structural Compliance Validator
=====================================================================
Validates and enforces structural fidelity of the generated NotesDocument
against the deterministic NotesGenerationPlan produced in Step 2.
Ensures zero crashes for downstream renderers by self-healing missing components.
"""
import logging
from typing import List, Dict, Any, Optional
from app.services.notes.schemas import NotesDocument, NoteSection, VisualSpec, CalloutItem
from app.services.notes.context.schemas import CanonicalNotesContext
from app.services.notes.decision.schemas import NotesGenerationPlan

logger = logging.getLogger("teachgenie.notes.generation.compliance")


class StructuralComplianceValidator:
    """Enforces structural conformance between NotesDocument and NotesGenerationPlan."""

    @classmethod
    def validate_and_repair(
        cls,
        doc: NotesDocument,
        plan: NotesGenerationPlan,
        ctx: CanonicalNotesContext
    ) -> List[str]:
        """
        Validates structural compliance and repairs any structural gaps in-place.
        Returns a list of warning strings recorded.
        """
        warnings: List[str] = list(doc.generation_warnings or [])

        # ── 1. Section Blueprint Validation ──
        existing_section_types = {s.section_type for s in doc.sections}
        for sec_plan in plan.section_plan:
            if sec_plan.type not in existing_section_types:
                warning_msg = f"Missing required section type: '{sec_plan.type}'"
                warnings.append(warning_msg)
                logger.warning(warning_msg)

                # In-place repair: Create compliant stub
                stub = cls._create_section_stub(sec_plan, ctx)
                doc.sections.append(stub)
                existing_section_types.add(sec_plan.type)

        # ── 2. Practice Contract Validation ──
        expected_practice_count = plan.practice_plan.count if plan.practice_plan.required else 0
        actual_practice_count = len(doc.practice)

        if actual_practice_count < expected_practice_count:
            warning_msg = (
                f"Practice count shortfall: expected {expected_practice_count}, got {actual_practice_count}"
            )
            warnings.append(warning_msg)
            logger.warning(warning_msg)

            # Repair practice count shortfall
            types = plan.practice_plan.types or ["recall", "application"]
            diff = plan.practice_plan.difficulty
            for idx in range(actual_practice_count, expected_practice_count):
                q_type = types[idx % len(types)]
                doc.practice.append({
                    "question": f"Self-assessment question on {ctx.topic} ({q_type}): Explain the foundational principles.",
                    "question_type": q_type,
                    "difficulty": diff,
                    "answer": f"Foundational review of {ctx.topic} aligned with {ctx.class_level} curriculum standards.",
                    "explanation": f"Addresses curriculum expectations for {ctx.topic}.",
                    "target_concept": ctx.topic
                })

        # ── 3. Visual Blueprint Validation ──
        if plan.visual_plan.required:
            has_visuals = bool(doc.visuals) or any(s.visual_spec is not None for s in doc.sections)
            if not has_visuals:
                warning_msg = f"Visual specification missing for required visual type: '{plan.visual_plan.type}'"
                warnings.append(warning_msg)
                logger.warning(warning_msg)

                v_type = plan.visual_plan.type if plan.visual_plan.type != "optional" else "flowchart"
                focus = plan.visual_plan.focus or ctx.topic
                spec = VisualSpec(
                    type=v_type,
                    title=f"{focus} — {v_type.replace('_', ' ').title()}",
                    nodes=[
                        {"id": "node_1", "label": focus},
                        {"id": "node_2", "label": "Key Concept A"},
                        {"id": "node_3", "label": "Key Concept B"}
                    ],
                    edges=[
                        {"from": "node_1", "to": "node_2", "label": "defines"},
                        {"from": "node_1", "to": "node_3", "label": "applies to"}
                    ],
                    mermaid_code=f"graph TD\n  A[{focus}] --> B[Key Concept A]\n  A --> C[Key Concept B]"
                )
                doc.visuals.append(spec)

                # Attach to the first relevant section
                for sec in doc.sections:
                    if sec.section_type in ("overview", "core_concept", "flowchart", "mind_map"):
                        if not sec.visual_spec:
                            sec.visual_spec = spec
                            break

        # ── 4. Remediation Plan Validation ──
        if plan.remediation_plan.required and plan.remediation_plan.target_concepts:
            uncovered_targets = []
            for target in plan.remediation_plan.target_concepts:
                covered = False
                for sec in doc.sections:
                    if (sec.target_concept and target.lower() in sec.target_concept.lower()) or \
                       (target.lower() in sec.title.lower()) or \
                       (target.lower() in sec.content.lower()):
                        covered = True
                        break
                if not covered:
                    uncovered_targets.append(target)

            if uncovered_targets:
                warning_msg = f"Remediation targets not explicitly covered in generated notes: {uncovered_targets}"
                warnings.append(warning_msg)
                logger.warning(warning_msg)

                # Append remediation section targeting uncovered misconceptions
                for target in uncovered_targets:
                    remediation_sec = NoteSection(
                        section_type="common_misconceptions",
                        title=f"Clarification: Misconceptions in {target}",
                        content=(
                            f"A frequent misunderstanding in {target} involves conflating core principles. "
                            f"In standard curriculum frameworks, students must verify definitions and physical/logical conditions."
                        ),
                        target_concept=target,
                        common_mistakes=[f"Incorrectly assuming simplified rules apply universally to {target}."],
                        callouts=[
                            CalloutItem(
                                type="misconception",
                                title=f"Misconception Alert: {target}",
                                text=f"Ensure distinction between standard definitions and colloquial usage in {target}."
                            )
                        ]
                    )
                    doc.sections.append(remediation_sec)

        # ── 5. Revision Plan Validation ──
        if plan.revision_plan.required and not doc.revision_summary:
            warning_msg = "Revision summary missing for plan requiring revision."
            warnings.append(warning_msg)
            logger.warning(warning_msg)

            key_pts = []
            for s in doc.sections:
                key_pts.extend(s.key_points[:2])
            if not key_pts:
                key_pts = [f"Master core definition of {ctx.topic}.", "Review practice checkpoint solutions."]

            doc.revision_summary = {
                "key_points": key_pts[:5],
                "formulas": [],
                "common_mistakes": []
            }

        # Deduplicate warnings while preserving order
        unique_warnings = []
        for w in warnings:
            if w not in unique_warnings:
                unique_warnings.append(w)

        doc.generation_warnings = unique_warnings
        return unique_warnings

    @classmethod
    def _create_section_stub(cls, sec_plan: Any, ctx: CanonicalNotesContext) -> NoteSection:
        """Creates a compliant section stub when LLM output omits a required section."""
        sec_type = getattr(sec_plan, "type", "core_concept")
        target = getattr(sec_plan, "target", None) or ctx.topic
        title = sec_type.replace("_", " ").title()

        callouts: List[CalloutItem] = []
        if sec_type == "common_misconceptions":
            title = f"Common Misconceptions & Corrections: {target}"
            content = (
                f"Clarifying standard misconceptions regarding {target}. "
                f"Students frequently encounter conceptual pitfalls when applying definitions."
            )
            callouts.append(CalloutItem(
                type="misconception",
                title="Conceptual Clarification",
                text=f"Pay careful attention to the governing conditions of {target}."
            ))
        elif sec_type == "checkpoint_practice":
            title = f"Checkpoint Practice: {target}"
            content = f"Apply your understanding of {target} with targeted exercises."
        elif sec_type == "worked_example":
            title = f"Step-by-Step Worked Example: {target}"
            content = f"Guided breakdown of a canonical problem involving {target}."
        elif sec_type == "formula_box":
            title = f"Key Formulas & Definitions: {target}"
            content = f"Mathematical formulations and core dimensional units for {target}."
        else:
            content = (
                f"Essential curriculum notes on {target} aligned with {ctx.class_level} standards."
            )

        return NoteSection(
            section_type=sec_type,
            title=title,
            content=content,
            target_concept=target,
            callouts=callouts
        )
