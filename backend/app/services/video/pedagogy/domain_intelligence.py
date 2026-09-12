"""
Domain Intelligence Engine
==========================
Dynamically analyzes arbitrary topic prompts to classify:
1. DomainCategory (Computer Science, Mathematics, Physics, Biology, History, Business, etc.)
2. Sub-discipline and domain characteristics
3. Recommended pedagogy mode & primary visual archetype affinities
4. Always falls back gracefully to GENERIC_EDUCATIONAL if unconfident.
"""
from typing import Dict, Any, Tuple, List
import re
from ..schemas import DomainCategory, VisualStrategyArchetype

# Domain keyword associations for rapid deterministic matching & fallback
DOMAIN_KEYWORD_PATTERNS: Dict[DomainCategory, List[str]] = {
    DomainCategory.COMPUTER_SCIENCE: [
        "linked list", "data structure", "algorithm", "binary tree", "binary search tree", "bst", "graph", "sorting", "stack", "queue",
        "hash table", "recursion", "dynamic programming", "dinamic programing", "knapsack", "knapsac", "operating system", "cpu scheduling", "deadlock",
        "memory management", "dbms", "database", "normalization", "sql", "join", "transaction", "compiler",
        "networking", "tcp", "udp", "ip address", "http", "api", "python", "java", "c++", "object oriented",
        "machine learning", "neural network", "transformer", "git", "docker", "cloud", "concurrency"
    ],
    DomainCategory.MATHEMATICS: [
        "calculus", "derivative", "integration", "integral", "limit", "differential equation", "algebra",
        "matrix", "matrices", "determinant", "eigenvalue", "vector", "probability", "statistics", "bayes",
        "distribution", "trigonometry", "geometry", "linear algebra", "discrete math", "complex numbers",
        "polynomial", "quadratic", "arithmetic", "fourier", "laplace", "series"
    ],
    DomainCategory.PHYSICS: [
        "newton", "mechanics", "force", "acceleration", "gravity", "thermodynamics", "entropy", "optics",
        "electromagnetism", "maxwell", "quantum", "quantum tunneling", "relativity", "wave", "frequency", "doppler", "kinetic energy",
        "potential energy", "friction", "projectile", "momentum", "torque", "electric field", "magnetic field",
        "bernoulli", "physics", "kinematics"
    ],
    DomainCategory.CHEMISTRY: [
        "chemical bonding", "covalent", "ionic", "periodic table", "atomic structure", "orbital", "stoichiometry",
        "thermodynamics", "equilibrium", "acid", "base", "ph scale", "organic chemistry", "reaction mechanism",
        "electrochemistry", "redox", "catalyst", "polymer", "solubility", "titration", "sn1", "sn2", "electronegativity"
    ],
    DomainCategory.BIOLOGY: [
        "photosynthesis", "fotosintesis", "cellular respiration", "dna", "rna", "genetics", "mitosis", "meiosis", "human heart",
        "circulatory", "nervous system", "neuron", "synapse", "evolution", "natural selection", "ecology",
        "ecosystem", "cell biology", "organelle", "mitochondria", "enzyme", "atp", "immune system", "virus", "bacteria", "replication fork"
    ],
    DomainCategory.HISTORY: [
        "french revolution", "world war", "industrial revolution", "cold war", "american revolution", "mughal",
        "renaissance", "colonialism", "civil war", "ancient", "medieval", "treaty", "monarchy", "bastille",
        "empire", "independence movement", "treaty of versailles", "1857", "revolt", "mutiny", "sepoy"
    ],
    DomainCategory.GEOGRAPHY: [
        "tectonic plates", "plate tectonics", "continental drift", "earthquake", "volcano", "climate zones", "monsoon", "ocean currents", "atmosphere",
        "glaciers", "topography", "river system", "erosion", "geomorphology", "cartography", "latitudes", "geography"
    ],
    DomainCategory.ECONOMICS: [
        "supply and demand", "inflation", "gdp", "fiscal policy", "monetary policy", "macroeconomics",
        "microeconomics", "market equilibrium", "elasticity", "opportunity cost", "central bank", "recession",
        "interest rate", "unemployment", "trade balance", "rbi"
    ],
    DomainCategory.BUSINESS: [
        "marketing funnel", "tofu", "mofu", "bofu", "swot analysis", "business model", "accounting", "balance sheet", "income statement",
        "cash flow", "profit loss", "supply chain", "corporate finance", "valuation", "brand strategy", "customer journey",
        "unit economics", "cac", "ltv"
    ],
    DomainCategory.ENGINEERING: [
        "electrical circuit", "ohms law", "kirchhoff", "transistor", "semiconductor", "thermodynamics cycle",
        "fluid mechanics", "stress strain", "finite element", "signals and systems", "control systems", "cad",
        "engine", "ic engine", "four stroke", "two stroke", "digital electronics", "finite state machine"
    ],
    DomainCategory.LANGUAGE: [
        "grammar", "tenses", "parts of speech", "syntax", "phonetics", "active passive", "direct indirect",
        "vocabulary", "idioms", "reading comprehension", "essay structure", "punctuation"
    ],
    DomainCategory.SOCIAL_SCIENCE: [
        "indian constitution", "preamble", "fundamental rights", "parliament", "democracy", "judiciary",
        "sociology", "political science", "federalism", "human rights", "caste system", "globalization"
    ]
}


class DomainIntelligenceEngine:
    """Classifies topic and prompt into domain and pedagogical traits."""

    @staticmethod
    def detect_domain(topic: str, context: str = "") -> Tuple[DomainCategory, float]:
        """Returns (DomainCategory, confidence 0.0-1.0)."""
        combined = f"{topic.lower()} {context.lower()}".strip()

        best_domain = DomainCategory.GENERAL_KNOWLEDGE
        best_score = 0.0

        for domain, keywords in DOMAIN_KEYWORD_PATTERNS.items():
            matches = 0
            for kw in keywords:
                # Word boundary match preferred
                if re.search(r'\b' + re.escape(kw) + r'\b', combined):
                    matches += 2
                elif kw in combined:
                    matches += 1

            if matches > 0:
                score = min(0.95, 0.4 + (matches * 0.15))
                if score > best_score:
                    best_score = score
                    best_domain = domain

        if best_score == 0.0:
            return DomainCategory.GENERAL_KNOWLEDGE, 0.50

        return best_domain, best_score

    @staticmethod
    def get_domain_archetype_affinities(domain: DomainCategory) -> List[VisualStrategyArchetype]:
        """Returns ordered list of visual archetypes that work best for this domain."""
        affinities: Dict[DomainCategory, List[VisualStrategyArchetype]] = {
            DomainCategory.COMPUTER_SCIENCE: [
                VisualStrategyArchetype.DATA_STRUCTURE,
                VisualStrategyArchetype.ALGORITHM_TRACE,
                VisualStrategyArchetype.PROCESS_FLOW,
                VisualStrategyArchetype.CODE_EXECUTION,
                VisualStrategyArchetype.COMPARISON,
                VisualStrategyArchetype.SYSTEM_ARCHITECTURE
            ],
            DomainCategory.MATHEMATICS: [
                VisualStrategyArchetype.MATHEMATICAL_DERIVATION,
                VisualStrategyArchetype.GRAPH_PLOT,
                VisualStrategyArchetype.FORMULA_VISUALIZATION,
                VisualStrategyArchetype.STEP_SEQUENCE,
                VisualStrategyArchetype.CONCEPT_MAP
            ],
            DomainCategory.PHYSICS: [
                VisualStrategyArchetype.GRAPH_PLOT,
                VisualStrategyArchetype.FORMULA_VISUALIZATION,
                VisualStrategyArchetype.CAUSE_EFFECT,
                VisualStrategyArchetype.SCIENTIFIC_PROCESS,
                VisualStrategyArchetype.REAL_WORLD_EXAMPLE
            ],
            DomainCategory.CHEMISTRY: [
                VisualStrategyArchetype.SCIENTIFIC_PROCESS,
                VisualStrategyArchetype.CONCEPT_MAP,
                VisualStrategyArchetype.TABLE,
                VisualStrategyArchetype.STEP_SEQUENCE,
                VisualStrategyArchetype.COMPARISON
            ],
            DomainCategory.BIOLOGY: [
                VisualStrategyArchetype.SCIENTIFIC_PROCESS,
                VisualStrategyArchetype.PROCESS_FLOW,
                VisualStrategyArchetype.HIERARCHY,
                VisualStrategyArchetype.CONCEPT_MAP,
                VisualStrategyArchetype.ANATOMICAL_DIAGRAM,
                VisualStrategyArchetype.COMPARISON
            ],
            DomainCategory.HISTORY: [
                VisualStrategyArchetype.TIMELINE,
                VisualStrategyArchetype.CAUSE_EFFECT,
                VisualStrategyArchetype.CONCEPT_MAP,
                VisualStrategyArchetype.COMPARISON,
                VisualStrategyArchetype.MAP
            ],
            DomainCategory.GEOGRAPHY: [
                VisualStrategyArchetype.MAP,
                VisualStrategyArchetype.PROCESS_FLOW,
                VisualStrategyArchetype.CAUSE_EFFECT,
                VisualStrategyArchetype.HIERARCHY
            ],
            DomainCategory.ECONOMICS: [
                VisualStrategyArchetype.GRAPH_PLOT,
                VisualStrategyArchetype.CAUSE_EFFECT,
                VisualStrategyArchetype.TABLE,
                VisualStrategyArchetype.COMPARISON,
                VisualStrategyArchetype.CONCEPT_MAP
            ],
            DomainCategory.BUSINESS: [
                VisualStrategyArchetype.CHART,
                VisualStrategyArchetype.PROCESS_FLOW,
                VisualStrategyArchetype.TABLE,
                VisualStrategyArchetype.COMPARISON,
                VisualStrategyArchetype.HIERARCHY
            ],
            DomainCategory.ENGINEERING: [
                VisualStrategyArchetype.SYSTEM_ARCHITECTURE,
                VisualStrategyArchetype.PROCESS_FLOW,
                VisualStrategyArchetype.GRAPH_PLOT,
                VisualStrategyArchetype.MATHEMATICAL_DERIVATION
            ],
            DomainCategory.LANGUAGE: [
                VisualStrategyArchetype.TABLE,
                VisualStrategyArchetype.COMPARISON,
                VisualStrategyArchetype.STEP_SEQUENCE,
                VisualStrategyArchetype.TEXTUAL_EXPLAINER
            ],
            DomainCategory.SOCIAL_SCIENCE: [
                VisualStrategyArchetype.HIERARCHY,
                VisualStrategyArchetype.CONCEPT_MAP,
                VisualStrategyArchetype.TIMELINE,
                VisualStrategyArchetype.COMPARISON
            ]
        }
        return affinities.get(domain, [
            VisualStrategyArchetype.CONCEPT_MAP,
            VisualStrategyArchetype.PROCESS_FLOW,
            VisualStrategyArchetype.COMPARISON,
            VisualStrategyArchetype.STEP_SEQUENCE,
            VisualStrategyArchetype.GENERIC_DIAGRAM
        ])
