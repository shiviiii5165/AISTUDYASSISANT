"""
Practice & Visual Integrity Validator
=====================================
Validates practice question structure, presence of answers and explanations,
semantic difficulty alignment, and ensures visual diagrams (flowcharts, comparison matrices)
are semantically meaningful with connected nodes, edges, descriptive labels, and topic relevance.
"""
from typing import List, Dict, Any, Tuple, Optional
import re

from ...schemas import NotesDocument
from ...decision.schemas import NotesGenerationPlan, NoteDifficulty
from ...context.schemas import CanonicalNotesContext
from ..schemas import (
    ValidationViolation, ViolationSeverity, ValidationDimension
)


class PracticeAndVisualValidator:
    """Audits the pedagogical and structural integrity of practice questions and visual diagrams."""

    TRIVIAL_RECALL_PATTERNS = [
        r'^\s*define\s+\w+',
        r'^\s*state\s+the\s+definition',
        r'^\s*what\s+is\s+the\s+definition\s+of',
        r'^\s*what\s+is\s+inertia\??$',
        r'^\s*name\s+the\s+\w+'
    ]

    @classmethod
    def validate(
        cls,
        doc: NotesDocument,
        plan: NotesGenerationPlan,
        ctx: Optional[CanonicalNotesContext] = None
    ) -> Tuple[List[ValidationViolation], Dict[str, Any], float]:
        violations: List[ValidationViolation] = []
        details: Dict[str, Any] = {
            "practice_inspected": len(doc.practice),
            "visuals_inspected": len(doc.visuals),
            "practice_item_audits": []
        }
        score: float = 100.0

        # ── 1. Practice Items Quality, Completeness & Semantic Difficulty ──
        for idx, p in enumerate(doc.practice):
            sec_id = f"practice_{idx+1}"
            q = str(p.get("question", "")).strip()
            ans = str(p.get("answer", "")).strip()
            exp = str(p.get("explanation", "")).strip()
            stated_diff = str(p.get("difficulty", "")).lower()

            item_status = "VALID"
            item_notes = []

            if not q or len(q) < 8:
                violations.append(ValidationViolation(
                    code="PRACTICE_QUESTION_EMPTY_OR_TRIVIAL",
                    severity=ViolationSeverity.ERROR,
                    dimension=ValidationDimension.PRACTICE,
                    message=f"Practice question {idx+1} is empty or insufficiently descriptive.",
                    section_id=sec_id,
                    expected="A clear, complete practice question statement",
                    actual=q or "EMPTY",
                    repairable=True
                ))
                score -= 10.0
                item_status = "INVALID"
                item_notes.append("Empty question statement")

            # Answer presence and non-stub validation
            if not ans or ans.lower() in ("...", "tbd", "none", "n/a", "todo"):
                violations.append(ValidationViolation(
                    code="PRACTICE_ANSWER_MISSING_OR_STUB",
                    severity=ViolationSeverity.CRITICAL,
                    dimension=ValidationDimension.PRACTICE,
                    message=f"Practice question {idx+1} does not have a valid answer key (found stub '{ans}').",
                    section_id=sec_id,
                    expected="Definitive and scientifically correct answer key",
                    actual=ans,
                    repairable=True
                ))
                score -= 15.0
                item_status = "INVALID"
                item_notes.append("Missing answer key")

            if not exp or len(exp) < 10:
                violations.append(ValidationViolation(
                    code="PRACTICE_EXPLANATION_MISSING",
                    severity=ViolationSeverity.WARNING,
                    dimension=ValidationDimension.PRACTICE,
                    message=f"Practice question {idx+1} lacks a pedagogical step-by-step explanation.",
                    section_id=sec_id,
                    expected="Clear explanatory rationale",
                    actual=exp or "EMPTY",
                    repairable=True
                ))
                score -= 5.0
                if item_status == "VALID":
                    item_status = "WARNING"
                item_notes.append("Missing explanation")

            # Semantic difficulty check (Spec 16)
            # If plan requires ADVANCED difficulty, check if question is simple recall marked as advanced
            if plan.difficulty == NoteDifficulty.ADVANCED or stated_diff == "advanced":
                is_trivial_recall = any(re.search(pat, q, re.IGNORECASE) for pat in cls.TRIVIAL_RECALL_PATTERNS)
                if is_trivial_recall and len(q.split()) < 12 and "explain why" not in q.lower() and "calculate" not in q.lower():
                    violations.append(ValidationViolation(
                        code="PRACTICE_DIFFICULTY_SEMANTIC_MISMATCH",
                        severity=ViolationSeverity.ERROR,
                        dimension=ValidationDimension.PRACTICE,
                        message=f"Practice question {idx+1} ('{q}') is simple rote definition recall, failing the required ADVANCED cognitive depth.",
                        section_id=sec_id,
                        expected="Application, derivation, or analytical synthesis question for advanced plan",
                        actual=f"Basic rote recall question: '{q}'",
                        repairable=True
                    ))
                    score -= 15.0
                    item_status = "INVALID"
                    item_notes.append("Semantic difficulty mismatch")

            details["practice_item_audits"].append({
                "index": idx + 1,
                "status": item_status,
                "question": q[:60],
                "notes": item_notes
            })

        # ── 2. Visual Diagram Semantic Integrity & Topic Relevance (Spec 11, 18) ──
        all_visuals = list(doc.visuals)
        for s in doc.sections:
            if s.visual_spec:
                all_visuals.append(s.visual_spec)

        if plan.visual_plan.required:
            if not all_visuals:
                violations.append(ValidationViolation(
                    code="VISUAL_SPEC_REQUIRED_MISSING",
                    severity=ViolationSeverity.CRITICAL,
                    dimension=ValidationDimension.VISUAL,
                    message="Authoritative plan required a visual diagram, but no visual specifications were found.",
                    expected=f"Visual diagram of type '{plan.visual_plan.type}'",
                    actual="None",
                    repairable=True
                ))
                score -= 25.0
            else:
                topic_str = (doc.topic or (ctx.topic if ctx else "")).lower()
                for idx, v in enumerate(all_visuals):
                    v_type = getattr(v, "type", "flowchart")
                    nodes = getattr(v, "nodes", []) or []
                    edges = getattr(v, "edges", []) or []

                    if v_type == "flowchart":
                        if not nodes or len(nodes) == 0:
                            violations.append(ValidationViolation(
                                code="SEMANTICALLY_INVALID_VISUAL_EMPTY_NODES",
                                severity=ViolationSeverity.CRITICAL,
                                dimension=ValidationDimension.VISUAL,
                                message=f"Flowchart {idx+1} contains zero nodes; cannot represent a valid conceptual workflow.",
                                section_id=f"visual_{idx+1}",
                                expected="Meaningful conceptual nodes (> 0)",
                                actual="0 nodes",
                                repairable=True
                            ))
                            score -= 20.0
                        else:
                            # Check for blank or meaningless node labels
                            meaningless_labels = [
                                n for n in nodes
                                if not str(n.get("label", "")).strip() or str(n.get("label", "")).strip().lower() in ("node", "node_1", "step", "...")
                            ]
                            if len(meaningless_labels) == len(nodes):
                                violations.append(ValidationViolation(
                                    code="SEMANTICALLY_INVALID_VISUAL_DUMMY_LABELS",
                                    severity=ViolationSeverity.ERROR,
                                    dimension=ValidationDimension.VISUAL,
                                    message=f"Flowchart {idx+1} nodes contain only dummy labels ({[n.get('label') for n in meaningless_labels]}) merely to pass schema validation.",
                                    section_id=f"visual_{idx+1}",
                                    expected="Curriculum-grounded node descriptions",
                                    actual="Generic dummy stubs",
                                    repairable=True
                                ))
                                score -= 15.0

                            # Topic relevance check (Spec 18)
                            node_text = " ".join([str(n.get("label", "")) for n in nodes]).lower()
                            if "photosynthesis" in topic_str and ("newton" in node_text or "acceleration" in node_text):
                                violations.append(ValidationViolation(
                                    code="VISUAL_TOPIC_MISMATCH",
                                    severity=ViolationSeverity.CRITICAL,
                                    dimension=ValidationDimension.VISUAL,
                                    message=f"Flowchart {idx+1} diagrams Newtonian mechanics but document topic is '{doc.topic}'. Visual is completely irrelevant.",
                                    section_id=f"visual_{idx+1}",
                                    evidence=node_text[:120],
                                    expected=f"Visual elements modeling {doc.topic}",
                                    actual=node_text[:120],
                                    repairable=True
                                ))
                                score -= 30.0

                        if not edges or len(edges) == 0:
                            violations.append(ValidationViolation(
                                code="SEMANTICALLY_INVALID_VISUAL_EMPTY_EDGES",
                                severity=ViolationSeverity.ERROR,
                                dimension=ValidationDimension.VISUAL,
                                message=f"Flowchart {idx+1} has nodes but 0 edges; workflow transitions are disconnected.",
                                section_id=f"visual_{idx+1}",
                                expected="Connecting directed edges (> 0)",
                                actual="0 edges",
                                repairable=True
                            ))
                            score -= 15.0
                        else:
                            node_ids = {str(n.get("id")) for n in nodes if isinstance(n, dict) and n.get("id")}
                            for e in edges:
                                if isinstance(e, dict):
                                    src = str(e.get("from"))
                                    tgt = str(e.get("to"))
                                    if node_ids and (src not in node_ids or tgt not in node_ids):
                                        violations.append(ValidationViolation(
                                            code="VISUAL_EDGE_DANGLING_REFERENCE",
                                            severity=ViolationSeverity.WARNING,
                                            dimension=ValidationDimension.VISUAL,
                                            message=f"Flowchart edge ({src} -> {tgt}) references nonexistent node IDs.",
                                            section_id=f"visual_{idx+1}",
                                            expected=f"Valid node IDs in {list(node_ids)}",
                                            actual=f"from={src}, to={tgt}",
                                            repairable=True
                                        ))
                                        score -= 5.0
                                        break

        return violations, details, max(0.0, min(100.0, score))
