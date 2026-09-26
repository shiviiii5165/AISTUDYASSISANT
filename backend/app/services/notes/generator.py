"""
AI Notes Generation Engine — Primary Notes Generator
=====================================================
Orchestrates structured prompt construction, ModelRouter JSON generation,
response parsing, validation scoring, and bounded repair turns.
"""
import json
import logging
import uuid
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.services.ai.router import router as ai_router
from .schemas import (
    CanonicalNotesContext, DecisionOutput, NotesDocument,
    NoteSection, VisualSpec, CalloutItem, NoteFormat, NoteDepth, NoteDifficulty
)
from .validator import NotesValidator

logger = logging.getLogger("learnbygenie.notes.generator")


class NotesGenerator:
    """Generates structured, validated educational notes using ModelRouter and deterministic fallbacks."""

    @staticmethod
    async def generate(
        ctx: CanonicalNotesContext,
        decision: Any,
        sources: Optional[Any] = None
    ) -> NotesDocument:
        """
        Executes end-to-end notes generation using Step 3 Generation Engine:
        Prompt Construction -> ModelRouter -> Parsing -> Structural Compliance -> Quality Validation.
        """
        try:
            from app.services.notes.generation import generate_notes
            doc = await generate_notes(context=ctx, plan=decision, sources=sources)
            doc.quality = NotesValidator.evaluate(doc, ctx, decision)
            return doc
        except Exception as e:
            logger.error(f"Generation Engine execution failed: {e}; falling back to deterministic fallback.")
            return NotesGenerator._generate_deterministic_fallback(ctx, decision)

    @classmethod
    def generate_from_lesson_gap_context(
        cls,
        topic: str,
        weak_concepts: List[str],
        prerequisite_gaps: List[str],
        misconception_evidence: List[Dict[str, Any]]
    ) -> NotesDocument:
        """
        P3 Production Integration: Builds targeted remedial revision notes directly
        from weak concepts, diagnosed prerequisite gaps, and misconception evidence.
        """
        sections = []
        # Section 1: Prerequisite refresher
        sections.append(NoteSection(
            id="sec_prereq_gap",
            section_type="overview",
            title="Prerequisite Foundations Refresher",
            content="\n".join([f"Reinforcing foundation: {gap}. Essential before mastering {topic}." for gap in (prerequisite_gaps or ["Core prerequisites"])]),
            key_points=prerequisite_gaps or ["Core prerequisite foundation"]
        ))

        # Section 2: Targeted Misconception Clearance
        sections.append(NoteSection(
            id="sec_misc_clearance",
            section_type="common_misconceptions",
            title="Common Misconceptions & Counterexamples",
            content="\n".join([f"Misconception trap: {m.get('misconception', 'Common error')}. Correct insight: Grounded explanation." for m in (misconception_evidence or [{"misconception": "Concept inversion"}])]),
            key_points=[m.get("misconception", "Common error") for m in (misconception_evidence or [])]
        ))

        return NotesDocument(
            id=f"notes_remedial_{uuid.uuid4().hex[:8]}",
            title=f"Targeted Revision Notes: {topic}",
            topic=topic,
            sections=sections,
            metadata={"source": "vnext_adaptive_engine", "weak_concepts": weak_concepts}
        )

    @staticmethod
    def _build_generation_prompt(ctx: CanonicalNotesContext, decision: DecisionOutput) -> str:
        """Constructs a comprehensive, instructionally dense pedagogical prompt."""
        # Evidence grounding block
        evidence_text = ""
        if ctx.source_evidence:
            snippets = [f"- [{ev.get('badge', 'Source')}]: {ev.get('snippet', '')}" for ev in ctx.source_evidence[:4]]
            evidence_text = "\nVERIFIED SOURCE EVIDENCE (Ground claims strictly in this material):\n" + "\n".join(snippets)

        # Objectives & Lesson context block
        lesson_text = ""
        if ctx.learning_objectives:
            objs = "\n".join([f"- {o}" for o in ctx.learning_objectives])
            lesson_text += f"\nCANONICAL LEARNING OBJECTIVES:\n{objs}\n"
        if ctx.lesson_activities:
            acts = "\n".join([f"- {a}" for a in ctx.lesson_activities[:4]])
            lesson_text += f"\nTEACHING FLOW & ACTIVITIES:\n{acts}\n"
        if ctx.teacher_instructions:
            tacts = "\n".join([f"- {t}" for t in ctx.teacher_instructions[:3]])
            lesson_text += f"\nTEACHER'S INSTRUCTIONAL EMPHASIS:\n{tacts}\n"

        # Misconceptions & Weak Concepts block
        signals_text = ""
        if decision.misconceptions_to_target:
            misc = "\n".join([f"- {m}" for m in decision.misconceptions_to_target])
            signals_text += f"\nANTICIPATED STUDENT MISCONCEPTIONS (Must explicitly correct in callout or section):\n{misc}\n"
        if decision.weak_concepts_to_reinforce:
            weak = ", ".join(decision.weak_concepts_to_reinforce)
            signals_text += f"\nWEAK CONCEPTS REQUIRING EXTRA SCAFFOLDING & WORKED EXAMPLES:\n{weak}\n"

        formats_str = ", ".join([f.value for f in decision.selected_formats])
        required_secs_str = ", ".join(decision.required_sections)

        prompt = f"""
Generate comprehensive, student-friendly AI Study Notes for:

TOPIC: {ctx.topic}
SUBJECT: {ctx.subject}
TARGET LEVEL: {ctx.class_level} ({ctx.curriculum})
LANGUAGE: {ctx.language}
NOTE FORMATS: {formats_str}
TARGET DEPTH: {decision.depth.value.upper()} | DIFFICULTY: {decision.difficulty.value.upper()}

PEDAGOGICAL TONE INSTRUCTIONS:
{decision.tone_instructions}
{lesson_text}{signals_text}{evidence_text}

USER INSTRUCTIONS:
{ctx.explicit_user_instructions or 'Provide comprehensive coverage suitable for revision and mastery.'}

MANDATORY SECTIONS TO PRODUCE ({required_secs_str}):
1. "overview": Brief 2-3 sentence concept hook and intuition.
2. "core_concept": Clear, structured explanation with key points and definitions.
3. "worked_example": Real-world practical application or step-by-step solved problem.
4. "quick_summary": Bulleted high-yield takeaways.
5. "checkpoint_practice": 2 diagnostic practice questions with answers for self-assessment.
"""

        if "flowchart" in decision.required_sections or NoteFormat.FLOWCHART in decision.selected_formats:
            prompt += """
6. "flowchart": Include a visual_spec object with nodes and edges showing the sequential process.
"""
        if "comparison_table" in decision.required_sections or NoteFormat.COMPARISON_NOTES in decision.selected_formats:
            prompt += """
7. "comparison_table": Include a Markdown comparison table contrasting the key entities.
"""
        if "formula_box" in decision.required_sections or NoteFormat.FORMULA_SHEET in decision.selected_formats:
            prompt += """
8. "formula_box": List all crucial formulas, unit symbols, and conditions of applicability.
"""
        if "common_misconceptions" in decision.required_sections:
            prompt += """
9. "common_misconceptions": Highlight the exact misconceptions, why students get them wrong, and the correct rule.
"""

        prompt += """
OUTPUT JSON SCHEMA:
{
  "title": "Clear, student-friendly title",
  "sections": [
    {
      "section_type": "overview",
      "title": "Introduction & Big Picture",
      "content": "Markdown text...",
      "key_points": ["Point 1", "Point 2"],
      "examples": [],
      "formulas": [],
      "common_mistakes": [],
      "callouts": [
        {"type": "tip", "title": "Quick Insight", "text": "..."}
      ],
      "visual_spec": null
    },
    {
      "section_type": "core_concept",
      "title": "Core Mechanism & Rules",
      "content": "Detailed markdown explanation...",
      "key_points": ["Key definition", "Mechanism step"],
      "examples": ["Real-world analogy..."],
      "formulas": [],
      "common_mistakes": ["What students confuse..."],
      "callouts": [
        {"type": "warning", "title": "Common Misconception", "text": "Explain why the misconception is wrong..."}
      ],
      "visual_spec": {
        "type": "flowchart",
        "title": "Process Flow",
        "nodes": [
          {"id": "1", "label": "Step 1: Input", "description": "..."},
          {"id": "2", "label": "Step 2: Processing", "description": "..."}
        ],
        "edges": [
          {"from": "1", "to": "2", "label": "transitions to"}
        ],
        "mermaid_code": "graph TD\\n  A[Step 1] --> B[Step 2]"
      }
    }
  ]
}
Return ONLY valid JSON.
"""
        return prompt

    @staticmethod
    def _parse_llm_response(
        raw_json: Dict[str, Any],
        ctx: CanonicalNotesContext,
        decision: DecisionOutput
    ) -> NotesDocument:
        """Converts raw LLM dictionary output into a strict NotesDocument instance."""
        note_id = f"note_{uuid.uuid4().hex[:12]}"
        title = raw_json.get("title") or f"{ctx.topic} — {ctx.class_level} Study Notes"

        raw_sections = raw_json.get("sections") or []
        sections: List[NoteSection] = []

        for i, s_dict in enumerate(raw_sections):
            visual_data = s_dict.get("visual_spec")
            visual_obj = None
            if visual_data and isinstance(visual_data, dict):
                visual_obj = VisualSpec(
                    type=visual_data.get("type", "flowchart"),
                    title=visual_data.get("title", ""),
                    nodes=visual_data.get("nodes", []),
                    edges=visual_data.get("edges", []),
                    mermaid_code=visual_data.get("mermaid_code")
                )

            callouts_list = []
            for c in s_dict.get("callouts", []):
                if isinstance(c, dict):
                    callouts_list.append(CalloutItem(
                        type=c.get("type", "tip"),
                        title=c.get("title", "Note"),
                        text=c.get("text", "")
                    ))

            sec = NoteSection(
                id=f"sec_{i+1}_{uuid.uuid4().hex[:6]}",
                section_type=s_dict.get("section_type", "core_concept"),
                title=s_dict.get("title") or f"Section {i+1}",
                content=s_dict.get("content", ""),
                key_points=s_dict.get("key_points", []),
                examples=s_dict.get("examples", []),
                formulas=s_dict.get("formulas", []),
                common_mistakes=s_dict.get("common_mistakes", []),
                callouts=callouts_list,
                visual_spec=visual_obj
            )
            sections.append(sec)

        # Fallback if LLM generated zero sections
        if not sections:
            sections.append(NoteSection(
                section_type="overview",
                title="Overview",
                content=f"Comprehensive study notes for {ctx.topic}.",
                key_points=[f"Key principles of {ctx.topic}"]
            ))

        doc = NotesDocument(
            id=note_id,
            title=title,
            subject=ctx.subject,
            class_level=ctx.class_level,
            topic=ctx.topic,
            curriculum=ctx.resolved_context.curriculum if getattr(ctx, "resolved_context", None) and ctx.resolved_context.curriculum else (ctx.curriculum.board if hasattr(ctx.curriculum, "board") and ctx.curriculum.board else str(ctx.curriculum or "CBSE")),
            language=ctx.language,
            mode=ctx.mode,
            selected_formats=decision.selected_formats,
            depth=decision.depth,
            difficulty=decision.difficulty,
            sections=sections,
            source_citations=ctx.source_evidence,
            lineage=ctx.lineage_ids
        )
        return doc

    @staticmethod
    async def _attempt_repair(
        doc: NotesDocument,
        ctx: CanonicalNotesContext,
        decision: DecisionOutput
    ) -> NotesDocument:
        """Executes a single bounded refinement turn targeting specific validator warnings."""
        repair_prompt = f"""
The study notes you generated for '{doc.topic}' ({doc.class_level}) had the following quality validator warnings:
{chr(10).join([f"- {w}" for w in doc.quality.warnings])}

Please update the sections JSON to address these warnings directly:
1. Ensure all missing sections ({', '.join(decision.required_sections)}) are provided with rich content.
2. Ensure vocabulary matches {doc.class_level}.
3. Address student misconceptions explicitly.

Return the complete improved JSON matching the schema:
{{"title": "{doc.title}", "sections": [...]}}
"""
        try:
            repaired_json = await ai_router.generate_json(
                task="repair",
                messages=[
                    {"role": "system", "content": "You are an educational content QA repair agent. Return ONLY valid JSON."},
                    {"role": "user", "content": repair_prompt}
                ],
                temperature=0.1,
                max_tokens=4096,
                timeout=30.0
            )
            repaired_doc = NotesGenerator._parse_llm_response(repaired_json, ctx, decision)
            repaired_doc.id = doc.id
            repaired_doc.quality = NotesValidator.evaluate(repaired_doc, ctx, decision)
            return repaired_doc
        except Exception as e:
            logger.warning(f"Repair turn failed, keeping original document: {e}")
            return doc

    @staticmethod
    def _generate_deterministic_fallback(
        ctx: CanonicalNotesContext,
        decision: Any
    ) -> NotesDocument:
        """Guarantees the system never crashes even during complete AI provider downtime."""
        from app.services.notes.generation.engine import _build_deterministic_fallback, ensure_generation_plan
        plan = ensure_generation_plan(decision, ctx)
        doc = _build_deterministic_fallback(ctx, plan)
        doc.quality = NotesValidator.evaluate(doc, ctx, decision)
        return doc

