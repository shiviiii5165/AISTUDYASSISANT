"""
LearnByGenie — Feature 3: Prerequisite Graph Auditor
=====================================================
Automated topology audit service (§4, §40).
Detects:
- Cycles
- Self-edges
- Duplicate edges
- Inactive edges
- Orphan skills
- Broken skill ID references
"""
from typing import List, Dict, Set
from collections import defaultdict

from .schemas import GraphAuditReport, SkillPrerequisiteEdge
from .dag_engine import PrerequisiteDAGEngine
from app.services.diagnostic.curriculum_blueprint import CANONICAL_SKILLS, get_skill


class GraphAuditor:
    """
    Deterministic audit tool for prerequisite graph integrity.
    """

    @staticmethod
    def audit_graph(edges: List[SkillPrerequisiteEdge]) -> GraphAuditReport:
        all_canonical_ids = {s.id for s in CANONICAL_SKILLS}

        seen_edges: Set[tuple] = set()
        duplicate_edges: List[str] = []
        self_edges: List[str] = []
        inactive_edges: List[str] = []
        orphan_references: List[str] = []

        active_edges: List[SkillPrerequisiteEdge] = []

        for e in edges:
            edge_tuple = (e.prerequisite_skill_id, e.dependent_skill_id)

            if not e.is_active:
                inactive_edges.append(f"{e.prerequisite_skill_id} -> {e.dependent_skill_id}")
                continue

            # Check self-edge
            if e.prerequisite_skill_id == e.dependent_skill_id:
                self_edges.append(e.prerequisite_skill_id)

            # Check duplicate edge
            if edge_tuple in seen_edges:
                duplicate_edges.append(f"{edge_tuple[0]} -> {edge_tuple[1]}")
            else:
                seen_edges.add(edge_tuple)

            # Check reference validity against canonical skills
            if e.prerequisite_skill_id not in all_canonical_ids:
                orphan_references.append(e.prerequisite_skill_id)
            if e.dependent_skill_id not in all_canonical_ids:
                orphan_references.append(e.dependent_skill_id)

            active_edges.append(e)

        # Build DAG engine to detect cycles
        dag = PrerequisiteDAGEngine(active_edges)
        cycles = dag.detect_cycles()

        # Identify orphan skills (skills with 0 in-degree and 0 out-degree)
        connected_skills = set()
        for p, d in seen_edges:
            connected_skills.add(p)
            connected_skills.add(d)

        isolated_skills = [
            s.id for s in CANONICAL_SKILLS
            if s.id not in connected_skills
        ]

        is_healthy = (
            len(cycles) == 0 and
            len(self_edges) == 0 and
            len(duplicate_edges) == 0 and
            len(orphan_references) == 0
        )

        return GraphAuditReport(
            total_skills=len(all_canonical_ids),
            total_edges=len(edges),
            is_dag=(len(cycles) == 0),
            cycles=cycles,
            orphan_skills=orphan_references,  # broken foreign references
            self_edges=self_edges,
            duplicate_edges=duplicate_edges,
            inactive_edges=inactive_edges,
            is_healthy=is_healthy
        )
