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
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from ..schemas import CanonicalDomain


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
        specialization: Optional[str] = None
    ) -> CanonicalConcept:
        """
        Resolves to existing canonical concept or deterministically provisions a new
        namespaced canonical concept, preventing ad-hoc ephemeral IDs.
        """
        existing = cls.resolve(concept_name, domain)
        if existing:
            return existing

        # Deterministically build namespaced ID
        norm = cls._normalize(concept_name)
        # Protect against ephemeral stage-local IDs like 'stage_0_concept'
        clean_slug = re.sub(r"^stage_\d+_", "", norm)
        clean_slug = clean_slug.replace(" ", "_")[:32]
        
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
        cls._build_alias_index()
        objectives_text = " ".join(stage_objectives or [])
        combined = f"{stage_title} {stage_description} {objectives_text}".lower()
        topic_lower = topic.lower()

        # Dynamic Programming Stage Detection
        is_dp = bool(re.search(r"\b(dp|dynamic[\s-]programming)\b", f"{topic_lower} {combined}", re.IGNORECASE))
        if is_dp:
            # 1. 2D DP / Knapsack
            if any(k in combined for k in ["2d", "knapsack", "grid", "unique paths", "subset sum", "target sum", "two dimensional"]):
                return ["cs.algo.dp.two_dimensional", "cs.algo.dp.grid", "cs.algo.dp.knapsack"]

            # 2. Synthesis & Pitfalls / Debugging
            if any(k in combined for k in ["synthesis", "pitfall", "pitfalls", "mistake", "debugging", "complexity", "space optimization", "transition error"]):
                return ["cs.algo.dp.state_design", "cs.algo.dp.transition_errors", "cs.algo.dp.complexity", "cs.algo.dp.debugging"]

            # 3. Tabulation / Bottom-Up
            if any(k in combined for k in ["tabulation", "bottom-up", "bottom up", "recurrence relation", "recurrence"]):
                return ["cs.algo.dp.tabulation", "cs.algo.dp.bottom_up", "cs.algo.dp.recurrence"]

            # 4. Optimal Substructure / State Definition
            if any(k in combined for k in ["optimal substructure", "substructure", "state definition", "two pillars"]):
                return ["cs.algo.dp.optimal_substructure", "cs.algo.dp.state_definition"]

            # 5. Memoization / Top-Down
            if any(k in combined for k in ["memoization", "top-down", "top down", "from recursion to dp", "power of memoization"]):
                return ["cs.algo.dp.memoization", "cs.algo.dp.top_down"]

        # Check if stage_concept_id is an explicit canonical ID already
        if stage_concept_id and not re.match(r"^(concept_\d+|stage_\d+.*|c_default)$", stage_concept_id, re.IGNORECASE):
            resolved = cls.resolve(stage_concept_id)
            if resolved:
                return [resolved.canonical_id]

        # Check stage title against alias index
        resolved_title = cls.resolve(stage_title)
        if resolved_title:
            return [resolved_title.canonical_id]

        # Fallback: if unresolvable, do NOT pretend generic concept_N is canonical
        return ["UNRESOLVED_CANONICAL_CONCEPT"]

