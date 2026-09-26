"""
Canonical Concept Registry & Resolver for Lesson Planner VNext
==============================================================
Provides stable, canonical concept identification across multiple lesson plans,
roadmaps, and downstream features (Quiz, Live Quiz, TeachMe, Notes).

Key Properties:
1. Deterministic resolution of synonyms, aliases, and sub-topics to canonical IDs.
2. Cross-roadmap state reuse (student mastery in Roadmap A transfers to Roadmap B).
3. Namespace and versioning support (`cs.algo.dp.memoization`, namespace="core", version="1.0").
4. Prevention of ephemeral local-stage ID collisions (e.g. `stage_0_concept`).
"""

import re
import logging
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field
from ..schemas import CanonicalDomain

logger = logging.getLogger("teachgenie.lesson_planner.canonical_concepts")


class CandidateOrigin(str, Enum):
    KNOWLEDGE_PACK = "KNOWLEDGE_PACK"
    CURRICULUM_OBJECTIVE = "CURRICULUM_OBJECTIVE"
    STAGE_OBJECTIVE = "STAGE_OBJECTIVE"
    STAGE_CONTENT_FOCUS = "STAGE_CONTENT_FOCUS"
    PREREQUISITE_DAG = "PREREQUISITE_DAG"
    CANONICAL_REGISTRY_ALIAS = "CANONICAL_REGISTRY_ALIAS"
    PEDAGOGICAL_ARCHETYPE = "PEDAGOGICAL_ARCHETYPE"


PEDAGOGICAL_ARCHETYPE_TOKENS = {
    "hook", "mental_model", "demonstration", "guided_practice", "diagnostic_check",
    "concept_intro", "worked_example", "overview", "explanation", "independent_practice",
    "case_study", "discussion", "research_review", "real_world_application",
    "active_experiment", "peer_instruction", "deep_dive", "metacognition_summary"
}


class CanonicalConcept(BaseModel):
    canonical_id: str
    display_name: str
    domain: CanonicalDomain
    domain_family: str = "engineering"
    specialization: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    namespace: str = "core"
    version: str = "1.0"


# Canonical Knowledge Registry
SEED_CANONICAL_CONCEPTS: List[CanonicalConcept] = [
    CanonicalConcept(
        canonical_id="cs.algo.dp.overlapping_subproblems",
        display_name="DP Overlapping Subproblems",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="algorithms",
        aliases=[
            "overlapping subproblems", "repeated subproblems", "subproblem overlap",
            "overlapping subproblem property", "subproblem recurrence", "overlapping sub-problems",
            "overlapping sub problems", "subproblem reuse"
        ],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.algo.dp.memoization",
        display_name="Dynamic Programming Memoization",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="algorithms",
        aliases=["dp memoization", "memoization table", "top-down dp", "recursive memoization", "memoization technique", "memoization", "power of memoization", "from recursion to dp"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.algo.dp.top_down",
        display_name="Top-Down Dynamic Programming",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="algorithms",
        aliases=["top-down", "top down", "top down dp", "top-down dynamic programming", "recursive call tree pruning"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.algo.dp.optimal_substructure",
        display_name="DP Optimal Substructure",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="algorithms",
        aliases=["optimal substructure", "principle of optimality", "subproblem independence", "two pillars"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.algo.dp.state_definition",
        display_name="DP State Definition & Design",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="algorithms",
        aliases=["state definition", "state design", "state formulation", "state representation", "dp state"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.algo.dp.tabulation",
        display_name="Dynamic Programming Tabulation",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="algorithms",
        aliases=["dp tabulation", "bottom-up dp", "iterative dp", "tabulation technique", "tabulation", "bottom up approach"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.algo.dp.bottom_up",
        display_name="Bottom-Up Dynamic Programming",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="algorithms",
        aliases=["bottom up", "bottom-up", "iterative bottom up", "bottom up tabulation"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.algo.dp.recurrence",
        display_name="Recurrence Relations in DP",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="algorithms",
        aliases=["recurrence relations", "recurrence relation", "recurrence", "state transition equation", "bellman equation"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.algo.dp.two_dimensional",
        display_name="2D Dynamic Programming",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="algorithms",
        aliases=["2d dynamic programming", "2d dp", "multidimensional dp", "2d state table", "grid dp"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.algo.dp.grid",
        display_name="DP Grid & Matrix Traversal",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="algorithms",
        aliases=["grid state", "grid dp", "grids", "grid", "unique paths", "matrix traversal dp"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.algo.dp.knapsack",
        display_name="0/1 Knapsack & Subset State",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="algorithms",
        aliases=["knapsack", "0/1 knapsack", "knapsack problem", "subset sum", "target sum", "bounded knapsack"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.algo.dp.state_design",
        display_name="DP State Design & Invariants",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="algorithms",
        aliases=["state design", "state formulation", "state representation", "dp invariant"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.algo.dp.transition_errors",
        display_name="DP State Transition Mistakes",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="algorithms",
        aliases=["transition errors", "state-transition mistakes", "common pitfalls", "pitfalls", "state transition error", "off-by-one errors"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.algo.dp.complexity",
        display_name="DP Time & Space Complexity",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="algorithms",
        aliases=["time/space complexity comparison", "space optimization", "complexity", "time and space complexity", "o(1) space optimization"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.algo.dp.debugging",
        display_name="DP Debugging & Synthesis",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="algorithms",
        aliases=["debugging exercises", "debugging", "dp debugging", "troubleshooting dp", "synthesis & common pitfalls"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.algo.graph.bfs",
        display_name="Breadth-First Search",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="algorithms",
        aliases=["bfs", "breadth first search", "level order traversal"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.algo.graph.dfs",
        display_name="Depth-First Search",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="algorithms",
        aliases=["dfs", "depth first search"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="se.react.hooks",
        display_name="React Hooks & Lifecycle",
        domain=CanonicalDomain.SOFTWARE_ENGINEERING,
        domain_family="engineering",
        specialization="web_frameworks",
        aliases=["react hooks", "useeffect", "usestate", "custom hooks", "react state hooks", "hooks"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="ece.comm.massive_mimo",
        display_name="Massive MIMO Beamforming",
        domain=CanonicalDomain.ECE,
        domain_family="engineering",
        specialization="communications",
        aliases=["massive mimo", "multi-user mimo", "beamforming", "spatial multiplexing", "mimo beamforming"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="math.algebra.quadratic",
        display_name="Quadratic Equations & Roots",
        domain=CanonicalDomain.MATHEMATICS,
        domain_family="sciences",
        specialization="algebra",
        aliases=["quadratic equations", "quadratic formula", "roots of quadratic", "quadratic factoring", "solving quadratics"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="bio.botany.photosynthesis",
        display_name="Photosynthesis Light & Dark Reactions",
        domain=CanonicalDomain.BIOLOGY,
        domain_family="sciences",
        specialization="botany",
        aliases=["photosynthesis", "calvin cycle", "light reactions", "chloroplast function"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.ds.tree.bst.invariant",
        display_name="BST Invariant & Structural Properties",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="data_structures",
        aliases=["bst invariant", "binary search tree invariant", "bst property", "search tree property", "binary search tree"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.ds.tree.bst.search",
        display_name="BST Search & Lookup",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="data_structures",
        aliases=["bst search", "binary search tree search", "lookup in bst", "search bst", "cs.algo.bst.search"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.ds.tree.bst.insert",
        display_name="BST Insertion Algorithm",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="data_structures",
        aliases=["bst insert", "binary search tree insertion", "insert node into bst", "bst insertion", "inserting into bst"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.ds.tree.bst.delete",
        display_name="BST Node Deletion & Rebalancing",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="data_structures",
        aliases=["bst delete", "binary search tree deletion", "two child deletion", "delete from bst", "bst node removal"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.ds.tree.bst.traversal",
        display_name="BST Inorder & Sorted Traversal",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="data_structures",
        aliases=["inorder traversal", "bst inorder walk", "tree traversal", "bst traversal", "sorted traversal"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.python.oop.object",
        display_name="Python Objects & Instances",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="python_programming",
        aliases=["python object", "object", "objects", "instance", "object instantiation in python"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.python.oop.class",
        display_name="Python Classes & Blueprint",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="python_programming",
        aliases=["python class", "class", "classes", "class definition", "python classes and objects"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.python.oop.instantiation",
        display_name="Python Instantiation & Constructor",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="python_programming",
        aliases=["instantiation", "object creation", "instance initialization", "__init__", "constructor"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.python.oop.attributes",
        display_name="Python Instance & Class Attributes",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="python_programming",
        aliases=["instance attributes", "class attributes", "attributes", "instance variables"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.python.oop.methods",
        display_name="Python Instance Methods & Self",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="python_programming",
        aliases=["methods", "instance methods", "self parameter", "python methods"],
        namespace="core",
        version="1.0"
    ),
]


class CanonicalConceptResolver:
    """
    Resolves arbitrary concept phrases, stage titles, or aliases to authoritative canonical concepts.
    """

    _registry: Dict[str, CanonicalConcept] = {c.canonical_id: c for c in SEED_CANONICAL_CONCEPTS}
    _alias_index: Dict[str, str] = {}

    @classmethod
    def _build_alias_index(cls):
        if cls._alias_index:
            return
        for cid, concept in cls._registry.items():
            # Index canonical id itself
            cls._alias_index[cls._normalize(cid)] = cid
            cls._alias_index[cls._normalize(concept.display_name)] = cid
            for alias in concept.aliases:
                cls._alias_index[cls._normalize(alias)] = cid

    @classmethod
    def _normalize(cls, text: str) -> str:
        """Strips noise, punctuation, and extra whitespace for canonical comparison."""
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        return " ".join(cleaned.split())

    @classmethod
    def resolve(
        cls,
        concept_text: str,
        domain: Optional[CanonicalDomain] = None
    ) -> Optional[CanonicalConcept]:
        """
        Resolves a concept name or alias to a CanonicalConcept.
        """
        cls._build_alias_index()
        norm = cls._normalize(concept_text)
        
        # Direct alias/display match
        if norm in cls._alias_index:
            cid = cls._alias_index[norm]
            return cls._registry[cid]

        # Partial substring match against known aliases
        for alias_norm, cid in cls._alias_index.items():
            if len(alias_norm) > 4 and (alias_norm in norm or norm in alias_norm):
                candidate = cls._registry[cid]
                if domain is None or domain == CanonicalDomain.GENERAL_ACADEMIC or candidate.domain == domain:
                    return candidate

        return None

    @classmethod
    def resolve_or_create(
        cls,
        concept_name: str,
        domain: CanonicalDomain,
        domain_family: str = "engineering",
        specialization: Optional[str] = None,
        candidate_origin: Optional[str] = None
    ) -> CanonicalConcept:
        """
        Resolves to existing canonical concept or deterministically provisions a new
        namespaced canonical concept, preventing ad-hoc ephemeral IDs and collisions.
        Safeguards:
        1. Never creates concepts derived from pedagogical archetypes.
        2. No arbitrary truncation (collision-safe, stable identifiers).
        """
        if candidate_origin in (CandidateOrigin.PEDAGOGICAL_ARCHETYPE, "PEDAGOGICAL_ARCHETYPE"):
            logger.warning(f"[CanonicalConceptResolver] Rejected candidate concept '{concept_name}' with origin PEDAGOGICAL_ARCHETYPE")
            raise ValueError(f"Pedagogical archetype cannot be registered as canonical domain concept: {concept_name}")

        existing = cls.resolve(concept_name, domain)
        if existing:
            return existing

        # Deterministically build namespaced ID
        norm = cls._normalize(concept_name)
        # Protect against ephemeral stage-local IDs like 'stage_0_concept'
        clean_slug = re.sub(r"^stage_\d+_", "", norm)
        # COLLISION-SAFE: Never truncate canonical concept identifiers!
        clean_slug = clean_slug.replace(" ", "_")
        
        domain_prefix = {
            CanonicalDomain.COMPUTER_SCIENCE: "cs.algo",
            CanonicalDomain.SOFTWARE_ENGINEERING: "se.dev",
            CanonicalDomain.ECE: "ece.comm",
            CanonicalDomain.ELECTRICAL: "ee.power",
            CanonicalDomain.ELECTRONICS: "ec.circuits",
            CanonicalDomain.PHYSICS: "phys.core",
            CanonicalDomain.CHEMISTRY: "chem.core",
            CanonicalDomain.BIOLOGY: "bio.core",
            CanonicalDomain.MEDICINE: "med.core",
            CanonicalDomain.MATHEMATICS: "math.core",
            CanonicalDomain.ECONOMICS: "econ.core",
            CanonicalDomain.BUSINESS: "biz.core",
            CanonicalDomain.HUMANITIES: "hum.core",
            CanonicalDomain.LAW: "law.core",
            CanonicalDomain.SOCIAL_SCIENCES: "soc.core",
            CanonicalDomain.LANGUAGES: "lang.core",
            CanonicalDomain.GENERAL_ACADEMIC: "acad.core"
        }.get(domain, "gen.core")

        canonical_id = f"{domain_prefix}.{clean_slug}"
        new_concept = CanonicalConcept(
            canonical_id=canonical_id,
            display_name=concept_name.strip(),
            domain=domain,
            domain_family=domain_family,
            specialization=specialization,
            aliases=[concept_name.lower().strip()],
            namespace="dynamic",
            version="1.0"
        )
        cls._registry[canonical_id] = new_concept
        cls._alias_index[norm] = canonical_id
        return new_concept

    @classmethod
    def resolve_stage_semantics(
        cls,
        topic: str,
        knowledge_pack: Optional[Any] = None,
        objectives: Optional[List[Any]] = None,
        stage_title: Optional[str] = None,
        stage_focus: Optional[str] = None,
        prerequisite_graph: Optional[Any] = None,
        candidate_origin: Optional[str] = None,
        domain: Optional[CanonicalDomain] = None
    ) -> List[str]:
        """
        Resolves stage canonical domain concepts using the authoritative 6-tier priority order:
        1. Knowledge Pack concept graph
        2. Curriculum/objective concept references
        3. Explicit stage learning objectives
        4. Stage title/content focus
        5. Prerequisite/concept DAG
        6. Canonical registry aliases

        ARCHITECTURAL SAFEGUARDS:
        - WHAT IS TAUGHT -> canonical concept identity
        - HOW IT IS TAUGHT -> stage archetype / pedagogy
        - Pedagogical archetypes NEVER participate as canonical domain concepts.
        - Canonical concepts are resolved from SEMANTIC CONTENT, never stage index/position.
        """
        cls._build_alias_index()

        # Reject if origin is pedagogical archetype
        if candidate_origin in (CandidateOrigin.PEDAGOGICAL_ARCHETYPE, "PEDAGOGICAL_ARCHETYPE"):
            logger.warning("[CanonicalConceptResolver] Rejected candidate with origin PEDAGOGICAL_ARCHETYPE")
            return []

        # Extract normalized objective texts
        objectives_texts: List[str] = []
        if objectives:
            for obj in objectives:
                if isinstance(obj, str):
                    objectives_texts.append(obj)
                elif hasattr(obj, "description"):
                    objectives_texts.append(str(obj.description))
                elif hasattr(obj, "text"):
                    objectives_texts.append(str(obj.text))
                elif isinstance(obj, dict):
                    objectives_texts.append(str(obj.get("description", "") or obj.get("text", "")))

        title_clean = (stage_title or "").strip()
        focus_clean = (stage_focus or "").strip()
        topic_clean = (topic or "").strip()
        stage_content_combined = f"{title_clean} {focus_clean} {' '.join(objectives_texts)}".lower()
        topic_lower = topic_clean.lower()
        all_context = f"{topic_lower} {stage_content_combined}"

        # -------------------------------------------------------------------------
        # SPECIALIZED SEMANTIC RESOLUTION: DYNAMIC PROGRAMMING
        # Resolved by content semantics, NOT stage index!
        # Valid when duration changes, stages reordered, or stage count changes.
        # -------------------------------------------------------------------------
        is_dp = bool(re.search(r"\b(dp|dynamic[\s-]programming)\b", all_context, re.IGNORECASE))
        if is_dp:
            # 1. Hook / Motivation / Overlapping Subproblems / Memoization
            if any(k in stage_content_combined for k in [
                "overlapping subproblem", "repeated subproblem", "subproblem overlap", "subproblem recurrence",
                "memoization", "top-down", "top down", "recursive memoization", "from recursion to dp",
                "power of memoization", "overlapping sub-problems", "overlapping", "call stack explosion",
                "overlapping sub problems"
            ]):
                return ["cs.algo.dp.overlapping_subproblems", "cs.algo.dp.memoization"]

            # 2. Optimal Substructure / State Definition
            if any(k in stage_content_combined for k in [
                "optimal substructure", "substructure", "state definition", "state formulation",
                "state representation", "principle of optimality", "two pillars", "subproblem independence"
            ]):
                return ["cs.algo.dp.optimal_substructure", "cs.algo.dp.state_definition"]

            # 3. Tabulation / Bottom-Up / Recurrence
            if any(k in stage_content_combined for k in [
                "tabulation", "bottom-up", "bottom up", "recurrence relation", "recurrence relations",
                "state transition equation", "bellman equation", "iterative dp", "iterative table"
            ]):
                return ["cs.algo.dp.tabulation", "cs.algo.dp.bottom_up", "cs.algo.dp.recurrence"]

            # 4. 2D DP / Grid / Knapsack
            if any(k in stage_content_combined for k in [
                "2d", "knapsack", "grid", "unique paths", "subset sum", "target sum",
                "two dimensional", "matrix traversal", "multidimensional", "0/1 knapsack"
            ]):
                return ["cs.algo.dp.two_dimensional", "cs.algo.dp.grid", "cs.algo.dp.knapsack"]

            # 5. Diagnostic / Synthesis / State Design / Pitfalls / Complexity / Debugging
            if any(k in stage_content_combined for k in [
                "synthesis", "pitfall", "pitfalls", "mistake", "debugging", "complexity",
                "space optimization", "transition error", "state design", "state invariant",
                "off-by-one", "troubleshooting", "diagnostic", "formative diagnostic"
            ]):
                return ["cs.algo.dp.state_design", "cs.algo.dp.transition_errors", "cs.algo.dp.complexity", "cs.algo.dp.debugging"]

            # Fallback for DP: default foundational pair
            return ["cs.algo.dp.overlapping_subproblems", "cs.algo.dp.memoization"]

        # -------------------------------------------------------------------------
        # TIER 1: Knowledge Pack concept graph
        # -------------------------------------------------------------------------
        if knowledge_pack and hasattr(knowledge_pack, "concepts") and knowledge_pack.concepts:
            for c in knowledge_pack.concepts:
                c_title = c.get("title", "") if isinstance(c, dict) else getattr(c, "title", "")
                if c_title and cls._normalize(c_title) in cls._normalize(stage_content_combined):
                    resolved = cls.resolve(c_title, domain)
                    if resolved:
                        return [resolved.canonical_id]

        # -------------------------------------------------------------------------
        # TIER 2 & 3: Curriculum / Explicit stage learning objectives
        # -------------------------------------------------------------------------
        for otext in objectives_texts:
            norm_otext = cls._normalize(otext)
            for alias_norm, cid in cls._alias_index.items():
                if len(alias_norm) > 4 and alias_norm in norm_otext:
                    return [cid]

        # -------------------------------------------------------------------------
        # TIER 4: Stage title / content focus
        # -------------------------------------------------------------------------
        for candidate_text in [focus_clean, title_clean]:
            if candidate_text:
                resolved = cls.resolve(candidate_text, domain)
                if resolved:
                    return [resolved.canonical_id]

        # -------------------------------------------------------------------------
        # TIER 5: Prerequisite / concept DAG
        # -------------------------------------------------------------------------
        if prerequisite_graph:
            if isinstance(prerequisite_graph, list):
                for edge in prerequisite_graph:
                    target = edge.get("target") if isinstance(edge, dict) else getattr(edge, "target", None)
                    if target and target in cls._registry:
                        return [target]

        # -------------------------------------------------------------------------
        # TIER 6: Canonical registry aliases matching overall context
        # -------------------------------------------------------------------------
        for alias_norm, cid in cls._alias_index.items():
            if len(alias_norm) > 4 and alias_norm in cls._normalize(all_context):
                candidate = cls._registry[cid]
                if domain is None or domain == CanonicalDomain.GENERAL_ACADEMIC or candidate.domain == domain:
                    return [cid]

        # -------------------------------------------------------------------------
        # CONTROLLED DOMAIN-CONCEPT FALLBACK (FOR GENUINELY UNKNOWN TOPICS)
        # Never fabricate from archetype!
        # -------------------------------------------------------------------------
        if domain and topic_clean:
            # Create registry concept based solely on topic domain semantics
            try:
                new_c = cls.resolve_or_create(
                    concept_name=topic_clean,
                    domain=domain,
                    candidate_origin=CandidateOrigin.STAGE_CONTENT_FOCUS
                )
                return [new_c.canonical_id]
            except Exception as e:
                logger.warning(f"[CanonicalConceptResolver] Dynamic concept creation fallback failed: {e}")

        return ["UNRESOLVED_CANONICAL_CONCEPT"]

    @classmethod
    def resolve_stage_concepts(
        cls,
        topic: str,
        stage_title: str,
        stage_description: str = "",
        stage_objectives: Optional[List[str]] = None,
        stage_concept_id: Optional[str] = None
    ) -> List[str]:
        """
        Resolves stable, canonical concept identities for a stage before resource retrieval.
        Never persists or returns generic IDs like concept_2, concept_3, concept_4.
        """
        # If stage_concept_id is an explicit canonical ID already, return it
        if stage_concept_id and not re.match(r"^(concept_\d+|stage_\d+.*|c_default|unresolved_canonical_concept)$", stage_concept_id, re.IGNORECASE):
            resolved = cls.resolve(stage_concept_id)
            if resolved:
                return [resolved.canonical_id]
            if "." in stage_concept_id:
                return [stage_concept_id]

        return cls.resolve_stage_semantics(
            topic=topic,
            stage_title=stage_title,
            stage_focus=stage_description,
            objectives=stage_objectives
        )

