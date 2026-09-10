"""
TeachGenie Notes Generation Engine — Structured Response Parser
===============================================================
Parses raw LLM JSON responses into strongly typed NotesDocument instances,
extracting sections, visual specifications, practice items, and metadata.
"""
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.services.notes.schemas import (
    NotesDocument, NoteSection, VisualSpec, CalloutItem,
    NoteFormat, NoteDepth, NoteDifficulty
)
from app.services.notes.context.schemas import CanonicalNotesContext
from app.services.notes.decision.schemas import NotesGenerationPlan

logger = logging.getLogger("teachgenie.notes.generation.parser")


class OutputParser:
    """Parses, sanitizes, and maps raw model JSON into a verified NotesDocument."""

    @classmethod
    def parse_response(
        cls,
        raw_output: Any,
        ctx: CanonicalNotesContext,
        plan: NotesGenerationPlan,
        model_name: Optional[str] = None
    ) -> NotesDocument:
        """Parses model response into NotesDocument."""
        if isinstance(raw_output, str):
            try:
                data = json.loads(raw_output)
            except Exception as e:
                logger.warning(f"Failed to parse raw LLM output as JSON: {e}")
                data = {}
        elif isinstance(raw_output, dict):
            data = raw_output
        else:
            data = {}

        doc_id = f"note_{uuid.uuid4().hex[:12]}"
        title = data.get("title") or f"{ctx.topic} — {ctx.class_level} Study Notes"
        learning_objectives = data.get("learning_objectives") or list(ctx.learning_objectives)

        # ── 1. Parse Sections ──
        raw_sections = data.get("sections") or []
        sections: List[NoteSection] = []
        visuals_collected: List[VisualSpec] = []

        for i, s_dict in enumerate(raw_sections):
            if not isinstance(s_dict, dict):
                continue

            sec_id = s_dict.get("id") or f"sec_{i+1}_{uuid.uuid4().hex[:6]}"
            sec_type = s_dict.get("section_type") or "core_concept"
            sec_title = s_dict.get("title") or f"Section {i+1}"
            sec_content = s_dict.get("content") or ""
            target_concept = s_dict.get("target_concept")

            # Parse visual spec
            visual_data = s_dict.get("visual_spec")
            visual_obj: Optional[VisualSpec] = None
            if isinstance(visual_data, dict) and visual_data.get("type"):
                visual_obj = VisualSpec(
                    type=visual_data.get("type", "flowchart"),
                    title=visual_data.get("title") or sec_title,
                    nodes=visual_data.get("nodes", []),
                    edges=visual_data.get("edges", []),
                    mermaid_code=visual_data.get("mermaid_code")
                )
                visuals_collected.append(visual_obj)

            # Parse callouts
            callouts_list: List[CalloutItem] = []
            for c in s_dict.get("callouts", []):
                if isinstance(c, dict):
                    callouts_list.append(CalloutItem(
                        type=c.get("type", "tip"),
                        title=c.get("title", "Note"),
                        text=c.get("text", "")
                    ))

            sec = NoteSection(
                id=sec_id,
                section_type=sec_type,
                title=sec_title,
                content=sec_content,
                target_concept=target_concept,
                key_points=s_dict.get("key_points", []),
                examples=s_dict.get("examples", []),
                formulas=s_dict.get("formulas", []),
                common_mistakes=s_dict.get("common_mistakes", []),
                callouts=callouts_list,
                visual_spec=visual_obj
            )
            sections.append(sec)

        # ── 2. Parse Practice Items ──
        raw_practice = data.get("practice") or []
        practice_items: List[Dict[str, Any]] = []
        for p in raw_practice:
            if isinstance(p, dict) and p.get("question"):
                practice_items.append({
                    "question": p.get("question", ""),
                    "question_type": p.get("question_type", "recall"),
                    "difficulty": p.get("difficulty", plan.practice_plan.difficulty),
                    "answer": p.get("answer", ""),
                    "explanation": p.get("explanation", ""),
                    "target_concept": p.get("target_concept", ctx.topic)
                })

        # ── 3. Parse Revision Summary ──
        revision_summary = data.get("revision_summary")
        if not isinstance(revision_summary, dict):
            revision_summary = None

        # ── 4. Parse Source Citations ──
        source_citations = data.get("source_citations") or list(ctx.source_evidence)

        # ── 5. Generation Metadata ──
        gen_meta = {
            "model": model_name or "default_model",
            "schema_version": "1.0",
            "plan_schema_version": plan.schema_version,
            "purpose": plan.purpose.primary,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "decision_confidence": plan.decision_confidence
        }

        doc = NotesDocument(
            schema_version="1.0",
            id=doc_id,
            document_id=doc_id,
            title=title,
            subject=ctx.subject,
            class_level=ctx.class_level,
            topic=ctx.topic,
            curriculum=ctx.resolved_context.curriculum if getattr(ctx, "resolved_context", None) and ctx.resolved_context.curriculum else str(ctx.curriculum or "CBSE"),
            language=ctx.language,
            mode=ctx.mode,
            learning_objectives=learning_objectives,
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
            generation_warnings=[]
        )
        return doc
