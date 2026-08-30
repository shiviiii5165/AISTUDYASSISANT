from typing import List, Dict, Any, Optional, Set, Tuple
from .schemas import (
    CourseGraph, CourseUnit, ConceptNode, DependencyEdge, BloomLevel, 
    CourseCoverage, SemesterPlan, SemesterScheduledLesson, LearningRoadmap, StageStatus
)
from datetime import datetime, timedelta


class CourseIntelligenceEngine:
    """
    Manages course structure, concept graphs, cycle prevention,
    coverage calculations, and semester-level calendar generation.
    """

    @staticmethod
    def build_concept_graph(
        course_id: str,
        title: str,
        units: List[Dict[str, Any]],
        concepts: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]]
    ) -> CourseGraph:
        """
        Builds and validates a structured concept graph.
        """
        course_units = []
        for i, u in enumerate(units):
            course_units.append(CourseUnit(
                id=u.get("id", f"unit_{i+1}"),
                unit_number=u.get("unit_number", i+1),
                title=u.get("title", f"Unit {i+1}"),
                description=u.get("description", ""),
                topics=u.get("topics", []),
                estimated_hours=float(u.get("estimated_hours", 4.0)),
                coverage_percentage=int(u.get("coverage_percentage", 0))
            ))

        concept_nodes = []
        for c in concepts:
            bloom = c.get("bloom_level", "understand")
            if isinstance(bloom, str):
                try:
                    bloom = BloomLevel(bloom.lower())
                except ValueError:
                    bloom = BloomLevel.UNDERSTAND
            
            concept_nodes.append(ConceptNode(
                id=c.get("id", ""),
                title=c.get("title", ""),
                description=c.get("description", ""),
                unit_id=c.get("unit_id"),
                prerequisite_ids=c.get("prerequisite_ids", []),
                bloom_level=bloom
            ))

        edges = []
        for d in dependencies:
            edges.append(DependencyEdge(
                source=d.get("source", ""),
                target=d.get("target", ""),
                edge_type=d.get("edge_type", "prerequisite_of"),
                strength=float(d.get("strength", 1.0))
            ))

        graph = CourseGraph(
            course_id=course_id,
            title=title,
            units=course_units,
            nodes=concept_nodes,
            edges=edges
        )

        # Validate that graph has no circular dependencies
        CourseIntelligenceEngine.detect_and_break_cycles(graph)
        return graph

    @staticmethod
    def detect_and_break_cycles(graph: CourseGraph, max_depth: int = 10) -> List[Tuple[str, str]]:
        """
        Detects cycles in prerequisite relationships using DFS with cycle prevention.
        Removes offending edges to ensure a strict DAG.
        """
        adj: Dict[str, List[str]] = {node.id: [] for node in graph.nodes}
        for edge in graph.edges:
            if edge.edge_type in ["prerequisite_of", "depends_on"]:
                if edge.source in adj:
                    adj[edge.source].append(edge.target)

        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        cycles_found: List[Tuple[str, str]] = []

        def dfs(node_id: str, depth: int) -> bool:
            if depth > max_depth:
                return False
            visited.add(node_id)
            rec_stack.add(node_id)

            for neighbor in adj.get(node_id, []):
                if neighbor not in visited:
                    if dfs(neighbor, depth + 1):
                        return True
                elif neighbor in rec_stack:
                    cycles_found.append((node_id, neighbor))
                    return True

            rec_stack.remove(node_id)
            return False

        for node in graph.nodes:
            if node.id not in visited:
                dfs(node.id, 0)

        if cycles_found:
            # Remove cycle-forming edges from graph
            broken = set(cycles_found)
            graph.edges = [e for e in graph.edges if (e.source, e.target) not in broken]

        return cycles_found

    @staticmethod
    def get_prerequisite_closure(
        graph: CourseGraph,
        concept_id: str,
        max_depth: int = 5
    ) -> List[str]:
        """
        Returns all transitive prerequisites for a concept up to max_depth.
        Guarantees no infinite loops.
        """
        prereqs: List[str] = []
        visited: Set[str] = set()
        node_map = {n.id: n for n in graph.nodes}

        def traverse(cid: str, current_depth: int):
            if current_depth > max_depth or cid in visited:
                return
            visited.add(cid)
            node = node_map.get(cid)
            if not node:
                return
            for pid in node.prerequisite_ids:
                if pid not in visited:
                    prereqs.append(pid)
                    traverse(pid, current_depth + 1)

        traverse(concept_id, 1)
        return prereqs

    @staticmethod
    def compute_course_coverage(
        units: List[CourseUnit],
        completed_concept_ids: Set[str]
    ) -> CourseCoverage:
        """
        Calculates unit-by-unit and aggregate course coverage percentage.
        """
        if not units:
            return CourseCoverage(total_units=0, covered_units=0, coverage_percentage=0, unit_breakdown=[])

        total_units = len(units)
        covered_count = 0
        breakdown = []

        for u in units:
            total_topics = len(u.topics)
            if total_topics == 0:
                pct = 100 if u.id in completed_concept_ids else 0
            else:
                covered_topics = sum(1 for t in u.topics if t in completed_concept_ids or u.id in completed_concept_ids)
                pct = int((covered_topics / total_topics) * 100)

            if pct >= 80:
                covered_count += 1
                status = "Covered"
            elif pct > 0:
                status = "Partially Covered"
            else:
                status = "Not Covered"

            breakdown.append({
                "unit_id": u.id,
                "unit_number": u.unit_number,
                "title": u.title,
                "coverage_percentage": pct,
                "status": status
            })

        overall_pct = int((covered_count / total_units) * 100) if total_units > 0 else 0

        return CourseCoverage(
            total_units=total_units,
            covered_units=covered_count,
            coverage_percentage=overall_pct,
            unit_breakdown=breakdown
        )

    @staticmethod
    def generate_semester_plan(
        course_id: str,
        units: List[CourseUnit],
        start_date: datetime,
        total_weeks: int = 14,
        classes_per_week: int = 3,
        minutes_per_class: int = 60,
        exam_weeks: Optional[List[int]] = None,
        holidays: Optional[List[datetime]] = None
    ) -> SemesterPlan:
        """
        Deterministically builds a full semester academic schedule mapping units to teaching sessions.
        """
        exam_weeks = exam_weeks or [7, 14]
        holiday_dates = set(h.date() if isinstance(h, datetime) else h for h in (holidays or []))

        scheduled: List[SemesterScheduledLesson] = []
        current_date = start_date

        all_topics: List[Tuple[str, str, bool]] = []
        for u in units:
            for t in u.topics:
                is_lab = "lab" in t.lower() or "practical" in t.lower() or "implementation" in t.lower()
                all_topics.append((u.title, t, is_lab))

        topic_idx = 0
        total_topics = len(all_topics)

        for week in range(1, total_weeks + 1):
            is_exam_week = week in exam_weeks

            for session in range(1, classes_per_week + 1):
                while current_date.weekday() >= 5:  # Skip weekends
                    current_date += timedelta(days=1)

                is_hol = current_date.date() in holiday_dates
                date_str = current_date.strftime("%Y-%m-%d")

                if is_hol:
                    scheduled.append(SemesterScheduledLesson(
                        week_number=week,
                        session_number=session,
                        date_str=date_str,
                        unit_title="Holiday",
                        topic_title="Institute Holiday / Recess",
                        duration_minutes=minutes_per_class,
                        is_holiday=True
                    ))
                elif is_exam_week:
                    scheduled.append(SemesterScheduledLesson(
                        week_number=week,
                        session_number=session,
                        date_str=date_str,
                        unit_title="Assessments",
                        topic_title="Mid-term / End-term Examination & Evaluation",
                        duration_minutes=minutes_per_class,
                        is_exam=True
                    ))
                else:
                    if topic_idx < total_topics:
                        u_title, t_title, is_lab = all_topics[topic_idx]
                        topic_idx += 1
                    else:
                        u_title = "Revision & Remediation"
                        t_title = "Comprehensive Review & Viva Prep"
                        is_lab = False

                    scheduled.append(SemesterScheduledLesson(
                        week_number=week,
                        session_number=session,
                        date_str=date_str,
                        unit_title=u_title,
                        topic_title=t_title,
                        duration_minutes=minutes_per_class,
                        is_practical=is_lab
                    ))

                current_date += timedelta(days=2 if session < classes_per_week else 3)

        coverage = 100 if total_topics == 0 or topic_idx >= total_topics else int((topic_idx / total_topics) * 100)

        return SemesterPlan(
            course_id=course_id,
            total_weeks=total_weeks,
            classes_per_week=classes_per_week,
            minutes_per_class=minutes_per_class,
            scheduled_lessons=scheduled,
            coverage_percentage=coverage
        )
