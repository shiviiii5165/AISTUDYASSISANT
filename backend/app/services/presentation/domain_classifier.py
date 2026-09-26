"""
LearnByGenie vNEXT — Domain & Purpose Classifier
================================================
Multi-signal classification using topic + audience + context + ontology evidence.

Resolution policy (spec §13):
  high-confidence deterministic rule → no LLM call
  ambiguous / low-confidence case   → context-based disambiguation
  unresolvable ambiguity             → lightweight model classifier (classify_domain_with_model_fallback)

Returns domain, subdomain, confidence, classification_basis for full provenance.
"""
from app.core.logging import logger
import re
from typing import Optional, Dict, List, Any, Tuple
from .schemas import (
    DomainClassification,
    PresentationGoal,
    PresentationMode,
    ContentDensity,
    StoryGrammarType,
    TemplateSelectionSource,
)


# ═══════════════════════════════════════════════════════════════
# CLASSIFICATION BASIS VALUES
# ═══════════════════════════════════════════════════════════════
# Canonical values for classification_basis (spec §2):
#   DETERMINISTIC_RULE       — high-confidence single-domain keyword match
#   CONTEXT_DISAMBIGUATION   — ambiguous keywords resolved by custom_context / ontology
#   MODEL_DISAMBIGUATION     — resolved by lightweight LLM classifier (Phase 2)
#   DEFAULT_FALLBACK         — no signal matched, returned "general"

CLASSIFICATION_BASIS_DETERMINISTIC = "DETERMINISTIC_RULE"
CLASSIFICATION_BASIS_CONTEXT = "CONTEXT_DISAMBIGUATION"
CLASSIFICATION_BASIS_MODEL = "MODEL_DISAMBIGUATION"
CLASSIFICATION_BASIS_DEFAULT = "DEFAULT_FALLBACK"


# ═══════════════════════════════════════════════════════════════
# DOMAIN KEYWORD RULES — ordered by specificity
# 18 first-class domains covering any-topic presentation generation
# ═══════════════════════════════════════════════════════════════

DOMAIN_RULES: Dict[str, Dict[str, Any]] = {
    "computer_science": {
        "keywords": [
            "algorithm", "data structure", "programming", "software", "database",
            "compiler", "operating system", "node.js", "node js", "nodejs",
            "python language", "java ",
            "react", "api", "cpu", "memory management", "cache", "thread",
            "socket", "http", "tcp", "udp", "encryption", "kubernetes", "docker",
            "cloud computing", "devops", "git", "microservice", "rest api",
            "graphql", "sql", "nosql", "mongodb", "redis", "big data", "hadoop",
            "spark", "kafka", "blockchain", "cryptography", "cybersecurity",
            "web development", "frontend", "backend", "full stack",
            "oop", "functional programming", "recursion", "binary tree",
            "hash table", "linked list", "sorting algorithm",
            "machine learning", "deep learning", "neural network",
            "artificial intelligence", "nlp", "computer vision",
            "reinforcement learning", "gpt", "bert", "llm", "ml",
            "convolutional", "recurrent neural", "attention mechanism",
            "backpropagation", "gradient descent",
            "software architecture", "system architecture", "event loop",
            "asynchronous", "non-blocking", "middleware", "runtime",
        ],
        "subdomains": {
            "systems": ["operating system", "kernel", "process scheduling",
                        "memory management", "cpu scheduling", "file system",
                        "virtual memory", "deadlock"],
            "networking": ["network", "tcp", "http", "socket", "dns", "routing",
                          "protocol", "node.js", "express", "websocket", "udp",
                          "osi model", "ip address"],
            "databases": ["database", "sql", "nosql", "mongodb", "redis",
                         "indexing", "query", "normalization", "acid",
                         "transaction", "postgresql"],
            "ai_ml": ["machine learning", "deep learning", "neural network",
                     "artificial intelligence", "nlp", "computer vision",
                     "reinforcement learning", "gpt", "bert", "llm", "ml",
                     "convolutional", "attention mechanism", "transformer model",
                     "backpropagation", "gradient descent"],
            "web_development": ["web development", "frontend", "backend",
                               "react", "javascript", "html", "css", "vue",
                               "angular", "next.js", "django", "flask"],
            "devops_cloud": ["kubernetes", "docker", "ci/cd", "devops",
                            "cloud computing", "aws", "azure", "gcp",
                            "terraform", "microservice"],
            "algorithms": ["algorithm", "data structure", "sorting", "graph algorithm",
                          "dynamic programming", "complexity", "binary search",
                          "recursion", "greedy", "divide and conquer"],
            "security": ["security", "encryption", "cryptography", "cybersecurity",
                        "authentication", "authorization", "firewall", "ssl", "tls"],
        },
    },
    "mathematics": {
        "keywords": [
            "theorem", "proof", "equation", "calculus", "algebra", "geometry",
            "topology", "eigenvalue", "eigenvector", "matrix", "vector space",
            "linear algebra", "differential equation", "integral", "probability",
            "statistics", "number theory", "group theory", "fourier",
            "laplace transform", "taylor series", "complex analysis",
            "real analysis", "combinatorics", "graph theory", "optimization",
            "numerical methods", "trigonometry", "logarithm", "polynomial",
            "derivative", "gradient", "hessian", "stochastic",
            "mathematical induction", "set theory", "boolean algebra",
        ],
        "subdomains": {
            "linear_algebra": ["eigenvalue", "eigenvector", "matrix", "vector space",
                              "linear algebra", "determinant", "linear transformation",
                              "orthogonal", "diagonalization"],
            "calculus": ["calculus", "differential", "integral", "derivative",
                        "limit", "continuity", "taylor series", "partial derivative"],
            "probability_statistics": ["probability", "statistics", "bayesian",
                                      "distribution", "hypothesis", "regression",
                                      "variance", "standard deviation", "stochastic"],
            "discrete": ["combinatorics", "graph theory", "number theory",
                        "discrete mathematics", "boolean algebra", "recurrence"],
            "analysis": ["real analysis", "complex analysis", "topology",
                        "measure theory", "functional analysis"],
        },
    },
    "physics": {
        "keywords": [
            "mechanics", "thermodynamics", "electromagnetism", "quantum",
            "relativity", "optics", "wave", "particle", "newton",
            "maxwell", "schrodinger", "velocity", "acceleration", "force",
            "energy", "momentum", "entropy", "electromagnetic", "photon",
            "electron", "proton", "neutron", "nuclear", "gravity",
            "magnetic field", "electric field", "circuit", "resistance",
            "capacitance", "inductance", "semiconductor", "diode",
            "astronomy", "astrophysics", "orbit", "planetary", "planet",
            "galaxy", "cosmology", "celestial", "solar system",
        ],
        "subdomains": {
            "mechanics": ["mechanics", "newton", "force", "velocity",
                         "acceleration", "momentum", "torque", "friction"],
            "electromagnetism": ["electromagnetism", "maxwell", "electromagnetic",
                                "magnetic field", "electric field", "faraday",
                                "coulomb", "gauss"],
            "quantum": ["quantum", "schrodinger", "wave function", "photon",
                       "superposition", "entanglement", "uncertainty principle"],
            "thermodynamics": ["thermodynamics", "entropy", "heat", "temperature",
                              "carnot", "boltzmann"],
            "optics": ["optics", "lens", "refraction", "diffraction", "laser",
                      "polarization", "interference"],
            "astronomy_astrophysics": ["astronomy", "astrophysics", "orbit", "planetary",
                                       "planet", "solar system", "celestial", "galaxy", "cosmology"],
        },
    },
    "chemistry": {
        "keywords": [
            "molecule", "atom", "chemical bond", "chemical reaction", "organic chemistry",
            "inorganic", "periodic table", "oxidation", "reduction",
            "acid", "base", "ph level", "ph scale", "catalyst", "polymer", "isomer",
            "stoichiometry", "molarity", "chemical equilibrium", "electrochemistry",
            "spectroscopy", "chromatography", "nucleophilic", "electrophilic",
            "sn1", "sn2", "functional group", "aromatic", "alkene", "alkane",
            "molar mass", "titration", "covalent bond", "ionic bond", "covalent", "ionic",
        ],
        "subdomains": {
            "organic": ["organic chemistry", "functional group", "isomer",
                       "sn1", "sn2", "nucleophilic", "electrophilic",
                       "aromatic", "alkene", "polymer", "stereochemistry"],
            "inorganic": ["inorganic", "coordination compound", "crystal field",
                         "ligand", "transition metal"],
            "physical": ["thermochemistry", "kinetics", "equilibrium",
                        "electrochemistry", "quantum chemistry"],
            "analytical": ["spectroscopy", "chromatography", "titration",
                          "mass spectrometry"],
        },
    },
    "biology": {
        "keywords": [
            "cell", "dna", "rna", "protein", "gene", "evolution",
            "ecology", "photosynthesis", "mitosis", "meiosis", "enzyme",
            "metabolism", "respiration", "organelle", "chromosome",
            "mutation", "natural selection", "ecosystem", "biodiversity",
            "taxonomy", "anatomy", "physiology", "neuroscience",
            "microbiology", "genetics", "genomics", "bioinformatics",
            "immunology", "pathogen", "vaccine", "antibiotic",
            "chloroplast", "mitochondria", "ribosome",
            "plant biology", "cellular respiration", "krebs cycle",
            "calvin cycle", "atp", "nadph", "light reaction",
        ],
        "subdomains": {
            "molecular": ["dna", "rna", "protein", "gene", "genome",
                         "transcription", "translation", "replication",
                         "molecular biology", "bioinformatics"],
            "cell_biology": ["cell", "organelle", "mitosis", "meiosis",
                            "membrane", "cytoplasm", "nucleus"],
            "ecology": ["ecology", "ecosystem", "biodiversity", "population",
                       "food chain", "habitat", "conservation"],
            "evolution": ["evolution", "natural selection", "speciation",
                         "phylogenetics", "adaptation", "darwin"],
            "physiology": ["photosynthesis", "respiration", "metabolism",
                          "digestion", "circulation", "nervous system"],
        },
    },
    "medicine_health_sciences": {
        "keywords": [
            "disease", "diagnosis", "treatment", "patient", "clinical",
            "pathology", "pharmacology", "surgery", "epidemiology",
            "symptom", "therapy", "prognosis", "cancer", "diabetes",
            "cardiovascular", "infectious disease", "mental health",
            "public health", "healthcare", "nursing", "hypertension",
            "pathophysiology", "drug", "dosage", "prescription",
            "anatomy", "organ", "tissue", "blood pressure",
            "cholesterol", "cardiac", "pulmonary", "renal",
            "oncology", "radiology", "dermatology", "neurology",
            "psychiatry", "pediatrics", "geriatrics", "immunotherapy",
            "vaccine", "antibiotic resistance", "pandemic", "epidemic",
            "bioethics", "clinical trial", "evidence-based medicine",
            "toxicology", "toxicity", "poison", "toxin", "exposure",
        ],
        "subdomains": {
            "clinical_medicine": ["diagnosis", "treatment", "patient", "clinical",
                                 "prognosis", "therapy", "prescription", "dosage"],
            "pathology": ["pathology", "pathophysiology", "disease", "symptom",
                         "histology", "biopsy"],
            "pharmacology": ["pharmacology", "drug", "dosage", "pharmacokinetics",
                            "adverse effect", "drug interaction"],
            "public_health": ["public health", "epidemiology", "pandemic",
                             "epidemic", "health policy", "sanitation",
                             "disease prevention"],
            "specialties": ["oncology", "cardiology", "neurology", "psychiatry",
                           "pediatrics", "dermatology", "radiology",
                           "orthopedics", "ophthalmology"],
            "toxicology": ["toxicology", "toxicity", "poison", "toxin", "exposure",
                          "overdose", "heavy metal"],
        },
    },
    "engineering": {
        "keywords": [
            "circuit", "signal processing", "control system", "mimo",
            "antenna", "modulation", "bandwidth", "frequency", "filter",
            "amplifier", "transistor", "vlsi", "fpga", "embedded system",
            "robotics", "mechatronics", "cad", "finite element",
            "structural engineering", "fluid dynamics", "heat transfer",
            "materials science", "composite", "alloy",
            "5g", "lte", "ofdm", "beamforming", "massive mimo",
            "wireless communication", "radar", "digital signal",
            "transformer", "voltage", "step-up", "step-down",
            "power supply", "rectifier", "inverter",
            "electrical engineering", "mechanical engineering",
            "civil engineering", "chemical engineering",
        ],
        "subdomains": {
            "electrical": ["circuit", "transistor", "semiconductor", "vlsi",
                          "power electronics", "amplifier", "transformer",
                          "voltage", "step-up", "step-down", "rectifier",
                          "inverter", "power supply",
                          "electrical engineering"],
            "communications": ["signal processing", "mimo", "antenna",
                              "modulation", "bandwidth", "5g", "lte",
                              "ofdm", "beamforming", "wireless", "radar"],
            "control": ["control system", "pid", "feedback", "transfer function",
                       "stability", "state space"],
            "mechanical": ["fluid dynamics", "heat transfer", "thermodynamics",
                          "finite element", "structural", "cad"],
        },
    },
    "business": {
        "keywords": [
            "marketing", "management", "strategy", "entrepreneurship",
            "startup", "venture capital", "roi",
            "supply chain", "logistics", "operations", "leadership",
            "negotiation", "branding", "market research", "swot",
            "porter", "bcg matrix", "balanced scorecard",
            "competitive advantage", "value proposition",
            "business model", "lean startup", "agile management",
            "corporate strategy", "merger", "acquisition",
        ],
        "subdomains": {
            "marketing": ["marketing", "branding", "advertising", "consumer behavior",
                         "digital marketing", "seo", "social media marketing"],
            "management": ["management", "leadership", "organizational behavior",
                          "human resources", "project management", "agile"],
            "strategy": ["strategy", "competitive advantage", "swot",
                        "porter", "innovation", "disruption"],
            "entrepreneurship": ["startup", "venture capital", "entrepreneurship",
                                "lean startup", "business model"],
        },
    },
    "economics": {
        "keywords": [
            "gdp", "inflation", "monetary policy", "fiscal policy",
            "supply and demand", "market equilibrium", "macroeconomics",
            "microeconomics", "trade", "tariff", "exchange rate",
            "interest rate", "central bank", "federal reserve",
            "keynesian", "monetarism", "game theory", "oligopoly",
            "monopoly", "externality", "public goods",
        ],
        "subdomains": {
            "macro": ["gdp", "inflation", "monetary policy", "fiscal policy",
                     "unemployment", "economic growth", "central bank"],
            "micro": ["supply and demand", "market equilibrium", "elasticity",
                     "consumer surplus", "producer surplus", "marginal"],
            "international": ["trade", "tariff", "exchange rate", "balance of payments",
                            "comparative advantage", "globalization"],
        },
    },
    "history": {
        "keywords": [
            "revolution", "war", "empire", "dynasty", "colonialism",
            "independence", "civil rights", "renaissance", "reformation",
            "industrial revolution", "cold war", "world war",
            "ancient", "medieval", "modern history", "civilization",
            "archaeology", "primary source", "historiography",
        ],
        "subdomains": {
            "ancient": ["ancient", "greek", "roman", "egyptian", "mesopotamia",
                       "bronze age", "iron age"],
            "medieval": ["medieval", "feudal", "crusade", "viking",
                        "byzantine", "ottoman"],
            "modern": ["industrial revolution", "world war", "cold war",
                      "colonialism", "independence", "civil rights",
                      "french revolution", "american revolution"],
        },
    },
    "literature_humanities": {
        "keywords": [
            "novel", "poem", "playwright", "shakespeare", "literary analysis",
            "narrative", "metaphor", "symbolism", "protagonist", "antagonist",
            "tragedy", "comedy", "macbeth", "hamlet", "sonnet",
            "modernism", "postmodernism", "romanticism", "realism",
            "gothic", "satire", "irony", "allegory",
            "philosophy", "ethics", "aesthetics", "existentialism",
            "phenomenology", "hermeneutics", "rhetoric",
            "humanities", "cultural studies", "art history",
            "literary criticism", "literary theory", "deconstruction",
        ],
        "subdomains": {
            "drama": ["shakespeare", "macbeth", "hamlet", "tragedy", "comedy",
                     "playwright", "theater", "dramatic irony"],
            "poetry": ["poem", "sonnet", "meter", "rhyme", "stanza", "haiku",
                      "epic poetry", "lyric"],
            "fiction": ["novel", "short story", "narrator", "plot",
                       "character development", "point of view"],
            "philosophy": ["philosophy", "ethics", "existentialism",
                          "phenomenology", "epistemology", "metaphysics"],
            "cultural_studies": ["cultural studies", "art history",
                                "aesthetics", "humanities"],
        },
    },
    "law": {
        "keywords": [
            "constitution", "statute", "precedent", "jurisprudence",
            "criminal law", "civil law", "contract", "tort", "liability",
            "jurisdiction", "court", "legislation", "regulation",
            "intellectual property", "patent", "copyright",
            "consideration", "doctrine", "legal theory", "plaintiff",
            "defendant", "judgment", "verdict", "appeal",
            "human rights", "due process", "habeas corpus",
            "equity", "common law", "statutory interpretation",
        ],
        "subdomains": {
            "contract_law": ["contract", "consideration", "breach", "offer",
                            "acceptance", "performance", "remedy"],
            "criminal_law": ["criminal law", "felony", "misdemeanor",
                            "prosecution", "defense", "sentencing"],
            "constitutional_law": ["constitution", "amendment", "judicial review",
                                  "separation of powers", "due process",
                                  "human rights"],
            "intellectual_property": ["intellectual property", "patent", "copyright",
                                     "trademark", "trade secret"],
            "tort_law": ["tort", "negligence", "liability", "damages",
                        "duty of care", "causation"],
        },
    },
    "languages": {
        "keywords": [
            "verb conjugation", "grammar", "syntax", "morphology",
            "phonetics", "phonology", "semantics", "pragmatics",
            "linguistics", "second language", "language acquisition",
            "translation", "bilingual", "multilingual",
            "tense", "subjunctive", "imperative", "declension",
            "french", "spanish", "german", "mandarin", "arabic",
            "japanese", "korean", "hindi", "portuguese",
            "vocabulary", "pronunciation", "dialect", "sociolinguistics",
            "applied linguistics", "language teaching",
            "esl", "efl", "tesol", "language pedagogy",
        ],
        "subdomains": {
            "applied_linguistics": ["language acquisition", "second language",
                                   "language teaching", "esl", "efl", "tesol",
                                   "bilingual education"],
            "theoretical_linguistics": ["phonetics", "phonology", "morphology",
                                       "syntax", "semantics", "pragmatics"],
            "specific_languages": ["french", "spanish", "german", "mandarin",
                                  "arabic", "japanese", "korean", "hindi",
                                  "portuguese"],
        },
    },
    "education": {
        "keywords": [
            "pedagogy", "curriculum", "assessment", "learning theory",
            "bloom's taxonomy", "constructivism", "differentiation",
            "inclusive education", "educational technology", "e-learning",
            "instructional design", "scaffolding", "formative assessment",
            "summative assessment", "learning outcomes", "rubric",
            "classroom management", "student engagement", "andragogy",
            "educational psychology", "cognitive load theory",
            "zone of proximal development", "vygotsky", "piaget",
        ],
        "subdomains": {
            "pedagogy": ["pedagogy", "instructional design", "scaffolding",
                        "constructivism", "bloom's taxonomy"],
            "assessment": ["assessment", "formative assessment", "summative assessment",
                          "rubric", "learning outcomes"],
            "ed_tech": ["educational technology", "e-learning", "lms",
                       "blended learning", "mooc", "gamification"],
        },
    },
    "social_sciences": {
        "keywords": [
            "democracy", "governance", "political system", "election",
            "parliament", "congress", "foreign policy", "diplomacy",
            "international relations", "sovereignty", "geopolitics",
            "political theory", "ideology",
            "sociology", "social stratification", "social mobility",
            "class", "race", "gender studies", "feminism",
            "social relationships", "community", "communities", "social network",
            "anthropology", "ethnography", "culture",
            "psychology", "cognitive psychology", "behavioral psychology",
            "developmental psychology", "social psychology",
            "geography", "geopolitics", "urbanization", "migration",
            "demography", "population dynamics",
        ],
        "subdomains": {
            "political_science": ["democracy", "governance", "election",
                                 "parliament", "political theory", "ideology",
                                 "international relations", "geopolitics"],
            "sociology": ["sociology", "social stratification", "social mobility",
                         "inequality", "class", "race", "gender studies",
                         "social relationships", "community", "communities", "social network"],
            "psychology": ["psychology", "cognitive psychology", "behavioral",
                          "developmental psychology", "social psychology"],
            "anthropology": ["anthropology", "ethnography", "culture",
                            "archaeology", "cultural anthropology"],
            "geography": ["geography", "urbanization", "migration",
                         "demography", "population dynamics"],
        },
    },
    "environmental_science": {
        "keywords": [
            "climate change", "global warming", "renewable energy",
            "sustainability", "carbon emission", "greenhouse gas",
            "biodiversity loss", "deforestation", "pollution",
            "environmental policy", "conservation", "water resource",
            "waste management", "recycling", "circular economy",
            "solar energy", "wind energy", "hydropower", "geothermal",
            "carbon footprint", "carbon neutral", "net zero",
            "ozone layer", "acid rain", "eutrophication",
            "environmental impact", "ecosystem service",
            "clean energy", "energy transition", "fossil fuel",
        ],
        "subdomains": {
            "climate": ["climate change", "global warming", "greenhouse gas",
                       "carbon emission", "carbon footprint", "net zero"],
            "energy": ["renewable energy", "solar energy", "wind energy",
                      "hydropower", "geothermal", "energy transition",
                      "clean energy", "fossil fuel"],
            "conservation": ["conservation", "biodiversity loss", "deforestation",
                            "endangered species", "habitat restoration"],
            "pollution": ["pollution", "waste management", "recycling",
                         "circular economy", "water quality", "air quality"],
        },
    },
    "finance_accounting": {
        "keywords": [
            "finance", "accounting", "investment", "portfolio",
            "valuation", "derivatives", "risk management",
            "financial statement", "balance sheet", "income statement",
            "cash flow", "audit", "tax", "depreciation", "amortization",
            "stock market", "bond", "equity", "mutual fund",
            "hedge fund", "private equity", "ipo", "dividend",
            "financial analysis", "ratio analysis", "working capital",
            "budgeting", "cost accounting", "managerial accounting",
            "gaap", "ifrs", "financial reporting",
            "capital budgeting", "npv", "irr", "wacc",
        ],
        "subdomains": {
            "corporate_finance": ["valuation", "capital budgeting", "npv", "irr",
                                 "wacc", "cost of capital", "dividend policy"],
            "investment": ["portfolio", "stock market", "bond", "equity",
                          "mutual fund", "derivatives", "risk management",
                          "hedge fund"],
            "accounting": ["accounting", "financial statement", "balance sheet",
                          "income statement", "cash flow", "audit", "gaap",
                          "ifrs", "depreciation"],
            "taxation": ["tax", "taxation", "tax planning", "tax compliance",
                        "corporate tax", "income tax"],
        },
    },
    "general": {
        "keywords": [],
        "subdomains": {},
    },
}


# ═══════════════════════════════════════════════════════════════
# PURPOSE CLASSIFICATION RULES
# ═══════════════════════════════════════════════════════════════

PURPOSE_KEYWORDS: Dict[str, List[str]] = {
    "teach": ["teach", "lesson", "lecture", "classroom", "student", "learn",
              "explain to students", "course", "syllabus", "curriculum"],
    "explain": ["explain", "introduction to", "overview", "primer",
                "fundamentals", "basics", "beginner"],
    "introduce": ["introduction", "intro to", "getting started", "what is"],
    "deep_dive": ["deep dive", "advanced", "in-depth", "comprehensive",
                  "detailed analysis", "thorough examination"],
    "revise": ["revise", "revision", "review", "recap", "summary of"],
    "exam_prep": ["exam", "test", "quiz prep", "assessment", "practice questions"],
    "technical_brief": ["technical brief", "technical overview", "system design",
                       "implementation guide", "engineering spec"],
    "research_presentation": ["research", "findings", "methodology",
                             "experiment", "hypothesis", "literature review"],
    "business_pitch": ["pitch", "investor", "fundraising", "startup",
                      "business plan", "proposal"],
    "comparison_presentation": ["comparison", "vs", "versus", "compared to",
                               "differences between", "pros and cons"],
    "process_explanation": ["process", "workflow", "how to", "step by step",
                           "procedure", "method"],
    "data_story": ["data analysis", "analytics", "metrics", "dashboard",
                  "insights from data", "statistical analysis",
                  "trends", "adoption trends", "data-driven"],
}

MODE_KEYWORDS: Dict[str, List[str]] = {
    "lecture": ["lecture", "class", "course", "university", "college"],
    "workshop": ["workshop", "hands-on", "practical", "lab", "exercise"],
    "self_study": ["self study", "self-paced", "independent", "tutorial"],
    "seminar": ["seminar", "discussion", "panel"],
    "conference": ["conference", "talk", "keynote", "presentation"],
    "classroom": ["classroom", "school", "high school", "k-12"],
    "training_session": ["training", "onboarding", "corporate training"],
    "briefing": ["brief", "executive", "summary presentation", "report"],
}


# ═══════════════════════════════════════════════════════════════
# TEMPLATE RECOMMENDATION RULES
# ═══════════════════════════════════════════════════════════════

TEMPLATE_BY_DOMAIN_PURPOSE: Dict[str, Dict[str, str]] = {
    "computer_science": {
        "default": "technical",
        "teach": "academic",
        "explain": "visual",
        "deep_dive": "technical",
        "research_presentation": "minimal",
    },
    "mathematics": {
        "default": "academic",
        "teach": "academic",
        "deep_dive": "technical",
    },
    "physics": {
        "default": "academic",
        "technical_brief": "technical",
    },
    "chemistry": {
        "default": "academic",
        "teach": "visual",
    },
    "biology": {
        "default": "visual",
        "teach": "visual",
        "research_presentation": "academic",
    },
    "medicine_health_sciences": {
        "default": "academic",
        "teach": "academic",
        "research_presentation": "minimal",
        "data_story": "editorial",
    },
    "engineering": {
        "default": "technical",
        "teach": "academic",
    },
    "business": {
        "default": "editorial",
        "business_pitch": "editorial",
        "data_story": "minimal",
    },
    "economics": {
        "default": "academic",
        "business_pitch": "editorial",
        "data_story": "minimal",
    },
    "history": {
        "default": "editorial",
        "teach": "academic",
    },
    "literature_humanities": {
        "default": "editorial",
        "teach": "academic",
        "research_presentation": "minimal",
    },
    "law": {
        "default": "academic",
        "teach": "academic",
        "research_presentation": "minimal",
    },
    "languages": {
        "default": "visual",
        "teach": "visual",
        "explain": "academic",
    },
    "education": {
        "default": "visual",
        "teach": "academic",
        "research_presentation": "minimal",
    },
    "social_sciences": {
        "default": "academic",
        "teach": "academic",
        "research_presentation": "minimal",
        "data_story": "editorial",
    },
    "environmental_science": {
        "default": "visual",
        "teach": "academic",
        "data_story": "editorial",
        "research_presentation": "minimal",
    },
    "finance_accounting": {
        "default": "editorial",
        "teach": "academic",
        "data_story": "minimal",
        "business_pitch": "editorial",
    },
    "general": {
        "default": "academic",
    },
}

THEME_BY_DOMAIN_TEMPLATE: Dict[str, Dict[str, str]] = {
    "computer_science": {
        "technical": "indigo_innovation",
        "academic": "blue_professional",
        "visual": "blue_professional",
        "minimal": "minimal_charcoal",
        "editorial": "minimal_charcoal",
    },
    "mathematics": {
        "academic": "blue_professional",
        "technical": "minimal_charcoal",
        "minimal": "minimal_charcoal",
    },
    "physics": {
        "academic": "blue_professional",
        "technical": "indigo_innovation",
    },
    "chemistry": {
        "academic": "emerald_academic",
        "visual": "teal_corporate",
    },
    "biology": {
        "visual": "emerald_academic",
        "academic": "emerald_academic",
    },
    "medicine_health_sciences": {
        "academic": "blue_professional",
        "minimal": "minimal_charcoal",
        "editorial": "teal_corporate",
    },
    "engineering": {
        "technical": "teal_corporate",
        "academic": "blue_professional",
    },
    "business": {
        "editorial": "orange_energy",
        "minimal": "minimal_charcoal",
    },
    "economics": {
        "academic": "blue_professional",
        "editorial": "teal_corporate",
        "minimal": "minimal_charcoal",
    },
    "history": {
        "editorial": "minimal_charcoal",
        "academic": "blue_professional",
    },
    "literature_humanities": {
        "editorial": "minimal_charcoal",
        "academic": "blue_professional",
        "minimal": "minimal_charcoal",
    },
    "law": {
        "academic": "blue_professional",
        "minimal": "minimal_charcoal",
    },
    "languages": {
        "visual": "orange_energy",
        "academic": "blue_professional",
    },
    "education": {
        "visual": "emerald_academic",
        "academic": "blue_professional",
        "minimal": "minimal_charcoal",
    },
    "social_sciences": {
        "academic": "blue_professional",
        "minimal": "minimal_charcoal",
        "editorial": "teal_corporate",
    },
    "environmental_science": {
        "visual": "emerald_academic",
        "academic": "emerald_academic",
        "editorial": "teal_corporate",
        "minimal": "minimal_charcoal",
    },
    "finance_accounting": {
        "editorial": "teal_corporate",
        "academic": "blue_professional",
        "minimal": "minimal_charcoal",
    },
    "general": {
        "academic": "blue_professional",
        "technical": "indigo_innovation",
        "editorial": "minimal_charcoal",
        "visual": "blue_professional",
        "minimal": "minimal_charcoal",
    },
}


# ═══════════════════════════════════════════════════════════════
# STORY GRAMMAR SELECTION RULES
# ═══════════════════════════════════════════════════════════════

GRAMMAR_BY_DOMAIN: Dict[str, StoryGrammarType] = {
    "computer_science": StoryGrammarType.TECHNICAL_SYSTEM,
    "mathematics": StoryGrammarType.CONCEPT_TEACHING,
    "physics": StoryGrammarType.CONCEPT_TEACHING,
    "chemistry": StoryGrammarType.PROCESS,
    "biology": StoryGrammarType.PROCESS,
    "medicine_health_sciences": StoryGrammarType.CONCEPT_TEACHING,
    "engineering": StoryGrammarType.TECHNICAL_SYSTEM,
    "business": StoryGrammarType.DATA_STORY,
    "economics": StoryGrammarType.DATA_STORY,
    "history": StoryGrammarType.HISTORY_EVOLUTION,
    "literature_humanities": StoryGrammarType.CONCEPT_TEACHING,
    "law": StoryGrammarType.CONCEPT_TEACHING,
    "languages": StoryGrammarType.CONCEPT_TEACHING,
    "education": StoryGrammarType.CONCEPT_TEACHING,
    "social_sciences": StoryGrammarType.COMPARISON,
    "environmental_science": StoryGrammarType.DATA_STORY,
    "finance_accounting": StoryGrammarType.DATA_STORY,
    "general": StoryGrammarType.CONCEPT_TEACHING,
}

# Override grammar for specific purposes
GRAMMAR_BY_PURPOSE: Dict[str, StoryGrammarType] = {
    "comparison_presentation": StoryGrammarType.COMPARISON,
    "research_presentation": StoryGrammarType.RESEARCH,
    "data_story": StoryGrammarType.DATA_STORY,
    "process_explanation": StoryGrammarType.PROCESS,
}

# Modifier suggestions by domain
MODIFIER_SUGGESTIONS: Dict[str, List[StoryGrammarType]] = {
    "computer_science": [StoryGrammarType.CONCEPT_TEACHING, StoryGrammarType.COMPARISON],
    "mathematics": [StoryGrammarType.PROCESS],
    "physics": [StoryGrammarType.PROCESS, StoryGrammarType.DATA_STORY],
    "chemistry": [StoryGrammarType.CONCEPT_TEACHING, StoryGrammarType.COMPARISON],
    "biology": [StoryGrammarType.CONCEPT_TEACHING, StoryGrammarType.DATA_STORY],
    "medicine_health_sciences": [StoryGrammarType.PROCESS, StoryGrammarType.DATA_STORY],
    "engineering": [StoryGrammarType.CONCEPT_TEACHING, StoryGrammarType.PROCESS],
    "business": [StoryGrammarType.COMPARISON, StoryGrammarType.PROCESS],
    "economics": [StoryGrammarType.CONCEPT_TEACHING, StoryGrammarType.COMPARISON],
    "history": [StoryGrammarType.CONCEPT_TEACHING, StoryGrammarType.DATA_STORY],
    "literature_humanities": [StoryGrammarType.COMPARISON, StoryGrammarType.HISTORY_EVOLUTION],
    "law": [StoryGrammarType.COMPARISON, StoryGrammarType.PROCESS],
    "languages": [StoryGrammarType.PROCESS, StoryGrammarType.COMPARISON],
    "education": [StoryGrammarType.PROCESS, StoryGrammarType.DATA_STORY],
    "social_sciences": [StoryGrammarType.DATA_STORY, StoryGrammarType.CONCEPT_TEACHING],
    "environmental_science": [StoryGrammarType.PROCESS, StoryGrammarType.CONCEPT_TEACHING],
    "finance_accounting": [StoryGrammarType.COMPARISON, StoryGrammarType.PROCESS],
    "general": [StoryGrammarType.CONCEPT_TEACHING],
}

# Extra modifiers triggered by topic intelligence signals
TOPIC_SIGNAL_MODIFIERS: Dict[str, StoryGrammarType] = {
    "misconception": StoryGrammarType.CONCEPT_TEACHING,
    "comparison": StoryGrammarType.COMPARISON,
    "chronology": StoryGrammarType.HISTORY_EVOLUTION,
    "data": StoryGrammarType.DATA_STORY,
    "process": StoryGrammarType.PROCESS,
}


# ═══════════════════════════════════════════════════════════════
# CLASSIFICATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def _keyword_match(kw: str, text: str) -> bool:
    """Match keyword in text with word boundaries and common inflection (plurals),
    preventing false substring matches (e.g. 'ph' in 'photosynthesis' or 'morphology' in 'geomorphology')."""
    kw = kw.strip()
    if not kw:
        return False
    if kw.endswith("y") and len(kw) > 2 and kw[-2] not in "aeiou":
        stem = re.escape(kw[:-1])
        pattern = r'(?:\b|^)' + stem + r'(?:y|ies)(?:\b|$)'
    else:
        pattern = r'(?:\b|^)' + re.escape(kw) + r'(?:s|es)?(?:\b|$)'
    return bool(re.search(pattern, text, re.IGNORECASE))


def _normalize_text(*texts: Optional[str]) -> str:
    """Concatenate and normalize text signals for keyword matching."""
    parts = [t.lower().strip() for t in texts if t]
    return " ".join(parts)


def classify_domain(
    topic: str,
    audience: str = "",
    custom_context: str = "",
    ontology_evidence: Optional[Dict[str, Any]] = None,
) -> DomainClassification:
    """
    Multi-signal domain classification.
    
    Resolution policy (spec §6, §13):
      1. Check deterministic keyword rules across all available signals
      2. Use ontology evidence + custom_context for disambiguation
      3. If ambiguous and context available, apply CONTEXT_DISAMBIGUATION
      4. Return with confidence and classification_basis

    Classification basis values:
      DETERMINISTIC_RULE       — clear single-domain winner
      CONTEXT_DISAMBIGUATION   — ambiguous resolved by context/ontology signals
      MODEL_DISAMBIGUATION     — resolved by LLM (Phase 2)
      DEFAULT_FALLBACK         — no keyword match at all
    """
    combined = _normalize_text(topic, audience, custom_context)

    # Model override support via ontology_evidence
    if ontology_evidence and "_model_domain_override" in ontology_evidence:
        override_domain = ontology_evidence["_model_domain_override"]
        override_sub = ontology_evidence.get("_model_subdomain_override", "")
        return DomainClassification(
            domain=override_domain,
            subdomain=override_sub,
            confidence=0.90,
            classification_basis=CLASSIFICATION_BASIS_MODEL,
        )

    # Add ontology evidence if available
    ontology_text = ""
    if ontology_evidence:
        core_subs = ontology_evidence.get("core_subtopics", [])
        must_inc = ontology_evidence.get("must_include", [])
        ontology_text = " ".join(core_subs + must_inc).lower()
        combined = f"{combined} {ontology_text}"

    # Score each domain by keyword hits
    scores: Dict[str, Tuple[float, str, int]] = {}
    for domain_key, domain_data in DOMAIN_RULES.items():
        if domain_key == "general":
            continue
        hits = 0
        total_kw = len(domain_data["keywords"])
        if total_kw == 0:
            continue
        for kw in domain_data["keywords"]:
            if _keyword_match(kw, combined):
                hits += 1
        if hits > 0:
            score = hits / max(total_kw, 1)
            # Determine best subdomain
            best_sub = ""
            best_sub_score = 0
            for sub_key, sub_kws in domain_data.get("subdomains", {}).items():
                sub_hits = sum(1 for skw in sub_kws if _keyword_match(skw, combined))
                if sub_hits > best_sub_score:
                    best_sub_score = sub_hits
                    best_sub = sub_key
            scores[domain_key] = (score, best_sub, hits)

    if not scores:
        logger.info(f"[DomainClassifier] No keyword match for topic='{topic}' → general")
        return DomainClassification(
            domain="general",
            subdomain="",
            confidence=0.15,
            classification_basis=CLASSIFICATION_BASIS_DEFAULT,
        )

    # Sort by score descending
    ranked = sorted(scores.items(), key=lambda x: x[1][0], reverse=True)
    best_domain = ranked[0][0]
    best_score, best_sub, best_hits = ranked[0][1]

    # Check for ambiguity: if top two domains are within 20% of each other
    is_ambiguous = False
    if len(ranked) >= 2:
        second_score = ranked[1][1][0]
        if best_score > 0 and second_score / best_score > 0.8:
            is_ambiguous = True

    # ─── AMBIGUOUS DOMAIN RESOLUTION ──────────────────────────
    if is_ambiguous:
        second_domain = ranked[1][0]
        second_sub = ranked[1][1][1]

        # Try context-based disambiguation using custom_context or ontology
        context_signal = _normalize_text(custom_context)
        if ontology_text:
            context_signal = f"{context_signal} {ontology_text}"

        if context_signal.strip():
            # Re-score using only context signals (not original topic)
            ctx_scores: Dict[str, int] = {}
            for candidate in [best_domain, second_domain]:
                ctx_hits = 0
                for kw in DOMAIN_RULES[candidate]["keywords"]:
                    if _keyword_match(kw, context_signal):
                        ctx_hits += 1
                ctx_scores[candidate] = ctx_hits

            if ctx_scores.get(best_domain, 0) > ctx_scores.get(second_domain, 0):
                # Context confirms the primary guess
                diff = ctx_scores[best_domain] - ctx_scores.get(second_domain, 0)
                confidence = min(0.95, 0.80 + diff * 0.05)
                basis = CLASSIFICATION_BASIS_CONTEXT

                # Re-check subdomain using context
                best_sub_score = 0
                for sub_key, sub_kws in DOMAIN_RULES[best_domain].get("subdomains", {}).items():
                    sub_hits = sum(1 for skw in sub_kws if _keyword_match(skw, context_signal))
                    if sub_hits > best_sub_score:
                        best_sub_score = sub_hits
                        best_sub = sub_key

                logger.info(
                    f"[DomainClassifier] Ambiguity resolved by context: "
                    f"{best_domain}(ctx={ctx_scores[best_domain]}) > "
                    f"{second_domain}(ctx={ctx_scores[second_domain]})"
                )
            elif ctx_scores.get(second_domain, 0) > ctx_scores.get(best_domain, 0):
                # Context flips to the second domain
                best_domain = second_domain
                diff = ctx_scores[second_domain] - ctx_scores.get(ranked[0][0], 0)
                confidence = min(0.95, 0.80 + diff * 0.05)
                basis = CLASSIFICATION_BASIS_CONTEXT

                # Determine subdomain for new best domain
                best_sub = ranked[1][1][1]
                best_sub_score = 0
                for sub_key, sub_kws in DOMAIN_RULES[best_domain].get("subdomains", {}).items():
                    sub_hits = sum(1 for skw in sub_kws if _keyword_match(skw, context_signal))
                    if sub_hits > best_sub_score:
                        best_sub_score = sub_hits
                        best_sub = sub_key

                logger.info(
                    f"[DomainClassifier] Ambiguity flipped by context: "
                    f"{second_domain}(ctx={ctx_scores[second_domain]}) > "
                    f"{ranked[0][0]}(ctx={ctx_scores.get(ranked[0][0], 0)})"
                )
            else:
                # Context tie — remain ambiguous, lower confidence
                confidence = 0.35
                basis = CLASSIFICATION_BASIS_DETERMINISTIC
                logger.info(
                    f"[DomainClassifier] Ambiguous: {best_domain}({best_score:.3f}) "
                    f"vs {second_domain}({ranked[1][1][0]:.3f}) for topic='{topic}'"
                )
        else:
            # No context available — lower confidence, deterministic pick
            confidence = 0.35
            basis = CLASSIFICATION_BASIS_DETERMINISTIC
            logger.info(
                f"[DomainClassifier] Ambiguous (no context): {best_domain}({best_score:.3f}) "
                f"vs {second_domain}({ranked[1][1][0]:.3f}) for topic='{topic}'"
            )
    else:
        # Decisive single-domain winner
        confidence = min(0.98, 0.85 + best_hits * 0.03)
        basis = CLASSIFICATION_BASIS_DETERMINISTIC

    logger.info(
        f"[DomainClassifier] topic='{topic}' → domain={best_domain}, "
        f"subdomain={best_sub}, confidence={confidence:.2f}, basis={basis}"
    )
    return DomainClassification(
        domain=best_domain,
        subdomain=best_sub,
        confidence=round(min(1.0, confidence), 3),
        classification_basis=basis,
    )


# ═══════════════════════════════════════════════════════════════
# LOW-CONFIDENCE MODEL DISAMBIGUATION
# ═══════════════════════════════════════════════════════════════
# When deterministic + context disambiguation are insufficient,
# invoke a lightweight LLM classifier. This eliminates hand-written
# rules for every ambiguous noun (spec §13).
#
# Contract:
#   HIGH-CONFIDENCE deterministic → zero LLM cost
#   LOW-CONFIDENCE / ambiguous    → one lightweight classifier call
#   classification_basis          → MODEL_DISAMBIGUATION
# ═══════════════════════════════════════════════════════════════

# Confidence threshold below which the model fallback is triggered
MODEL_DISAMBIGUATION_CONFIDENCE_THRESHOLD = 0.70

# Valid domains the model may return
_VALID_DOMAINS = set(DOMAIN_RULES.keys())

# Subdomain registry for model validation
_VALID_SUBDOMAINS: Dict[str, set] = {
    domain_key: set(domain_data.get("subdomains", {}).keys())
    for domain_key, domain_data in DOMAIN_RULES.items()
}


def _build_disambiguation_prompt(
    topic: str,
    custom_context: str,
    candidate_domains: list,
) -> str:
    """Build a minimal prompt for the lightweight classifier."""
    domain_list = ", ".join(candidate_domains)
    ctx_line = f"\nAdditional context: {custom_context}" if custom_context else ""
    return (
        f"Classify the academic/educational topic into exactly one domain.\n"
        f"\nTopic: {topic}{ctx_line}\n"
        f"\nValid domains: {domain_list}\n"
        f"\nRespond with ONLY a JSON object (no markdown, no explanation):\n"
        f'{{"domain": "<domain>", "subdomain": "<subdomain_or_empty>", "confidence": <0.0-1.0>}}'
    )


async def classify_domain_with_model_fallback(
    topic: str,
    audience: str = "",
    custom_context: str = "",
    ontology_evidence: Optional[Dict[str, Any]] = None,
) -> DomainClassification:
    """
    Async domain classification with model fallback for low-confidence cases.

    Resolution policy:
      1. Run deterministic classify_domain() — zero LLM cost for clear matches
      2. If confidence >= threshold AND not DEFAULT_FALLBACK → return deterministic result immediately (zero LLM call)
      3. If confidence < threshold or DEFAULT_FALLBACK → invoke one lightweight LLM classifier call
      4. Validate model response; fall back to deterministic result if invalid

    This eliminates the need for hand-written keyword rules for ambiguous nouns.
    """
    # Step 1: Deterministic classification (zero LLM cost)
    result = classify_domain(
        topic=topic,
        audience=audience,
        custom_context=custom_context,
        ontology_evidence=ontology_evidence,
    )

    # Step 2: If high confidence and not default fallback, return immediately (zero LLM call)
    if result.confidence >= MODEL_DISAMBIGUATION_CONFIDENCE_THRESHOLD and result.classification_basis != CLASSIFICATION_BASIS_DEFAULT:
        logger.info(
            f"[DomainClassifier] High-confidence ({result.confidence:.2f} >= "
            f"{MODEL_DISAMBIGUATION_CONFIDENCE_THRESHOLD}, basis={result.classification_basis}) — zero model calls"
        )
        return result

    # Step 3: Low confidence — invoke lightweight model classifier
    logger.info(
        f"[DomainClassifier] Low-confidence ({result.confidence:.2f} < "
        f"{MODEL_DISAMBIGUATION_CONFIDENCE_THRESHOLD}) — invoking model disambiguation "
        f"for topic='{topic}'"
    )

    try:
        from ..ai.router import ModelRouter
        import json as _json

        router = ModelRouter()

        # Build candidate list: all domains (the model should pick freely)
        candidate_domains = list(_VALID_DOMAINS)
        prompt = _build_disambiguation_prompt(topic, custom_context, candidate_domains)

        llm_response = await router.generate_text(
            task="semantic_qa",  # cheapest task tier
            prompt=prompt,
            system_instruction=(
                "You are a domain classifier for educational presentations. "
                "Classify the topic into the single most appropriate academic domain. "
                "Return ONLY valid JSON."
            ),
            temperature=0.0,   # deterministic
            max_tokens=100,    # very small — just JSON
            timeout=8.0,       # fast timeout
        )

        # Parse model response
        raw = llm_response.text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        parsed = _json.loads(raw)
        model_domain = parsed.get("domain", "").strip().lower()
        model_subdomain = parsed.get("subdomain", "").strip().lower()
        model_confidence = float(parsed.get("confidence", 0.5))

        # Validate: domain must be in our registry
        if model_domain not in _VALID_DOMAINS:
            logger.warning(
                f"[DomainClassifier] Model returned invalid domain '{model_domain}', "
                f"keeping deterministic result: {result.domain}"
            )
            return result

        # Validate subdomain (if provided, must be valid for that domain)
        if model_subdomain and model_subdomain not in _VALID_SUBDOMAINS.get(model_domain, set()):
            model_subdomain = ""  # Clear invalid subdomain but keep the domain

        logger.info(
            f"[DomainClassifier] Model disambiguation: topic='{topic}' → "
            f"domain={model_domain}, subdomain={model_subdomain}, "
            f"confidence={model_confidence:.2f}"
        )

        return DomainClassification(
            domain=model_domain,
            subdomain=model_subdomain,
            confidence=round(min(1.0, model_confidence), 3),
            classification_basis=CLASSIFICATION_BASIS_MODEL,
        )

    except Exception as e:
        logger.warning(
            f"[DomainClassifier] Model disambiguation failed ({e}), "
            f"returning deterministic result: {result.domain}/{result.subdomain}"
        )
        return result


def classify_purpose(
    topic: str,
    audience: str = "",
    custom_context: str = "",
    depth: str = "full",
) -> PresentationGoal:
    """
    Classify the presentation's pedagogical purpose.
    Rules first, no LLM call (spec §13).
    """
    combined = _normalize_text(topic, audience, custom_context)

    best_purpose = None
    best_hits = 0
    for purpose_key, keywords in PURPOSE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in combined)
        if hits > best_hits:
            best_hits = hits
            best_purpose = purpose_key

    # Depth-based override — applied when no strong keyword signal
    if depth == "quick" and best_purpose in (None, "teach"):
        best_purpose = "introduce"
    elif depth == "expert" and best_purpose in (None, "teach", "explain"):
        best_purpose = "deep_dive"

    # Default to TEACH if no signal matched
    if best_purpose is None:
        best_purpose = "teach"

    try:
        return PresentationGoal(best_purpose)
    except ValueError:
        return PresentationGoal.TEACH


def classify_mode(
    audience: str = "",
    custom_context: str = "",
) -> PresentationMode:
    """Classify presentation delivery mode."""
    combined = _normalize_text(audience, custom_context)

    best_mode = "lecture"
    best_hits = 0
    for mode_key, keywords in MODE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in combined)
        if hits > best_hits:
            best_hits = hits
            best_mode = mode_key

    try:
        return PresentationMode(best_mode)
    except ValueError:
        return PresentationMode.LECTURE


def infer_technicality(
    domain: str,
    audience: str = "",
    depth: str = "full",
) -> ContentDensity:
    """Infer content technicality from domain + audience + depth."""
    technical_domains = {"computer_science", "engineering", "mathematics", "physics",
                        "finance_accounting"}
    aud_lower = audience.lower() if audience else ""

    if domain in technical_domains:
        if depth == "expert" or "advanced" in aud_lower or "professional" in aud_lower:
            return ContentDensity.HIGH
        return ContentDensity.MEDIUM
    if depth == "quick" or "beginner" in aud_lower or "high school" in aud_lower:
        return ContentDensity.LOW
    return ContentDensity.MEDIUM


def infer_audience_expertise(
    audience: str = "",
    education_level: str = "university",
) -> str:
    """Infer audience expertise level."""
    aud = audience.lower() if audience else ""
    if any(w in aud for w in ["expert", "advanced", "senior", "phd", "researcher"]):
        return "advanced"
    if any(w in aud for w in ["beginner", "introductory", "novice", "high school"]):
        return "beginner"
    if education_level in ("professional", "graduate"):
        return "advanced"
    if education_level == "high_school":
        return "beginner"
    return "intermediate"


def infer_visual_preference(
    domain: str,
    technicality: ContentDensity,
) -> str:
    """Infer visual preference from domain and complexity."""
    diagram_first_domains = {"computer_science", "engineering"}
    photo_domains = {"biology", "history", "literature_humanities",
                    "environmental_science"}
    data_viz_domains = {"finance_accounting", "economics"}

    if domain in diagram_first_domains:
        return "diagram_first"
    if domain in photo_domains:
        return "photo"
    if domain in data_viz_domains:
        return "data_visualization"
    if technicality == ContentDensity.HIGH:
        return "minimal"
    return "balanced"


def recommend_template(
    domain: str,
    purpose: PresentationGoal,
) -> str:
    """Deterministic template recommendation based on domain + purpose."""
    domain_map = TEMPLATE_BY_DOMAIN_PURPOSE.get(domain, TEMPLATE_BY_DOMAIN_PURPOSE["general"])
    purpose_key = purpose.value
    rec = domain_map.get(purpose_key, domain_map.get("default", "academic"))
    return rec


def recommend_theme(
    domain: str,
    template: str,
) -> str:
    """Deterministic theme recommendation based on domain + template."""
    domain_map = THEME_BY_DOMAIN_TEMPLATE.get(domain, THEME_BY_DOMAIN_TEMPLATE["general"])
    rec = domain_map.get(template, "blue_professional")
    return rec


def recommend_story_grammar(
    domain: str,
    purpose: PresentationGoal,
    topic_intelligence: Optional[Dict[str, Any]] = None,
) -> Tuple[StoryGrammarType, List[StoryGrammarType]]:
    """
    Select primary story grammar + modifiers.

    Primary grammar: determined by purpose override or domain default.
    Modifiers: domain-suggested + topic-signal-triggered.
    No arbitrary composition (spec §2).
    """
    # Purpose-specific override
    primary = GRAMMAR_BY_PURPOSE.get(purpose.value)
    if primary is None:
        primary = GRAMMAR_BY_DOMAIN.get(domain, StoryGrammarType.CONCEPT_TEACHING)

    # Base domain modifiers
    modifiers = list(MODIFIER_SUGGESTIONS.get(domain, [StoryGrammarType.CONCEPT_TEACHING]))

    # Topic intelligence signal modifiers
    if topic_intelligence:
        if topic_intelligence.get("misconceptions"):
            sig_mod = TOPIC_SIGNAL_MODIFIERS.get("misconception")
            if sig_mod and sig_mod not in modifiers:
                modifiers.append(sig_mod)
        if topic_intelligence.get("comparison_candidates"):
            sig_mod = TOPIC_SIGNAL_MODIFIERS.get("comparison")
            if sig_mod and sig_mod not in modifiers:
                modifiers.append(sig_mod)
        if topic_intelligence.get("chronology_if_relevant"):
            sig_mod = TOPIC_SIGNAL_MODIFIERS.get("chronology")
            if sig_mod and sig_mod not in modifiers:
                modifiers.append(sig_mod)
        if topic_intelligence.get("processes"):
            sig_mod = TOPIC_SIGNAL_MODIFIERS.get("process")
            if sig_mod and sig_mod not in modifiers:
                modifiers.append(sig_mod)

    # Remove primary from modifiers if present
    modifiers = [m for m in modifiers if m != primary]

    # Limit modifiers to 3
    modifiers = modifiers[:3]

    logger.info(
        f"[DomainClassifier] Grammar: primary={primary.value}, "
        f"modifiers={[m.value for m in modifiers]}"
    )
    return primary, modifiers


def estimate_duration(slide_count: int) -> int:
    """Estimate presentation duration in minutes (2 min/slide average)."""
    return max(5, int(slide_count * 2.0))


def canonicalize_topic(topic: str) -> str:
    """Normalize topic string for consistent matching."""
    # Strip common prefixes/suffixes
    cleaned = topic.strip()
    # Remove common framing phrases
    for prefix in ["introduction to ", "overview of ", "understanding ",
                   "fundamentals of ", "basics of ", "advanced "]:
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    # Title case
    return cleaned.strip().title()
