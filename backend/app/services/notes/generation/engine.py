"""
TeachGenie Notes Generation Engine — Primary Engine
===================================================
Executes Step 3 of the Notes Intelligence Architecture.
Transforms CanonicalNotesContext and NotesGenerationPlan into a structured,
pedagogically compliant NotesDocument, defended against prompt injection,
and verified for structural conformance.

STRICT INVARIANTS:
1. NotesGenerationPlan is TRUSTED. Step 3 executes the plan; it never modifies it.
2. LLM output is UNTRUSTED. Retrieved/source material is UNTRUSTED DATA.
3. Bounded Structural Repair: Safe structural repairs are applied; generic fake filler stubs are forbidden.
4. Bounded Regeneration: Missing semantic content triggers at most ONE targeted repair turn.
5. Deterministic fallback is clearly distinguished (ai_generation=False) and never fabricates context.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Set

from app.services.ai.router import router as ai_router
from app.services.notes.schemas import (
    NotesDocument, NoteSection, VisualSpec, CalloutItem,
    NoteFormat, NoteDepth, NoteDifficulty
)
from app.services.notes.context.schemas import CanonicalNotesContext
from app.services.notes.decision.schemas import (
    NotesGenerationPlan, PurposePlan, TeachingStrategyPlan, VisualPlan,
    RemediationPlan, PracticePlan, RevisionPlan, SectionPlanItem
)
from .schemas import GroundedSources, GenerationMode, SemanticDeficit
from .prompt_builder import PromptBuilder
from .output_parser import OutputParser
from .structural_compliance import StructuralComplianceValidator

logger = logging.getLogger("teachgenie.notes.generation.engine")


def ensure_generation_plan(plan_or_decision: Any, ctx: CanonicalNotesContext) -> NotesGenerationPlan:
    """Ensures input is a canonical NotesGenerationPlan, converting legacy structures if needed."""
    if isinstance(plan_or_decision, NotesGenerationPlan):
        return plan_or_decision

    # If it's a legacy DecisionOutput or has decision attributes, map it faithfully
    if hasattr(plan_or_decision, "selected_formats") or hasattr(plan_or_decision, "required_sections"):
        req_secs = getattr(plan_or_decision, "required_sections", []) or [
            "overview", "core_concept", "common_misconceptions", "quick_summary", "checkpoint_practice"
        ]
        sec_items = [SectionPlanItem(type=s, required=True) for s in req_secs]
        formats = getattr(plan_or_decision, "selected_formats", [NoteFormat.LEARNING_NOTES])
        depth = getattr(plan_or_decision, "depth", NoteDepth.STANDARD)
        difficulty = getattr(plan_or_decision, "difficulty", NoteDifficulty.STANDARD)
        misc = (
            getattr(plan_or_decision, "misconceptions_to_target", []) or
            getattr(ctx, "expected_misconceptions", []) or
            getattr(ctx, "student_misconceptions", []) or []
        )
        has_flowchart = any(
            f in (NoteFormat.FLOWCHART, NoteFormat.VISUAL_NOTES, NoteFormat.MIND_MAP)
            for f in formats
        )

        return NotesGenerationPlan.create(
            purpose=PurposePlan(),
            formats=formats,
            difficulty=difficulty,
            depth=depth,
            teaching_strategy=TeachingStrategyPlan(
                tone_instructions=getattr(plan_or_decision, "tone_instructions", "")
            ),
            section_plan=sec_items,
            visual_plan=VisualPlan(required=has_flowchart, type="flowchart" if has_flowchart else "optional"),
            remediation_plan=RemediationPlan(
                required=bool(misc),
                target_concepts=misc,
                include_misconception_correction=bool(misc)
            ),
            practice_plan=PracticePlan(required=True, count=3, difficulty="basic"),
            revision_plan=RevisionPlan(required=NoteFormat.QUICK_REVISION in formats)
        )

    # If no decision provided, execute step 2 decision engine (Step 3 never makes decision)
    try:
        from app.services.notes.decision.engine import NotesDecisionEngine
        return NotesDecisionEngine.decide(ctx)
    except Exception as e:
        logger.warning(f"Could not derive plan via decision engine: {e}; creating baseline plan.")
        return NotesGenerationPlan.create(
            purpose=PurposePlan(),
            formats=[NoteFormat.LEARNING_NOTES],
            difficulty=NoteDifficulty.STANDARD,
            depth=NoteDepth.STANDARD,
            teaching_strategy=TeachingStrategyPlan(),
            section_plan=[
                SectionPlanItem(type="overview", required=True),
                SectionPlanItem(type="core_concept", required=True),
                SectionPlanItem(type="common_misconceptions", required=True),
                SectionPlanItem(type="quick_summary", required=True),
                SectionPlanItem(type="checkpoint_practice", required=True),
            ],
            visual_plan=VisualPlan(required=False),
            remediation_plan=RemediationPlan(required=False),
            practice_plan=PracticePlan(required=True, count=3, difficulty="basic"),
            revision_plan=RevisionPlan(required=False),
        )


def _build_deterministic_fallback(
    ctx: CanonicalNotesContext,
    plan: NotesGenerationPlan,
    sources: Optional[GroundedSources] = None
) -> NotesDocument:
    """
    Constructs a complete, deterministic, plan-compliant NotesDocument when LLM generation fails.
    Strictly follows NotesGenerationPlan. Does NOT fabricate unknown student or curriculum attributes.
    """
    doc_id = f"note_{uuid.uuid4().hex[:12]}"
    curriculum_val = None
    if getattr(ctx, "resolved_context", None) and ctx.resolved_context.curriculum:
        curriculum_val = ctx.resolved_context.curriculum
    elif getattr(ctx, "curriculum", None):
        if hasattr(ctx.curriculum, "board") and ctx.curriculum.board:
            curriculum_val = ctx.curriculum.board
        elif isinstance(ctx.curriculum, str):
            curriculum_val = ctx.curriculum
    curriculum_str = str(curriculum_val).strip() if curriculum_val and str(curriculum_val).strip().lower() not in ("unknown", "none") else "unknown"

    class_val = None
    if getattr(ctx, "resolved_context", None) and ctx.resolved_context.class_level:
        class_val = ctx.resolved_context.class_level
    elif getattr(ctx, "class_level", None):
        class_val = ctx.class_level
    class_str = str(class_val).strip() if class_val and str(class_val).strip().lower() not in ("unknown", "none") else "unknown"

    title = f"{ctx.topic} — {class_str} Study Notes"
    learning_objectives = list(ctx.learning_objectives) if ctx.learning_objectives else [
        f"Understand the fundamental definition and scope of {ctx.topic}.",
        f"Apply core rules and problem-solving mechanisms of {ctx.topic}.",
        f"Recognize and avoid standard misconceptions regarding {ctx.topic}."
    ]

    sections: List[NoteSection] = []
    visuals: List[VisualSpec] = []

    # Visual spec if required (meaningful nodes & edges)
    visual_spec: Optional[VisualSpec] = None
    if plan.visual_plan.required:
        v_type = plan.visual_plan.type if plan.visual_plan.type != "optional" else "flowchart"
        focus = plan.visual_plan.focus or ctx.topic
        visual_spec = VisualSpec(
            type=v_type,
            title=f"{focus} — {v_type.replace('_', ' ').title()}",
            nodes=[
                {"id": "node_1", "label": focus},
                {"id": "node_2", "label": "Foundational Principle"},
                {"id": "node_3", "label": "Key Application"}
            ],
            edges=[
                {"from": "node_1", "to": "node_2", "label": "establishes"},
                {"from": "node_2", "to": "node_3", "label": "governs"}
            ],
            mermaid_code=f"graph TD\n  A[{focus}] --> B[Foundational Principle]\n  B --> C[Key Application]"
        )
        visuals.append(visual_spec)

    target_misconceptions = (
        plan.remediation_plan.target_concepts or
        getattr(ctx, "expected_misconceptions", []) or
        getattr(ctx, "student_misconceptions", []) or []
    )

    # Build sections strictly following section_plan blueprint
    for idx, sec_item in enumerate(plan.section_plan):
        sec_type = sec_item.type
        target = sec_item.target or ctx.topic
        sec_id = f"sec_{idx+1}_{uuid.uuid4().hex[:6]}"

        if sec_type == "overview":
            sec = NoteSection(
                id=sec_id,
                section_type=sec_type,
                title=f"Overview of {target}",
                content=(
                    f"Master study notes for **{target}**, tailored for **{class_str}** "
                    f"under the **{curriculum_str}** framework. Provides fundamental conceptual "
                    f"grounding required for {ctx.subject}."
                ),
                target_concept=target,
                key_points=[
                    f"Foundational definition and context of {target}.",
                    "Connection to broader principles and applications.",
                    "Key examination and conceptual expectations."
                ],
                callouts=[
                    CalloutItem(type="tip", title="Curriculum Focus", text=f"Focus on standard textbook definitions for {target}.")
                ]
            )
        elif sec_type == "core_concept":
            sec = NoteSection(
                id=sec_id,
                section_type=sec_type,
                title=f"Core Mechanisms & Key Principles: {target}",
                content=(
                    f"The operational principles governing **{target}**:\n\n"
                    "1. **Governing Laws**: Identify initial assumptions and boundary conditions.\n"
                    "2. **Operational Framework**: Track inputs, transformations, and final states.\n"
                    "3. **Verification**: Cross-check units, dimensions, and logical consistency."
                ),
                target_concept=target,
                key_points=[
                    f"State complete definitions of {target} using standard terminology.",
                    "Ensure step-by-step reasoning during proofs or derivations."
                ],
                examples=[
                    f"Standard worked example demonstrating {target}."
                ],
                visual_spec=visual_spec if visual_spec else None
            )
        elif sec_type == "common_misconceptions":
            misc_callouts: List[CalloutItem] = [
                CalloutItem(
                    type="misconception",
                    title="Common Misconception",
                    text=f"Students often mistakenly believe that '{m}'. In standard scientific/mathematical principles, this is incorrect."
                )
                for m in (target_misconceptions or ["assuming simplified rules apply universally"])
            ]
            sec = NoteSection(
                id=sec_id,
                section_type=sec_type,
                title=f"Common Misconceptions & Corrections: {target}",
                content=(
                    f"Mastering **{target}** requires actively debunking common pitfalls:\n\n"
                    "* Conflating everyday definitions with scientific/mathematical terminology.\n"
                    "* Over-generalizing formulas without verifying their range of validity."
                ),
                target_concept=target,
                common_mistakes=[
                    f"Treating '{m}' as a universally valid assumption."
                    for m in (target_misconceptions or ["standard textbook simplification"])
                ],
                callouts=misc_callouts
            )
        elif sec_type == "worked_example":
            sec = NoteSection(
                id=sec_id,
                section_type=sec_type,
                title=f"Step-by-Step Worked Example: {target}",
                content=(
                    f"**Problem**: Apply the principles of {target} to determine the system response.\n\n"
                    "**Step 1: Identify Given Quantities**\nExtract all provided parameters and verify SI units.\n\n"
                    "**Step 2: Select Governing Relationship**\nApply the standard formulation appropriate for conditions.\n\n"
                    "**Step 3: Calculate and State Units**\nSubstitute values and clearly box the final result with units."
                ),
                target_concept=target,
                examples=[f"Canonical solved problem for {target}."]
            )
        elif sec_type == "formula_box":
            sec = NoteSection(
                id=sec_id,
                section_type=sec_type,
                title=f"Key Formulas & Definitions: {target}",
                content=f"Summary of mathematical formulations and unit relationships for {target}.",
                target_concept=target,
                formulas=[f"Standard formula definition for {target}"]
            )
        elif sec_type == "quick_summary":
            sec = NoteSection(
                id=sec_id,
                section_type=sec_type,
                title=f"Quick Revision Summary: {target}",
                content=f"Essential high-yield takeaways for rapid exam review on **{target}**.",
                target_concept=target,
                key_points=[
                    f"Master the core mechanism of {target}.",
                    "Review conditions of applicability before calculations.",
                    "Pay special attention to standard misconception traps."
                ]
            )
        elif sec_type == "checkpoint_practice":
            sec = NoteSection(
                id=sec_id,
                section_type=sec_type,
                title=f"Checkpoint Practice: {target}",
                content=(
                    f"Self-assessment checkpoints for **{target}**:\n\n"
                    f"1. Explain the governing principle of {target} in your own words.\n"
                    f"2. How does changing boundary conditions impact the outcome?"
                ),
                target_concept=target
            )
        else:
            sec = NoteSection(
                id=sec_id,
                section_type=sec_type,
                title=sec_type.replace("_", " ").title(),
                content=f"Comprehensive curricular review covering {target} for {class_str}.",
                target_concept=target
            )
        sections.append(sec)

    # Ensure misconception coverage if targeted in plan but not present in section types
    existing_types = {s.section_type for s in sections}
    if target_misconceptions and "common_misconceptions" not in existing_types:
        misc_callouts = [
            CalloutItem(
                type="misconception",
                title="Common Misconception",
                text=f"Students often mistakenly believe that '{m}'. Note that this is incorrect."
            )
            for m in target_misconceptions
        ]
        sections.append(NoteSection(
            id=f"sec_misc_{uuid.uuid4().hex[:6]}",
            section_type="common_misconceptions",
            title="Common Misconceptions & Corrections",
            content=f"Targeted clarification on frequent student misconceptions regarding {ctx.topic}.",
            target_concept=ctx.topic,
            common_mistakes=[f"Incorrect assumption: {m}" for m in target_misconceptions],
            callouts=misc_callouts
        ))

    # Build practice items (preserving plan difficulty and count)
    practice_items: List[Dict[str, Any]] = []
    p_count = plan.practice_plan.count if plan.practice_plan.required else 3
    p_diff = plan.practice_plan.difficulty
    p_types = plan.practice_plan.types or ["recall", "application"]

    for i in range(p_count):
        q_type = p_types[i % len(p_types)]
        if p_diff == "advanced":
            q_text = f"Advanced problem {i+1} ({q_type}): Analyze and evaluate boundary conditions in {ctx.topic}."
            ans_text = f"Rigorous multi-step derivation and boundary analysis for {ctx.topic}."
        elif p_diff == "foundational":
            q_text = f"Foundational review {i+1} ({q_type}): Identify the core rule of {ctx.topic}."
            ans_text = f"Direct definition and fundamental application of {ctx.topic}."
        else:
            q_text = f"Standard question {i+1} ({q_type}): State and apply the principles of {ctx.topic}."
            ans_text = f"Standard curriculum solution for {ctx.topic}."

        practice_items.append({
            "question": q_text,
            "question_type": q_type,
            "difficulty": p_diff,
            "answer": ans_text,
            "explanation": f"Addresses {p_diff} curriculum expectations for {ctx.topic}.",
            "target_concept": ctx.topic
        })

    # Revision summary
    revision_summary = None
    if plan.revision_plan.required:
        revision_summary = {
            "key_points": [
                f"Core definition and operational conditions of {ctx.topic}.",
                f"Step-by-step problem-solving technique for {ctx.topic}."
            ],
            "formulas": [],
            "common_mistakes": [f"Confusing definitions in {ctx.topic} with informal usage."]
        }

    # Citations
    citations = []
    if sources and sources.items:
        citations = [
            {"source_id": s.source_id, "badge": s.badge or "Source", "title": s.title}
            for s in sources.items
        ]
    elif ctx.source_evidence:
        citations = list(ctx.source_evidence)

    doc = NotesDocument(
        schema_version="1.0",
        id=doc_id,
        document_id=doc_id,
        title=title,
        subject=ctx.subject,
        class_level=class_str,
        topic=ctx.topic,
        curriculum=curriculum_str,
        language=ctx.language,
        mode=ctx.mode,
        learning_objectives=learning_objectives,
        selected_formats=plan.formats,
        depth=plan.depth,
        difficulty=plan.difficulty,
        sections=sections,
        visuals=visuals,
        practice=practice_items,
        revision_summary=revision_summary,
        source_citations=citations,
        lineage=ctx.lineage_ids,
        generation_mode=GenerationMode.DETERMINISTIC_FALLBACK.value,
        structural_repairs=[],
        generation_metadata={
            "model": "deterministic_fallback",
            "schema_version": "1.0",
            "plan_schema_version": plan.schema_version,
            "purpose": plan.purpose.primary,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "decision_confidence": plan.decision_confidence,
            "ai_generation": False,
            "generation_mode": GenerationMode.DETERMINISTIC_FALLBACK.value,
            "structural_repairs": [],
            "generation_warnings": ["Generated using deterministic plan-driven fallback."]
        },
        generation_warnings=["Generated using deterministic plan-driven fallback."]
    )
    return doc


def _merge_repair_output(
    doc: NotesDocument,
    repair_data: Dict[str, Any],
    plan: NotesGenerationPlan,
    ctx: CanonicalNotesContext
) -> None:
    """Merges targeted repair output into the document while preserving existing valid sections."""
    if not isinstance(repair_data, dict):
        return

    existing_types = {s.section_type for s in doc.sections}

    # Merge newly generated sections
    repair_sections = repair_data.get("sections")
    if isinstance(repair_sections, list):
        for s_dict in repair_sections:
            if not isinstance(s_dict, dict):
                continue
            sec_type = str(s_dict.get("section_type", "")).strip()
            if not sec_type:
                continue

            # Only add if it repairs a missing section
            if sec_type not in existing_types:
                callouts_list = []
                for c in s_dict.get("callouts", []):
                    if isinstance(c, dict):
                        callouts_list.append(CalloutItem(
                            type=str(c.get("type", "tip")),
                            title=str(c.get("title", "Note")),
                            text=str(c.get("text", ""))
                        ))

                new_sec = NoteSection(
                    id=s_dict.get("id") or f"sec_{len(doc.sections)+1}_{doc.id}",
                    section_type=sec_type,
                    title=str(s_dict.get("title") or sec_type.replace("_", " ").title()),
                    content=str(s_dict.get("content") or "").strip(),
                    target_concept=s_dict.get("target_concept") or ctx.topic,
                    key_points=s_dict.get("key_points") or [],
                    examples=s_dict.get("examples") or [],
                    formulas=s_dict.get("formulas") or [],
                    common_mistakes=s_dict.get("common_mistakes") or [],
                    callouts=callouts_list
                )
                doc.sections.append(new_sec)
                existing_types.add(sec_type)

    # Merge practice items if shortfall exists
    repair_practice = repair_data.get("practice")
    expected_practice = plan.practice_plan.count if plan.practice_plan.required else 0
    if isinstance(repair_practice, list) and len(doc.practice) < expected_practice:
        for p in repair_practice:
            if len(doc.practice) >= expected_practice:
                break
            if isinstance(p, dict) and p.get("question"):
                doc.practice.append({
                    "question": str(p.get("question", "")).strip(),
                    "question_type": str(p.get("question_type", "recall")).strip(),
                    "difficulty": plan.practice_plan.difficulty,
                    "answer": str(p.get("answer", "")).strip(),
                    "explanation": str(p.get("explanation", "")).strip(),
                    "target_concept": str(p.get("target_concept") or ctx.topic).strip()
                })

    # Merge visual spec if missing
    repair_visual = repair_data.get("visual_spec")
    if isinstance(repair_visual, dict) and repair_visual.get("nodes") and not doc.visuals:
        v_obj = VisualSpec(
            type=str(repair_visual.get("type", plan.visual_plan.type or "flowchart")),
            title=str(repair_visual.get("title") or ctx.topic),
            nodes=repair_visual.get("nodes", []),
            edges=repair_visual.get("edges", []),
            mermaid_code=repair_visual.get("mermaid_code")
        )
        doc.visuals.append(v_obj)
        for s in doc.sections:
            if s.section_type in ("core_concept", "overview", "flowchart", "mind_map"):
                if not s.visual_spec:
                    s.visual_spec = v_obj
                    break


async def generate_notes(
    context: CanonicalNotesContext,
    plan: Any,
    sources: Optional[GroundedSources] = None
) -> NotesDocument:
    """
    Main Entrypoint for Step 3 Generation Engine.
    Executes pedagogical plan into a structured NotesDocument with bounded repair.
    """
    # 1. Ensure canonical plan
    resolved_plan: NotesGenerationPlan = ensure_generation_plan(plan, context)

    # 2. Standardize grounded sources if not supplied
    if sources is None:
        sources = GroundedSources.from_context(context)

    # 3. Build prompts with prompt-injection defense
    system_prompt = PromptBuilder.build_system_prompt(context, resolved_plan)
    user_prompt = PromptBuilder.build_user_prompt(context, resolved_plan, sources)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # 4. Invoke ModelRouter JSON generation
    try:
        raw_output = await ai_router.generate_json(
            task="content_generation",
            messages=messages,
            temperature=0.2,
            max_tokens=4096,
            timeout=55.0
        )

        doc = OutputParser.parse_response(
            raw_output=raw_output,
            ctx=context,
            plan=resolved_plan,
            sources=sources,
            model_name="ai_router.content_generation"
        )
    except Exception as e:
        logger.warning(f"AI Router generation failed: {e}; invoking deterministic fallback.")
        return _build_deterministic_fallback(context, resolved_plan, sources)

    # 5. Apply safe structural repairs
    StructuralComplianceValidator.apply_safe_structural_repairs(doc, resolved_plan, context)

    # 6. Audit semantic deficits
    deficit = StructuralComplianceValidator.audit_deficits(doc, resolved_plan, context)

    # 7. Bounded Regeneration Turn (MAX 1 ATTEMPT)
    if deficit.has_deficits:
        logger.info(f"Semantic deficits detected: {deficit}. Attempting ONE bounded repair turn...")
        repair_prompt = PromptBuilder.build_repair_prompt(context, resolved_plan, deficit, doc)
        repair_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": repair_prompt}
        ]

        try:
            repair_raw = await ai_router.generate_json(
                task="repair",
                messages=repair_messages,
                temperature=0.2,
                max_tokens=2048,
                timeout=40.0
            )
            # Merge repaired components into doc
            _merge_repair_output(doc, repair_raw, resolved_plan, context)

            # Re-apply safe structural repairs and re-audit
            StructuralComplianceValidator.apply_safe_structural_repairs(doc, resolved_plan, context)
            deficit = StructuralComplianceValidator.audit_deficits(doc, resolved_plan, context)
            if not deficit.has_deficits:
                doc.structural_repairs.append("semantic_deficits_repaired")
        except Exception as e:
            logger.warning(f"Bounded repair attempt failed: {e}")

    # 8. Final Status Assignment
    StructuralComplianceValidator.validate_and_repair(doc, resolved_plan, context)
    return doc
