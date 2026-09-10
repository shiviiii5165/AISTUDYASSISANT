"""
Practice & Visual Integrity Validator
=====================================
Validates practice question structure, presence of answers and explanations,
and ensures visual diagrams (flowcharts, comparison matrices) are semantically
meaningful with connected nodes, edges, and descriptive labels.
"""
from typing import List, Dict, Any, Tuple
import re

from ...schemas import NotesDocument
from ...decision.schemas import NotesGenerationPlan
from ..schemas import (
    ValidationViolation, ViolationSeverity, ValidationDimension
)


class PracticeAndVisualValidator:
    """Audits the pedagogical and structural integrity of practice questions and visual diagrams."""

    @staticmethod
    def validate(
        doc: NotesDocument,
        plan: NotesGenerationPlan
    ) -> Tuple[List[ValidationViolation], Dict[str, Any], float]:
        violations: List[ValidationViolation] = []
        details: Dict[str, Any] = {"practice_inspected": len(doc.practice), "visuals_inspected": len(doc.visuals)}
        score: float = 100.0

        # ── 1. Practice Items Quality & Completeness ──
        for idx, p in enumerate(doc.practice):
            sec_id = f"practice_{idx+1}"
            q = str(p.get("question", "")).strip()
            ans = str(p.get("answer", "")).strip()
            exp = str(p.get("explanation", "")).strip()

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

            # Answer presence and non-stub validation (Spec 21 & 22)
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

        # ── 2. Visual Diagram Semantic Integrity (Spec 11 & 24) ──
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
                for idx, v in enumerate(all_visuals):
                    v_type = getattr(v, "type", "flowchart")
                    nodes = getattr(v, "nodes", []) or []
                    edges = getattr(v, "edges", []) or []

                    if v_type == "flowchart":
                        # Must have meaningful nodes and edges
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
                            # Check edge integrity: edges connect existing node IDs
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
