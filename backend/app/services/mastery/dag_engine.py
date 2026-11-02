"""
LearnByGenie — Feature 3: Prerequisite DAG Engine
==================================================
Directed Acyclic Graph topology engine providing:
- Cycle detection & validation (Kahn's / DFS algorithm)
- Topological sort & transitive dependencies
- Readiness computation (separating concept mastery from prerequisite readiness)
- Deterministic repair path traversal
- Explainable next concept recommendations
"""
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict, deque

from .schemas import (
    MasteryState, ReadinessState, SkillPrerequisiteEdge,
    RelationshipType, LearningRecommendation
)
from app.services.diagnostic.curriculum_blueprint import CANONICAL_SKILLS, get_skill, DiagnosticSkill


class PrerequisiteDAGEngine:
    """
    In-memory graph operations over canonical skills and prerequisite edges.
    """

    def __init__(self, edges: Optional[List[SkillPrerequisiteEdge]] = None):
        self.adj_list: Dict[str, Set[str]] = defaultdict(set)       # prereq -> dependents
        self.reverse_adj: Dict[str, Set[str]] = defaultdict(set)    # dependent -> prereqs
        self.edge_types: Dict[Tuple[str, str], RelationshipType] = {}
        self.all_skills: Set[str] = {s.id for s in CANONICAL_SKILLS}

        # Initialize from canonical skills if no custom edges provided
        if edges is not None:
            for e in edges:
                if e.is_active:
                    self.add_edge_internal(e.prerequisite_skill_id, e.dependent_skill_id, e.relationship_type)
        else:
            for s in CANONICAL_SKILLS:
                for pid in s.prerequisite_skill_ids:
                    self.add_edge_internal(pid, s.id, RelationshipType.STRICT_PREREQUISITE)

    def add_edge_internal(self, prereq_id: str, dependent_id: str, rel_type: RelationshipType = RelationshipType.STRICT_PREREQUISITE):
        self.adj_list[prereq_id].add(dependent_id)
        self.reverse_adj[dependent_id].add(prereq_id)
        self.edge_types[(prereq_id, dependent_id)] = rel_type
        self.all_skills.add(prereq_id)
        self.all_skills.add(dependent_id)

    # ─── 1. DAG VALIDATION & CYCLE DETECTION ──────────────────────────────────

    def detect_cycles(self) -> List[List[str]]:
        """
        Detects cycles in the prerequisite graph using DFS coloring.
        Returns list of cycle paths if any exist.
        """
        # 0 = unvisited, 1 = visiting, 2 = visited
        visited: Dict[str, int] = {s: 0 for s in self.all_skills}
        cycles: List[List[str]] = []
        path: List[str] = []

        def dfs(node: str):
            visited[node] = 1
            path.append(node)
            for neighbor in self.adj_list.get(node, []):
                if visited[neighbor] == 1:
                    # Cycle found! Extract cycle segment
                    cycle_start_idx = path.index(neighbor)
                    cycles.append(list(path[cycle_start_idx:]) + [neighbor])
                elif visited[neighbor] == 0:
                    dfs(neighbor)
            path.pop()
            visited[node] = 2

        for s in self.all_skills:
            if visited[s] == 0:
                dfs(s)

        return cycles

    def would_create_cycle(self, prereq_id: str, dependent_id: str) -> bool:
        """Checks if adding an edge prereq_id -> dependent_id would introduce a cycle."""
        if prereq_id == dependent_id:
            return True
        # Check if prereq_id is already reachable from dependent_id
        visited: Set[str] = set()
        queue = deque([dependent_id])
        while queue:
            curr = queue.popleft()
            if curr == prereq_id:
                return True
            for next_node in self.adj_list.get(curr, []):
                if next_node not in visited:
                    visited.add(next_node)
                    queue.append(next_node)
        return False

    def get_topological_order(self, subject: Optional[str] = None) -> List[str]:
        """Returns valid learning order of skills using Kahn's algorithm."""
        skills = [s for s in self.all_skills if not subject or (get_skill(s) and get_skill(s).subject.lower() == subject.lower())]
        skill_set = set(skills)

        in_degree: Dict[str, int] = {s: 0 for s in skills}
        for s in skills:
            for p in self.reverse_adj.get(s, []):
                if p in skill_set:
                    in_degree[s] += 1

        queue = deque([s for s in skills if in_degree[s] == 0])
        order: List[str] = []

        while queue:
            curr = queue.popleft()
            order.append(curr)
            for dep in self.adj_list.get(curr, []):
                if dep in skill_set:
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        queue.append(dep)

        return order

    # ─── 2. ANCESTRY & DEPENDENCY TRAVERSAL ────────────────────────────────────

    def get_immediate_prerequisites(self, skill_id: str) -> List[str]:
        return sorted(list(self.reverse_adj.get(skill_id, [])))

    def get_immediate_dependents(self, skill_id: str) -> List[str]:
        return sorted(list(self.adj_list.get(skill_id, [])))

    def get_all_prerequisites_transitive(self, skill_id: str) -> Set[str]:
        """Traverse upstream ancestors."""
        res: Set[str] = set()
        queue = deque(self.reverse_adj.get(skill_id, []))
        while queue:
            curr = queue.popleft()
            if curr not in res:
                res.add(curr)
                for p in self.reverse_adj.get(curr, []):
                    queue.append(p)
        return res

    def get_all_dependents_transitive(self, skill_id: str) -> Set[str]:
        """Traverse downstream dependents."""
        res: Set[str] = set()
        queue = deque(self.adj_list.get(skill_id, []))
        while queue:
            curr = queue.popleft()
            if curr not in res:
                res.add(curr)
                for d in self.adj_list.get(curr, []):
                    queue.append(d)
        return res

    # ─── 3. READINESS COMPUTATION ─────────────────────────────────────────────

    def compute_readiness(
        self,
        skill_id: str,
        student_mastery_map: Dict[str, MasteryState]
    ) -> Tuple[ReadinessState, List[str]]:
        """
        Determines if student is ready to learn skill_id based on strict prerequisites (§13).
        Returns (ReadinessState, blocking_prerequisite_ids).
        """
        prereqs = self.get_immediate_prerequisites(skill_id)
        if not prereqs:
            return ReadinessState.READY, []

        blocking_skills: List[str] = []
        has_unassessed = False
        has_developing = False
        all_secure = True

        for pid in prereqs:
            # Check relationship type
            rel = self.edge_types.get((pid, skill_id), RelationshipType.STRICT_PREREQUISITE)
            if rel != RelationshipType.STRICT_PREREQUISITE:
                continue

            state = student_mastery_map.get(pid, MasteryState.NOT_ASSESSED)

            if state == MasteryState.NEEDS_REPAIR or state == MasteryState.FRAGILE:
                blocking_skills.append(pid)
                all_secure = False
            elif state == MasteryState.NOT_ASSESSED:
                has_unassessed = True
                all_secure = False
            elif state == MasteryState.DEVELOPING:
                has_developing = True
                all_secure = False
            elif state == MasteryState.SECURE:
                pass

        if blocking_skills:
            return ReadinessState.BLOCKED_BY_PREREQUISITE, blocking_skills
        if all_secure:
            return ReadinessState.READY, []
        if has_developing:
            return ReadinessState.PARTIALLY_READY, []
        if has_unassessed:
            return ReadinessState.NOT_ENOUGH_EVIDENCE, []

        return ReadinessState.NOT_ENOUGH_EVIDENCE, []

    # ─── 4. REPAIR PATH DETERMINATION ─────────────────────────────────────────

    def get_repair_path(
        self,
        target_skill_id: str,
        student_mastery_map: Dict[str, MasteryState]
    ) -> List[str]:
        """
        Finds the shortest meaningful repair path (§14).
        Traverses upstream prerequisites to find the lowest broken foundational skill.
        Example: Calculus -> Functions -> Algebra -> Fractions.
        If Fractions are SECURE and Algebra needs repair, returns [Algebra, Functions, Calculus].
        """
        repair_chain: List[str] = []
        visited: Set[str] = set()

        def traverse(curr: str):
            if curr in visited:
                return
            visited.add(curr)

            # Check prerequisites first (depth first, foundational first)
            for p in sorted(self.reverse_adj.get(curr, [])):
                p_state = student_mastery_map.get(p, MasteryState.NOT_ASSESSED)
                if p_state in (MasteryState.NEEDS_REPAIR, MasteryState.FRAGILE, MasteryState.DEVELOPING):
                    traverse(p)

            curr_state = student_mastery_map.get(curr, MasteryState.NOT_ASSESSED)
            if curr_state in (MasteryState.NEEDS_REPAIR, MasteryState.FRAGILE) and curr not in repair_chain:
                repair_chain.append(curr)

        traverse(target_skill_id)

        # If target itself needs repair and not yet in chain
        t_state = student_mastery_map.get(target_skill_id, MasteryState.NOT_ASSESSED)
        if t_state in (MasteryState.NEEDS_REPAIR, MasteryState.FRAGILE) and target_skill_id not in repair_chain:
            repair_chain.append(target_skill_id)

        return repair_chain

    # ─── 5. NEXT CONCEPT RECOMMENDATIONS ──────────────────────────────────────

    def get_recommendations(
        self,
        subject: str,
        student_mastery_map: Dict[str, MasteryState]
    ) -> List[LearningRecommendation]:
        """
        Generates explainable next learning recommendations (§15).
        1. Priority 1 (Repair): Broken prerequisites that unblock higher concepts.
        2. Priority 2 (Next Unlocked): Next unlocked skills whose prerequisites are ready.
        """
        recommendations: List[LearningRecommendation] = []
        subject_skills = [
            s for s in self.all_skills
            if get_skill(s) and get_skill(s).subject.lower() == subject.lower()
        ]

        # 1. Identify skills that need repair
        repair_candidates: Set[str] = set()
        for sk in subject_skills:
            if student_mastery_map.get(sk) == MasteryState.NEEDS_REPAIR:
                repair_candidates.add(sk)

        # For each repair candidate, compute which downstream skills it unblocks
        for rep_sk in sorted(repair_candidates):
            sk_obj = get_skill(rep_sk)
            sk_name = sk_obj.skill_name if sk_obj else rep_sk
            unblocks = [
                dep for dep in self.get_all_dependents_transitive(rep_sk)
                if get_skill(dep) and get_skill(dep).subject.lower() == subject.lower()
            ]
            unblock_names = [get_skill(u).skill_name for u in unblocks if get_skill(u)]

            reason = f"Concept needs repair."
            if unblocks:
                reason += f" Repairing this will unlock: {', '.join(unblock_names[:2])}."

            recommendations.append(LearningRecommendation(
                skill_id=rep_sk,
                skill_name=sk_name,
                subject=subject,
                recommendation_type="REPAIR_PREREQUISITE",
                priority=1,
                reason=reason,
                unblocks_skills=unblocks
            ))

        # 2. Identify next unlocked concepts (readiness == READY and mastery != SECURE)
        unlocked_candidates: List[str] = []
        for sk in self.get_topological_order(subject):
            m_state = student_mastery_map.get(sk, MasteryState.NOT_ASSESSED)
            if m_state == MasteryState.SECURE:
                continue

            r_state, blockers = self.compute_readiness(sk, student_mastery_map)
            if r_state == ReadinessState.READY and sk not in repair_candidates:
                unlocked_candidates.append(sk)

        for unl_sk in unlocked_candidates[:3]:
            sk_obj = get_skill(unl_sk)
            sk_name = sk_obj.skill_name if sk_obj else unl_sk
            prereqs = self.get_immediate_prerequisites(unl_sk)
            prereq_names = [get_skill(p).skill_name for p in prereqs if get_skill(p)]

            if prereq_names:
                reason = f"Prerequisites ({', '.join(prereq_names)}) are secure. Ready for progression."
            else:
                reason = "Foundational starting concept with no prerequisite blockers."

            recommendations.append(LearningRecommendation(
                skill_id=unl_sk,
                skill_name=sk_name,
                subject=subject,
                recommendation_type="NEXT_CONCEPT",
                priority=2,
                reason=reason,
                unblocks_skills=list(self.adj_list.get(unl_sk, []))
            ))

        return sorted(recommendations, key=lambda r: (r.priority, r.skill_name))
