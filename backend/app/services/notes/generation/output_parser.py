"""
LearnByGenie Notes Generation Engine — Structured Response Parser
===============================================================
Parses raw LLM JSON responses into strongly typed NotesDocument instances,
extracting sections, visual specifications, practice items, and metadata.
Enforces strict plan authority, citation provenance, and handles malformed inputs safely.
"""
import uuid
import json
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set

from app.services.notes.schemas import (
    NotesDocument, NoteSection, VisualSpec, CalloutItem,
    NoteFormat, NoteDepth, NoteDifficulty
)
from app.services.notes.context.schemas import CanonicalNotesContext
from app.services.notes.decision.schemas import NotesGenerationPlan
from .schemas import GroundedSources, GenerationMode

logger = logging.getLogger("learnbygenie.notes.generation.parser")


class OutputParser:
    """Parses, sanitizes, and maps raw model JSON into a verified NotesDocument."""

    @classmethod
    def parse_response(
        cls,
        raw_output: Any,
        ctx: CanonicalNotesContext,
        plan: NotesGenerationPlan,
        sources: Optional[GroundedSources] = None,
        model_name: Optional[str] = None
    ) -> NotesDocument:
        """Parses model response into NotesDocument without throwing unhandled exceptions."""
        data: Dict[str, Any] = {}
        repairs_performed: List[str] = []
        warnings: List[str] = []

        # ── 0. Safe JSON Extraction ──
        if raw_output is None:
            data = {}
            warnings.append("Model returned null output.")
        elif isinstance(raw_output, str):
            text = raw_output.strip()
            if not text:
                data = {}
                warnings.append("Model returned empty string output.")
            else:
                # Strip markdown code fences if present
                if "```" in text:
                    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
                    if match:
                        text = match.group(1).strip()
                    else:
                        text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
                try:
                    data = json.loads(text)
                except Exception as e:
                    logger.warning(f"Failed to parse model string as JSON: {e}")
                    warnings.append(f"Malformed JSON output: {str(e)[:80]}")
                    data = {}
        elif isinstance(raw_output, dict):
            data = raw_output
        elif isinstance(raw_output, list):
            # Model returned array of sections or objects
            data = {"sections": raw_output}
            repairs_performed.append("normalized_list_to_dict_wrapper")
        else:
            data = {}
            warnings.append(f"Unexpected output type: {type(raw_output).__name__}")

        doc_id = f"note_{uuid.uuid4().hex[:12]}"
        title = data.get("title") or f"{ctx.topic} — {ctx.class_level} Study Notes"
        learning_objectives = data.get("learning_objectives")
        if not isinstance(learning_objectives, list):
            learning_objectives = list(ctx.learning_objectives)

        # ── 1. Parse & Deduplicate Sections ──
        raw_sections = data.get("sections")
        if not isinstance(raw_sections, list):
            raw_sections = []

        sections: List[NoteSection] = []
        visuals_collected: List[VisualSpec] = []
        seen_section_signatures: Set[str] = set()

        for i, s_dict in enumerate(raw_sections):
            if not isinstance(s_dict, dict):
                continue

            sec_id = s_dict.get("id") or f"sec_{i+1}_{uuid.uuid4().hex[:6]}"
            sec_type = str(s_dict.get("section_type") or "core_concept").strip()
            sec_title = str(s_dict.get("title") or f"Section {i+1}").strip()
            sec_content = str(s_dict.get("content") or "").strip()
            target_concept = s_dict.get("target_concept")

            # Duplicate detection by signature
            sig = f"{sec_type}:{sec_title.lower()}"
            if sig in seen_section_signatures:
                repairs_performed.append(f"deduplicated_section:{sec_type}")
                continue
            seen_section_signatures.add(sig)

            # Parse visual spec
            visual_data = s_dict.get("visual_spec")
            visual_obj: Optional[VisualSpec] = None
            if isinstance(visual_data, dict) and visual_data.get("type"):
                nodes = visual_data.get("nodes") or []
                edges = visual_data.get("edges") or []
                visual_obj = VisualSpec(
                    type=str(visual_data.get("type", "flowchart")),
                    title=str(visual_data.get("title") or sec_title),
                    nodes=nodes if isinstance(nodes, list) else [],
                    edges=edges if isinstance(edges, list) else [],
                    mermaid_code=visual_data.get("mermaid_code")
                )
                visuals_collected.append(visual_obj)

            # Parse callouts safely
            callouts_raw = s_dict.get("callouts")
            callouts_list: List[CalloutItem] = []
            if isinstance(callouts_raw, list):
                for c in callouts_raw:
                    if isinstance(c, dict):
                        callouts_list.append(CalloutItem(
                            type=str(c.get("type", "tip")),
                            title=str(c.get("title", "Note")),
                            text=str(c.get("text", ""))
                        ))

            # Normalize list fields
            key_points = s_dict.get("key_points")
            examples = s_dict.get("examples")
            formulas = s_dict.get("formulas")
            common_mistakes = s_dict.get("common_mistakes")

            sec = NoteSection(
                id=sec_id,
                section_type=sec_type,
                title=sec_title,
                content=sec_content,
                target_concept=target_concept,
                key_points=key_points if isinstance(key_points, list) else [],
                examples=examples if isinstance(examples, list) else [],
                formulas=formulas if isinstance(formulas, list) else [],
                common_mistakes=common_mistakes if isinstance(common_mistakes, list) else [],
                callouts=callouts_list,
                visual_spec=visual_obj
            )
            sections.append(sec)

        # ── 1b. Parse Top-Level Visual Spec if Present ──
        top_visual = data.get("visual_spec") or data.get("visual")
        if isinstance(top_visual, dict) and top_visual.get("type"):
            nodes = top_visual.get("nodes") or []
            edges = top_visual.get("edges") or []
            v_obj = VisualSpec(
                type=str(top_visual.get("type", "flowchart")),
                title=str(top_visual.get("title") or f"{ctx.topic} Visual"),
                nodes=nodes if isinstance(nodes, list) else [],
                edges=edges if isinstance(edges, list) else [],
                mermaid_code=top_visual.get("mermaid_code") or top_visual.get("mermaid")
            )
            visuals_collected.append(v_obj)
            if sections and not sections[0].visual_spec:
                sections[0].visual_spec = v_obj

        # ── 2. Parse Practice Items (Plan Difficulty Authoritative) ──
        raw_practice = data.get("practice")
        if not isinstance(raw_practice, list):
            raw_practice = []

        practice_items: List[Dict[str, Any]] = []
        for p in raw_practice:
            if isinstance(p, dict) and p.get("question"):
                # Plan practice difficulty is strictly authoritative
                practice_items.append({
                    "question": str(p.get("question", "")).strip(),
                    "question_type": str(p.get("question_type", "recall")).strip(),
                    "difficulty": plan.practice_plan.difficulty,
                    "answer": str(p.get("answer", "")).strip(),
                    "explanation": str(p.get("explanation", "")).strip(),
                    "target_concept": str(p.get("target_concept") or ctx.topic).strip()
                })

        # ── 3. Parse Revision Summary ──
        revision_summary = data.get("revision_summary")
        if not isinstance(revision_summary, dict):
            revision_summary = None

        # ── 4. Parse & Validate Source Citations ──
        valid_source_ids: Set[str] = set()
        if sources and sources.items:
            valid_source_ids = {s.source_id for s in sources.items}
        elif ctx.source_evidence:
            for ev in ctx.source_evidence:
                if isinstance(ev, dict) and ev.get("source_id"):
                    valid_source_ids.add(ev["source_id"])

        raw_citations = data.get("source_citations")
        source_citations: List[Dict[str, Any]] = []
        if isinstance(raw_citations, list):
            for c in raw_citations:
                if isinstance(c, dict):
                    cid = c.get("source_id")
                    if valid_source_ids:
                        if cid in valid_source_ids:
                            source_citations.append(c)
                        else:
                            repairs_performed.append(f"rejected_invalid_citation:{cid}")
                            warnings.append(f"Rejected citation to nonexistent source ID: '{cid}'")
                    else:
                        # No verified sources provided, retain if present
                        source_citations.append(c)
        elif ctx.source_evidence:
            source_citations = list(ctx.source_evidence)

        # ── 5. Generation Metadata (Plan Is Authoritative) ──
        gen_meta = {
            "model": model_name or "default_model",
            "schema_version": "1.0",
            "plan_schema_version": plan.schema_version,
            "purpose": plan.purpose.primary,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "decision_confidence": plan.decision_confidence,
            "ai_generation": True,
            "generation_mode": GenerationMode.AI_GENERATED.value,
            "structural_repairs": repairs_performed,
            "generation_warnings": warnings
        }

        # ── 6. Assemble NotesDocument (Plan Dictates Contract) ──
        curriculum_val = (
            ctx.resolved_context.curriculum
            if getattr(ctx, "resolved_context", None) and ctx.resolved_context.curriculum
            else str(ctx.curriculum or "CBSE")
        )

        doc = NotesDocument(
            schema_version="1.0",
            id=doc_id,
            document_id=doc_id,
            title=title,
            subject=ctx.subject,
            class_level=ctx.class_level,
            topic=ctx.topic,
            curriculum=curriculum_val,
            language=ctx.language,
            mode=ctx.mode,
            learning_objectives=learning_objectives,
            # Plan is strictly authoritative for formats, depth, and difficulty
            selected_formats=plan.formats,
            depth=plan.depth,
            difficulty=plan.difficulty,
            sections=sections,
            visuals=visuals_collected,
            practice=practice_items,
            revision_summary=revision_summary,
            source_citations=source_citations,
            lineage=ctx.lineage_ids,
            generation_metadata=gen_meta,
            generation_warnings=warnings,
            generation_mode=GenerationMode.AI_GENERATED.value,
            structural_repairs=repairs_performed
        )
        return doc
