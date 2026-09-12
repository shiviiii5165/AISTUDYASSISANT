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
        aliases=["dp memoization", "memoization table", "top-down dp", "recursive memoization", "memoization technique", "memoization"],
        namespace="core",
        version="1.0"
    ),
    CanonicalConcept(
        canonical_id="cs.algo.dp.tabulation",
        display_name="Dynamic Programming Tabulation",
        domain=CanonicalDomain.COMPUTER_SCIENCE,
        domain_family="engineering",
        specialization="algorithms",
        aliases=["dp tabulation", "bottom-up dp", "iterative dp", "tabulation technique", "tabulation"],
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
