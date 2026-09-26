"""
Domain-Specific Content Writing & Depth Engine (Phase 2)
=========================================================
Provides domain-aware writing profiles, audience depth adaptation,
and content depth framework that maps SlideIntent to reasoning dimensions.

Domain profiles are GUIDANCE, not templates. Content must primarily derive from
PresentationBrief, TopicIntelligencePack, SlideBlueprint, source context,
audience, and presentation purpose. Domain profiles only influence reasoning
and writing style.

Subdomain and topic intelligence override generic domain rules.
Priority: source/context → topic intelligence → subdomain → domain → general fallback.
"""
import logging
import re
from typing import Dict, Any, List, Optional, Tuple, Set
from .schemas import SlideIntent, ContentDensity, SlideConceptPacket, SlideBlueprint, PresentationBrief

logger = logging.getLogger("teachgenie.presentation.domain_content_writer")


# ═══════════════════════════════════════════════════════════════
# Dynamic Domain Educator Personas (Guidance Only, Not Templates)
# ═══════════════════════════════════════════════════════════════

DOMAIN_EDUCATOR_PERSONAS: Dict[str, str] = {
    "computer_science": "Senior Systems Architect and Computing Educator emphasizing runtime state, latency, concurrency, and architecture",
    "mathematics": "Mathematician and Mathematics Educator emphasizing geometric intuition, formal definitions, and rigorous proof",
    "physics": "Theoretical and Experimental Physicist emphasizing physical models, conservation laws, and limiting boundary states",
    "chemistry": "Physical and Organic Chemist emphasizing reaction mechanisms, molecular orbitals, and thermodynamics",
    "biology": "Cellular and Molecular Biology Educator emphasizing structure-function relationships, biochemical pathways, and regulation",
    "medicine_health_sciences": "Clinical Educator and Pathophysiologist emphasizing mechanisms of action, clinical evidence, and diagnosis",
    "history": "Historian emphasizing primary source evidence, historiographical causation, continuity, and institutional change",
    "literature_humanities": "Literary Scholar and Humanities Educator emphasizing textual close reading, motif, dramatic tension, and interpretive evidence",
    "law": "Legal Scholar and Educator emphasizing legal doctrine, elements of proof, jurisdictional authority, and precedential analysis",
    "business": "Strategic Management Educator emphasizing market structures, operational economics, and decision frameworks",
    "economics": "Applied Micro and Macroeconomist emphasizing equilibrium dynamics, incentives, trade-offs, and empirical models",
    "finance_accounting": "Financial Analyst and Accounting Educator emphasizing valuation models, capital structure, and regulatory disclosure",
    "education": "Pedagogical Theorist emphasizing cognitive development, instructional design, and formative assessment",
    "social_sciences": "Social Scientist emphasizing empirical methodology, institutional frameworks, and behavioral evidence",
    "environmental_science": "Earth and Environmental Scientist emphasizing biogeochemical cycles, ecological dynamics, and empirical trends",
    "languages": "Linguist emphasizing syntactic structures, phonology, and semantic transformations",
    "engineering": "Systems and Design Engineer emphasizing design constraints, failure modes, and performance trade-offs",
    "general": "Subject Matter Specialist and Instructional Educator emphasizing conceptual clarity, concrete mechanisms, and structured reasoning",
}


def get_domain_educator_persona(domain: str, subdomain: str = "") -> str:
    """Resolve an educator persona for the domain/subdomain."""
    dom_key = domain.lower().strip() if domain else "general"
    persona = DOMAIN_EDUCATOR_PERSONAS.get(dom_key, DOMAIN_EDUCATOR_PERSONAS["general"])
    if subdomain:
        persona = f"{persona} with specialized focus in {subdomain}"
    return persona


# ═══════════════════════════════════════════════════════════════
# Contextual Vocabulary Leakage Guard (Risk + Context Validation)
# ═══════════════════════════════════════════════════════════════

# Terms that carry high cross-domain leakage risk when used outside appropriate contexts
DOMAIN_LEAKAGE_RISKS: Dict[str, List[str]] = {
    "biology": [
        "operational pipeline", "runtime", "system architecture",
        "microservices", "throughput", "latency", "subsystems",
        "call stack", "thread pool", "payload",
    ],
    "medicine_health_sciences": [
        "operational pipeline", "system architecture", "microservices",
        "runtime", "latency", "throughput", "subsystem components",
    ],
    "history": [
        "operational pipeline", "pipeline", "workflow", "runtime",
        "system architecture", "latency", "throughput", "subsystems",
        "stack trace", "microservices", "deployment pipeline",
    ],
    "literature_humanities": [
        "operational pipeline", "pipeline", "runtime", "system architecture",
        "throughput", "latency", "subsystems", "microservices", "payload",
    ],
    "literature_arts": [
        "operational pipeline", "pipeline", "runtime", "system architecture",
        "throughput", "latency", "subsystems", "microservices", "payload",
    ],
    "law": [
        "operational pipeline", "synergies", "ROI", "runtime",
        "microservices", "user onboarding", "funnel",
    ],
    "law_legal_studies": [
        "operational pipeline", "synergies", "ROI", "runtime",
        "microservices", "user onboarding", "funnel",
    ],
    "philosophy": [
        "operational pipeline", "microservices", "user onboarding", "ROI", "synergies",
    ],
    "mathematics": [
        "operational pipeline", "stakeholders", "user experience",
        "business goals", "market fit", "funnel",
    ],
    "physics": [
        "operational pipeline", "stakeholders", "user experience",
        "business goals", "ROI",
    ],
}

# Contexts or subdomains where seemingly leaked terms are legitimate (e.g. bioinformatics pipeline)
LEGITIMATE_CONTEXT_EXEMPTIONS: Dict[str, List[str]] = {
    "pipeline": ["bioinformatics", "genomics", "data", "processing", "computational", "ci/cd", "oil", "gas", "manufacturing", "supply"],
    "architecture": ["narrative", "legal", "financial", "cognitive", "biological", "cellular", "tissue", "gothic", "structural"],
    "runtime": ["computational", "algorithm", "software", "complexity", "simulation"],
    "latency": ["neural", "synaptic", "response", "computational", "network"],
    "throughput": ["renal", "metabolic", "cardiac", "cellular", "computational", "production", "bioinformatics", "genomics", "sequencing", "high-throughput"],
}


def check_contextual_vocabulary_leakage(
    text: str,
    domain: str,
    subdomain: str = "",
    topic: str = "",
) -> List[str]:
    """
    Detect vocabulary leakage while honoring contextual legitimacy (§3).
    A term is only flagged when its usage is semantically inappropriate for the topic/context.
    """
    if not text:
        return []

    domain_key = domain.lower().strip() if domain else "general"
    risk_terms = DOMAIN_LEAKAGE_RISKS.get(domain_key, [])
    if not risk_terms:
        return []

    combined_context = f"{topic} {subdomain}".lower()
    text_lower = text.lower()
    flagged: List[str] = []

    for term in risk_terms:
        # Check if the risk term appears in text
        if re.search(r'\b' + re.escape(term) + r'\b', text_lower):
            # Check if there is an exemption for this term in the topic/subdomain context
            is_exempt = False
            for root_word, valid_contexts in LEGITIMATE_CONTEXT_EXEMPTIONS.items():
                if root_word in term:
                    if any(v_ctx in combined_context for v_ctx in valid_contexts):
                        is_exempt = True
                        break
            if not is_exempt:
                flagged.append(term)

    return flagged


# ═══════════════════════════════════════════════════════════════
# Content Depth Framework — Reasoning Dimensions per Intent
# ═══════════════════════════════════════════════════════════════

# Maps SlideIntent to which reasoning dimensions are relevant
INTENT_REASONING_DIMENSIONS: Dict[str, List[str]] = {
    SlideIntent.DEFINITION.value:           ["WHAT", "WHY"],
    SlideIntent.CONCEPT_EXPLANATION.value:   ["WHAT", "HOW", "WHY"],
    SlideIntent.PROCESS_EXPLANATION.value:   ["HOW", "WHY"],
    SlideIntent.WORKED_EXAMPLE.value:        ["EXAMPLE", "HOW"],
    SlideIntent.COMPARISON.value:            ["DIFFERENCES", "WHEN_TO_USE"],
    SlideIntent.TRADEOFF.value:              ["BENEFIT", "COST", "DECISION_RULE"],
    SlideIntent.MISCONCEPTION.value:         ["WRONG_BELIEF", "CORRECT_MODEL", "WHY_CONFUSION"],
    SlideIntent.DATA_INSIGHT.value:          ["WHAT", "TREND", "IMPLICATION"],
    SlideIntent.CASE_STUDY.value:            ["CONTEXT", "ACTION", "RESULT", "LESSON"],
    SlideIntent.SYSTEM_OVERVIEW.value:       ["WHAT", "HOW", "TRADE-OFF"],
    SlideIntent.COMPONENT_BREAKDOWN.value:   ["WHAT", "HOW"],
    SlideIntent.CODE_EXAMPLE.value:          ["HOW", "EXAMPLE"],
    SlideIntent.FORMULA_EXPLANATION.value:   ["WHAT", "HOW", "EXAMPLE"],
    SlideIntent.REAL_WORLD_APPLICATION.value: ["WHEN", "EXAMPLE", "WHY"],
    SlideIntent.BEST_PRACTICES.value:        ["HOW", "WHY", "COMMON_CONFUSION"],
    SlideIntent.COMMON_MISTAKES.value:       ["WRONG_BELIEF", "CORRECT_MODEL"],
    SlideIntent.KNOWLEDGE_CHECK.value:       ["EXAMPLE"],
    SlideIntent.SUMMARY.value:              ["WHAT", "WHY"],
    SlideIntent.CONTEXT.value:              ["WHAT", "WHEN", "WHY"],
    SlideIntent.WHY_IT_MATTERS.value:       ["WHY", "EXAMPLE"],
    SlideIntent.HOOK.value:                 ["WHY", "EXAMPLE"],
    SlideIntent.COVER.value:                [],
    SlideIntent.Q_AND_A.value:              [],
}


# ═══════════════════════════════════════════════════════════════
# Domain Writing Profiles — Style Guidance (NOT Templates)
# ═══════════════════════════════════════════════════════════════

DOMAIN_WRITING_PROFILES: Dict[str, Dict[str, Any]] = {
    "computer_science": {
        "writing_style": "technical-analytical",
        "emphasis": ["execution flow", "architecture", "constraints", "trade-offs", "system behavior"],
        "preferred_structures": ["architecture diagram", "code walkthrough", "comparison matrix", "process flow"],
        "avoid": ["vague benefits", "marketing language"],
        "example_types": ["code snippet", "system trace", "request lifecycle"],
    },
    "mathematics": {
        "writing_style": "formal-intuitive",
        "emphasis": ["intuition before notation", "formula derivation", "worked example", "interpretation"],
        "preferred_structures": ["formula + explanation", "step-by-step computation", "visual transformation"],
        "avoid": ["formula without context", "result without interpretation"],
        "example_types": ["numerical computation", "geometric visualization", "proof sketch"],
    },
    "physics": {
        "writing_style": "model-experimental",
        "emphasis": ["physical intuition", "mathematical model", "experimental scenario", "limiting conditions"],
        "preferred_structures": ["equation + interpretation", "diagram + annotation", "scenario analysis"],
        "avoid": ["equation without physical meaning", "handwaving"],
        "example_types": ["thought experiment", "numerical scenario", "lab setup"],
    },
    "chemistry": {
        "writing_style": "mechanistic",
        "emphasis": ["reaction mechanism", "molecular reasoning", "conditions", "comparison between pathways"],
        "preferred_structures": ["mechanism diagram", "reaction comparison", "condition table"],
        "avoid": ["listing reactions without mechanism", "memorization without reasoning"],
        "example_types": ["reaction mechanism trace", "synthesis pathway", "lab observation"],
    },
    "biology": {
        "writing_style": "structure-function",
        "emphasis": ["structure-function relationship", "biological process", "significance", "misconception"],
        "preferred_structures": ["annotated illustration", "process cycle", "comparison of systems"],
        "avoid": ["listing parts without function", "oversimplification of mechanisms"],
        "example_types": ["organism case study", "experimental observation", "clinical relevance"],
    },
    "medicine_health_sciences": {
        "writing_style": "evidence-based-clinical",
        "emphasis": ["mechanism of action", "clinical relevance", "evidence", "caution around claims"],
        "preferred_structures": ["pathophysiology flow", "clinical decision tree", "evidence summary"],
        "avoid": ["unsourced medical claims", "definitive statements without evidence"],
        "example_types": ["clinical scenario", "drug mechanism", "epidemiological data"],
    },
    "history": {
        "writing_style": "narrative-analytical",
        "emphasis": ["context", "causes", "chronology", "consequences", "evidence", "interpretation"],
        "preferred_structures": ["timeline", "cause-effect chain", "primary source analysis"],
        "avoid": ["treating history as technical process", "presentism", "unsourced claims"],
        "example_types": ["primary source excerpt", "case comparison", "geographical/demographic data"],
    },
    "literature_humanities": {
        "writing_style": "argumentative-interpretive",
        "emphasis": ["argument", "theme", "textual evidence", "interpretation", "contrast"],
        "preferred_structures": ["close reading", "thematic comparison", "critical lens analysis"],
        "avoid": ["plot summary as analysis", "unsupported assertions"],
        "example_types": ["textual quotation", "comparative passage", "critical perspective"],
    },
    "law": {
        "writing_style": "analytical-precedential",
        "emphasis": ["rule statement", "elements", "precedent", "application", "exception"],
        "preferred_structures": ["rule framework", "case brief", "element analysis", "comparison of doctrines"],
        "avoid": ["legal advice", "overgeneralization of jurisdiction-specific rules"],
        "example_types": ["mini case application", "statutory interpretation", "hypothetical scenario"],
    },
    "business": {
        "writing_style": "strategic-decisional",
        "emphasis": ["framework", "decision criteria", "metrics", "case evidence", "implications"],
        "preferred_structures": ["strategic framework", "decision matrix", "case study flow"],
        "avoid": ["vague strategy language", "unsupported ROI claims"],
        "example_types": ["company case study", "market analysis", "financial comparison"],
    },
    "economics": {
        "writing_style": "analytical-empirical",
        "emphasis": ["model", "equilibrium", "policy implication", "empirical evidence", "trade-off"],
        "preferred_structures": ["supply-demand diagram", "policy comparison", "data trend"],
        "avoid": ["ideology as analysis", "oversimplified causal claims"],
        "example_types": ["policy scenario", "historical economic event", "data comparison"],
    },
    "finance_accounting": {
        "writing_style": "quantitative-regulatory",
        "emphasis": ["financial model", "risk-return", "regulatory context", "calculation"],
        "preferred_structures": ["financial statement", "ratio analysis", "risk framework"],
        "avoid": ["investment advice", "fabricated financial figures"],
        "example_types": ["financial calculation", "valuation scenario", "regulatory case"],
    },
    "education": {
        "writing_style": "pedagogical-reflective",
        "emphasis": ["learning theory", "instructional design", "evidence-based practice", "assessment"],
        "preferred_structures": ["pedagogical model", "lesson design flow", "research synthesis"],
        "avoid": ["prescriptive without evidence", "one-size-fits-all claims"],
        "example_types": ["classroom scenario", "assessment design", "research finding"],
    },
    "social_sciences": {
        "writing_style": "empirical-critical",
        "emphasis": ["theoretical framework", "methodology", "evidence", "interpretation", "limitation"],
        "preferred_structures": ["research design diagram", "theory comparison", "data visualization"],
        "avoid": ["correlation as causation", "unsupported generalizations"],
        "example_types": ["study summary", "survey data", "cross-cultural comparison"],
    },
    "environmental_science": {
        "writing_style": "systems-ecological",
        "emphasis": ["ecological dynamics", "empirical trends", "drivers", "policy implications"],
        "preferred_structures": ["system diagram", "trend analysis", "cause-effect cycle"],
        "avoid": ["advocacy without evidence", "fabricated environmental statistics"],
        "example_types": ["ecosystem case study", "trend data", "policy comparison"],
    },
    "languages": {
        "writing_style": "analytical-communicative",
        "emphasis": ["structural analysis", "usage pattern", "transformation rules", "context sensitivity"],
        "preferred_structures": ["grammatical diagram", "sentence transformation", "contrastive analysis"],
        "avoid": ["prescriptivism without noting descriptive variation"],
        "example_types": ["sentence transformation", "morphological analysis", "pragmatic scenario"],
    },
    "engineering": {
        "writing_style": "design-analytical",
        "emphasis": ["design constraints", "system architecture", "performance metrics", "trade-offs"],
        "preferred_structures": ["system block diagram", "design comparison", "performance analysis"],
        "avoid": ["marketing claims about technology", "vague performance benefits"],
        "example_types": ["design scenario", "failure analysis", "performance measurement"],
    },
    "general": {
        "writing_style": "expository-balanced",
        "emphasis": ["clarity", "concrete examples", "logical structure", "balanced perspective"],
        "preferred_structures": ["concept breakdown", "comparison", "example-driven explanation"],
        "avoid": ["jargon without definition", "unsupported claims"],
        "example_types": ["real-world scenario", "analogy", "comparison"],
    },
}


# ═══════════════════════════════════════════════════════════════
# Audience Depth Adaptation
# ═══════════════════════════════════════════════════════════════

AUDIENCE_DEPTH_PROFILES: Dict[str, Dict[str, Any]] = {
    "school": {
        "language": "simple, concrete",
        "audience_language": "simple, concrete",
        "explanation_depth": "surface mechanism with visual support",
        "jargon_level": "low — define every technical term",
        "examples": "concrete, everyday analogies",
        "assumed_knowledge": "minimal prior knowledge",
    },
    "undergraduate": {
        "language": "correct terminology, accessible",
        "audience_language": "correct terminology, accessible",
        "explanation_depth": "conceptual mechanism with worked examples",
        "jargon_level": "moderate — use standard disciplinary terms",
        "examples": "textbook examples with real-world connections",
        "assumed_knowledge": "introductory course knowledge",
    },
    "postgraduate": {
        "language": "precise terminology, nuanced",
        "audience_language": "precise terminology, nuanced",
        "explanation_depth": "assumptions, evidence, trade-offs, limitations",
        "jargon_level": "high — assumed familiarity with standard terms",
        "examples": "research findings, edge cases, comparative analysis",
        "assumed_knowledge": "strong disciplinary foundation",
    },
    "professional": {
        "language": "precise, practitioner-oriented",
        "audience_language": "precise, practitioner-oriented",
        "explanation_depth": "methods, evidence, limitations, current practices",
        "jargon_level": "domain-native — minimal definition needed",
        "examples": "industry cases, metrics, decision frameworks",
        "assumed_knowledge": "professional working knowledge",
    },
    "research": {
        "language": "precise, methodological",
        "audience_language": "precise, methodological",
        "explanation_depth": "assumptions, methodology, threats to validity, reproducibility",
        "jargon_level": "full technical vocabulary",
        "examples": "experimental results, ablation studies, benchmarks",
        "assumed_knowledge": "active researcher",
    },
}


def get_domain_profile(domain: str) -> Dict[str, Any]:
    """Get writing profile for a domain. Falls back to 'general' for unknown domains."""
    return DOMAIN_WRITING_PROFILES.get(domain.lower(), DOMAIN_WRITING_PROFILES["general"])


def get_audience_profile(education_level: str) -> Dict[str, Any]:
    """Get audience depth profile. Maps common audience strings to profiles."""
    level = education_level.lower().strip()
    # Map common audience values to profile keys
    level_map = {
        "university": "undergraduate",
        "college": "undergraduate",
        "high_school": "school",
        "secondary": "school",
        "primary": "school",
        "graduate": "postgraduate",
        "masters": "postgraduate",
        "phd": "research",
        "expert": "professional",
        "beginner": "school",
        "intermediate": "undergraduate",
        "advanced": "postgraduate",
        "research_professional": "professional",
        "research/professional": "professional",
    }
    profile_key = level_map.get(level, level)
    return AUDIENCE_DEPTH_PROFILES.get(profile_key, AUDIENCE_DEPTH_PROFILES["undergraduate"])


def get_reasoning_dimensions(intent: SlideIntent) -> List[str]:
    """Get relevant reasoning dimensions for a slide intent."""
    return INTENT_REASONING_DIMENSIONS.get(intent.value, ["WHAT", "HOW"])


def build_content_generation_context(
    domain: str,
    subdomain: str,
    intent: SlideIntent,
    education_level: str,
    topic: str,
    topic_intelligence: Optional[Dict[str, Any]] = None,
    source_context: str = "",
) -> Dict[str, Any]:
    """Build the full context dict for content generation.
    
    Priority order:
    1. Specific source/context
    2. Topic intelligence
    3. Subdomain
    4. Domain
    5. General fallback
    """
    domain_profile = get_domain_profile(domain)
    audience_profile = get_audience_profile(education_level)
    reasoning_dims = get_reasoning_dimensions(intent)

    context = {
        "domain": domain,
        "subdomain": subdomain,
        "topic": topic,
        "intent": intent.value,
        "writing_style": domain_profile["writing_style"],
        "emphasis": domain_profile["emphasis"],
        "preferred_structures": domain_profile["preferred_structures"],
        "avoid": domain_profile["avoid"],
        "example_types": domain_profile["example_types"],
        "audience_language": audience_profile["language"],
        "explanation_depth": audience_profile["explanation_depth"],
        "jargon_level": audience_profile["jargon_level"],
        "assumed_knowledge": audience_profile["assumed_knowledge"],
        "reasoning_dimensions": reasoning_dims,
    }

    # Source context takes highest priority
    if source_context:
        context["source_context"] = source_context
        context["content_origin_hint"] = "source_document"

    # Enrich from topic intelligence
    if topic_intelligence:
        ti_concepts = []
        for c in topic_intelligence.get("canonical_concepts", []):
            if isinstance(c, dict):
                ti_concepts.append(c.get("term", ""))
            elif isinstance(c, str):
                ti_concepts.append(c)
        context["canonical_concepts"] = [c for c in ti_concepts if c]
        context["processes"] = topic_intelligence.get("processes", [])
        context["misconceptions"] = topic_intelligence.get("misconceptions", [])
        context["comparison_candidates"] = topic_intelligence.get("comparison_candidates", [])
        context["real_world_examples"] = topic_intelligence.get("real_world_examples", [])
        context["formulas"] = topic_intelligence.get("formulas_or_equations", [])
        context["chronology"] = topic_intelligence.get("chronology_if_relevant", [])
        context["cause_effect_pairs"] = topic_intelligence.get("cause_effect_pairs", [])

    return context


# ═══════════════════════════════════════════════════════════════
# Intent-Aware Field Population Rules
# ═══════════════════════════════════════════════════════════════

# Specifies which SlideContent fields are EXPECTED for each intent
# Fields not listed should remain empty/None
INTENT_EXPECTED_FIELDS: Dict[str, List[str]] = {
    SlideIntent.COVER.value: ["title", "subtitle"],
    SlideIntent.HOOK.value: ["title", "primary_takeaway", "speaker_notes"],
    SlideIntent.CONTEXT.value: ["title", "primary_takeaway", "supporting_points", "speaker_notes"],
    SlideIntent.WHY_IT_MATTERS.value: ["title", "primary_takeaway", "supporting_points", "speaker_notes"],
    SlideIntent.AGENDA.value: ["title", "supporting_points", "speaker_notes"],
    SlideIntent.OBJECTIVES.value: ["title", "supporting_points", "speaker_notes"],
    SlideIntent.DEFINITION.value: ["title", "primary_takeaway", "supporting_points", "callout", "speaker_notes"],
    SlideIntent.MENTAL_MODEL.value: ["title", "primary_takeaway", "labels", "speaker_notes"],
    SlideIntent.CONCEPT_EXPLANATION.value: ["title", "primary_takeaway", "supporting_points", "example", "speaker_notes"],
    SlideIntent.SYSTEM_OVERVIEW.value: ["title", "primary_takeaway", "supporting_points", "labels", "speaker_notes"],
    SlideIntent.COMPONENT_BREAKDOWN.value: ["title", "primary_takeaway", "supporting_points", "labels", "speaker_notes"],
    SlideIntent.PROCESS_EXPLANATION.value: ["title", "primary_takeaway", "process_steps", "speaker_notes"],
    SlideIntent.COMPARISON.value: ["title", "primary_takeaway", "comparison_target_a", "comparison_target_b", "comparison_rows", "speaker_notes"],
    SlideIntent.TRADEOFF.value: ["title", "primary_takeaway", "supporting_points", "callout", "speaker_notes"],
    SlideIntent.WORKED_EXAMPLE.value: ["title", "primary_takeaway", "example", "speaker_notes"],
    SlideIntent.CODE_EXAMPLE.value: ["title", "primary_takeaway", "code", "code_language", "speaker_notes"],
    SlideIntent.FORMULA_EXPLANATION.value: ["title", "primary_takeaway", "formula", "formula_symbol_meanings", "example", "speaker_notes"],
    SlideIntent.CASE_STUDY.value: ["title", "primary_takeaway", "supporting_points", "example", "speaker_notes"],
    SlideIntent.REAL_WORLD_APPLICATION.value: ["title", "primary_takeaway", "supporting_points", "example", "speaker_notes"],
    SlideIntent.DATA_INSIGHT.value: ["title", "primary_takeaway", "data_points", "callout", "speaker_notes"],
    SlideIntent.MISCONCEPTION.value: ["title", "primary_takeaway", "misconception", "speaker_notes"],
    SlideIntent.COMMON_MISTAKES.value: ["title", "primary_takeaway", "supporting_points", "callout", "speaker_notes"],
    SlideIntent.BEST_PRACTICES.value: ["title", "primary_takeaway", "supporting_points", "speaker_notes"],
    SlideIntent.DIAGNOSTIC.value: ["title", "primary_takeaway", "supporting_points", "speaker_notes"],
    SlideIntent.KNOWLEDGE_CHECK.value: ["title", "primary_takeaway", "example", "speaker_notes"],
    SlideIntent.SUMMARY.value: ["title", "primary_takeaway", "supporting_points", "speaker_notes"],
    SlideIntent.REFERENCES.value: ["title", "supporting_points"],
    SlideIntent.Q_AND_A.value: ["title", "speaker_notes"],
}


def get_expected_fields(intent: SlideIntent) -> List[str]:
    """Return the list of SlideContent fields expected for a given intent.
    Empty fields for non-listed keys are correct."""
    return INTENT_EXPECTED_FIELDS.get(intent.value, ["title", "primary_takeaway", "supporting_points", "speaker_notes"])


def resolve_slide_concept_packet(
    blueprint: SlideBlueprint,
    brief: PresentationBrief,
    topic_intelligence: Optional[Any] = None,
    deck_memory: Optional[Any] = None,
    slide_no: int = 1,
    total_slides: int = 12,
    source_context: str = "",
) -> SlideConceptPacket:
    """
    Resolve a SlideConceptPacket for the given slide blueprint (§1 & §4).
    
    Priority order (§2):
    1. verified source context
    2. existing grounded TopicIntelligencePack
    3. reliable deterministic structural inference from blueprint
    4. unresolved / empty (NEVER fabricated fake facts)
    """
    topic = brief.canonical_topic or brief.topic
    domain = brief.domain
    subdomain = brief.subdomain or ""

    # Convert topic_intelligence to dict or model if needed
    ti = topic_intelligence.model_dump() if hasattr(topic_intelligence, "model_dump") else (topic_intelligence or {})
    if not isinstance(ti, dict):
        ti = {}

    # 1. Primary Concept Resolution
    primary_concept = ""
    source_terms: List[str] = []
    if isinstance(source_context, dict) and "key_terms" in source_context:
        source_terms = [t for t in source_context["key_terms"] if isinstance(t, str)]
    
    bp_concepts = [c for c in (blueprint.canonical_concepts or []) if c]
    
    ti_canonical = ti.get("canonical_concepts", [])
    ti_concept_terms = []
    for c in ti_canonical:
        if isinstance(c, dict):
            term = c.get("term", "")
            if term:
                ti_concept_terms.append(term)
        elif isinstance(c, str) and c:
            ti_concept_terms.append(c)

    candidates_pool = source_terms + bp_concepts + ti_concept_terms
    # Concept selection respecting deck memory progression
    for c in candidates_pool:
        if deck_memory and hasattr(deck_memory, "is_concept_already_introduced"):
            if not deck_memory.is_concept_already_introduced(c):
                primary_concept = c
                deck_memory.register_concept(c)
                break
        elif not primary_concept:
            primary_concept = c
            break

    if not primary_concept:
        if bp_concepts:
            primary_concept = bp_concepts[0]
        else:
            msg = blueprint.primary_message or ""
            if ":" in msg:
                primary_concept = msg.split(":")[0].strip()
            elif " - " in msg:
                primary_concept = msg.split(" - ")[0].strip()
            elif blueprint.semantic_role and hasattr(blueprint.semantic_role, "value"):
                primary_concept = f"{topic}: {blueprint.semantic_role.value.replace('_', ' ').title()}"
            else:
                primary_concept = topic

    if deck_memory and hasattr(deck_memory, "register_concept"):
        deck_memory.register_concept(primary_concept)

    # 2. Supporting Concepts
    supporting_concepts: List[str] = []
    for c in candidates_pool:
        if c != primary_concept and c not in supporting_concepts:
            supporting_concepts.append(c)
            if len(supporting_concepts) >= 4:
                break

    if not supporting_concepts:
        for st in ti.get("core_subtopics", []):
            term = st.split(":")[0].strip() if ":" in st else st
            if term != primary_concept and term not in supporting_concepts:
                supporting_concepts.append(term)
                if len(supporting_concepts) >= 3:
                    break

    # 3. Process Stages (if process-related)
    process_stages: List[str] = []
    if blueprint.intent in (SlideIntent.PROCESS_EXPLANATION, SlideIntent.SYSTEM_OVERVIEW):
        ti_processes = ti.get("processes", []) or ti.get("process_stages", [])
        if ti_processes:
            for p in ti_processes:
                if isinstance(p, str) and p not in process_stages:
                    process_stages.append(p)

    # 4. Cause-Effect Pairs
    cause_effect_pairs: List[Dict[str, str]] = []
    for ce in ti.get("cause_effect_pairs", []):
        if isinstance(ce, dict) and ce.get("cause") and ce.get("effect"):
            cause_effect_pairs.append(ce)

    # 5. Relationships from Intelligence or Source - Specialized & Deduplicated
    relationships: List[str] = []
    scored_pairs = []
    msg_words = set(w.lower() for w in re.findall(r"\w+", blueprint.primary_message or "") if len(w) > 3)
    bp_canon_lower = set(c.lower() for c in (blueprint.canonical_concepts or []) if c)
    concept_lower = primary_concept.lower()
    
    for ce in cause_effect_pairs:
        cause = ce['cause'].strip()
        effect = ce['effect'].strip()
        eff_words = effect.split()
        first_eff = eff_words[0].lower() if eff_words else ""
        finite_verbs = {
            "prevents", "creates", "ensures", "causes", "generates", "initiates",
            "drives", "produces", "establishes", "requires", "allows", "enables",
            "regulates", "modulates", "inhibits", "activates", "catalyzes", "governs",
            "applies", "relies", "functions", "balances", "couples", "transforms", "converts"
        }
        c_words = set(w.lower() for w in re.findall(r"\w+", cause.lower()))
        c_has_verb = any(w in finite_verbs for w in c_words)
        if first_eff in finite_verbs:
            if c_has_verb:
                rel_str = f"When {cause[0].lower() + cause[1:]}, it {first_eff} {' '.join(eff_words[1:])}"
            else:
                rel_str = f"{cause} {first_eff} {' '.join(eff_words[1:])}"
        else:
            if c_has_verb:
                rel_str = f"When {cause[0].lower() + cause[1:]}, it leads to {effect}"
            else:
                rel_str = f"{cause} leads to {effect}"
        c_text = f"{ce['cause']} {ce['effect']}".lower()
        rel_words = set(w.lower() for w in re.findall(r"\w+", c_text) if len(w) > 3)
        
        score = 0.0
        if concept_lower in c_text:
            score += 10.0
        for bc in bp_canon_lower:
            if bc in c_text:
                score += 8.0
        overlap = msg_words & rel_words
        score += len(overlap) * 4.0
        for sc in supporting_concepts[:2]:
            if sc.lower() in c_text:
                score += 2.0
                
        is_explained = False
        if deck_memory:
            if hasattr(deck_memory, "is_relationship_already_explained"):
                is_explained = deck_memory.is_relationship_already_explained(rel_str)
            elif hasattr(deck_memory, "is_relationship_already_used"):
                is_explained = deck_memory.is_relationship_already_used(rel_str)
                
        scored_pairs.append({
            "ce": ce,
            "rel_str": rel_str,
            "score": score,
            "is_explained": is_explained,
        })

    # Sort: prioritize unexplained relationships, then highest relevance score
    scored_pairs.sort(key=lambda x: (not x["is_explained"], x["score"]), reverse=True)
    
    if scored_pairs:
        for item in scored_pairs[:2]:
            relationships.append(item["rel_str"])
        # Register ONLY the primary selected relationship in deck memory
        if deck_memory and hasattr(deck_memory, "register_relationship"):
            deck_memory.register_relationship(scored_pairs[0]["rel_str"])

    # 6. Comparison Dimensions
    comparison_dimensions: List[str] = []
    if blueprint.intent in (SlideIntent.COMPARISON, SlideIntent.TRADEOFF):
        for comp in ti.get("comparison_candidates", []):
            if isinstance(comp, dict):
                axis = comp.get("comparison_axis", "") or comp.get("dimension", "")
                if axis and axis not in comparison_dimensions:
                    comparison_dimensions.append(axis)

    # 7. Example Candidates
    example_candidates: List[str] = []
    ex_sources = ti.get("real_world_examples", []) + ti.get("case_studies", []) + ti.get("applications", []) + ti.get("examples", [])
    for ex in ex_sources:
        if isinstance(ex, str) and ex:
            if deck_memory and hasattr(deck_memory, "is_example_already_used") and deck_memory.is_example_already_used(ex):
                continue
            example_candidates.append(ex)

    # 8. Misconceptions
    misconceptions: List[Dict[str, str]] = []
    for m in ti.get("misconceptions", []):
        if isinstance(m, dict) and m.get("myth") and m.get("reality"):
            misconceptions.append(m)

    # 9. Source-Grounded Facts (from document/RAG if provided)
    source_grounded_facts: List[str] = []
    if source_context:
        src_text = ""
        if isinstance(source_context, dict):
            if "claims" in source_context and isinstance(source_context["claims"], list):
                source_grounded_facts.extend([str(c) for c in source_context["claims"][:5]])
            src_text = source_context.get("text", "") or " ".join(str(v) for v in source_context.values() if isinstance(v, str))
        elif isinstance(source_context, str):
            src_text = source_context
        if src_text and not source_grounded_facts:
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', src_text) if len(s.strip().split()) >= 6]
            source_grounded_facts = sentences[:5]

    # 10. Contextual Vocabulary Leakage Risks for this slide
    leakage_risks = check_contextual_vocabulary_leakage(
        text=f"{primary_concept} {' '.join(supporting_concepts)}",
        domain=domain,
        subdomain=subdomain,
        topic=topic,
    )

    # 11. Domain Native Terms (from profile keywords)
    profile = get_domain_profile(domain)
    domain_native_terms = list(profile.get("emphasis", []))[:6]

    return SlideConceptPacket(
        primary_concept=primary_concept,
        supporting_concepts=supporting_concepts,
        relationships=relationships,
        required_terms=candidates_pool[:5],
        domain_native_terms=domain_native_terms,
        process_stages=process_stages,
        cause_effect_pairs=cause_effect_pairs,
        comparison_dimensions=comparison_dimensions,
        example_candidates=example_candidates,
        misconceptions=misconceptions,
        evidence_requirements=[],
        source_grounded_facts=source_grounded_facts,
        contextual_leakage_risks=leakage_risks,
    )


def build_domain_writing_prompt(
    context: Dict[str, Any],
    blueprint_message: str = "",
    semantic_role: str = "",
    slide_number: int = 1,
    total_slides: int = 12,
    previous_slide_summary: str = "",
    next_slide_intent: str = "",
    packet: Optional[SlideConceptPacket] = None,
) -> str:
    """Build a domain-aware, audience-adapted content generation prompt for the LLM.
    
    This prompt instructs the model to generate structured SlideContent
    in the appropriate domain writing style and audience depth.
    """
    domain = context.get("domain", "general")
    subdomain = context.get("subdomain", "")
    topic = context.get("topic", "")
    intent = context.get("intent", "concept_explanation")
    dims = context.get("reasoning_dimensions", [])
    emphasis = context.get("emphasis", [])
    avoid = context.get("avoid", [])
    writing_style = context.get("writing_style", "expository")
    audience_lang = context.get("audience_language", "accessible")
    explanation_depth = context.get("explanation_depth", "moderate")
    jargon_level = context.get("jargon_level", "moderate")
    example_types = context.get("example_types", [])

    educator_persona = get_domain_educator_persona(domain, subdomain)

    prompt_parts = [
        f"ROLE: You are an expert {educator_persona}.",
        f"Generate slide content for slide {slide_number}/{total_slides}.",
        f"Topic: {topic}",
        f"Domain: {domain}" + (f" / {subdomain}" if subdomain else ""),
        f"Intent: {intent}",
        f"Semantic Role: {semantic_role}" if semantic_role else "",
        f"Primary Message: {blueprint_message}" if blueprint_message else "",
        "",
        "CRITICAL CONTENT QUALITY DIRECTIVES:",
        "1. NO TOPIC-SUBSTITUTION PROSE: Never write generic filler where replacing the topic name leaves the sentence valid (e.g., 'X defines how X operates', 'When explaining X', 'The X operational pipeline', 'X plays a crucial role').",
        "2. PRIMARY TAKEAWAY MUST CONTAIN DOMAIN KNOWLEDGE: The dominant message must assert a concrete, topic-specific relationship, mechanism, constraint, cause-effect, or interpretation.",
        "3. SUPPORTING POINTS MUST BE SEMANTICALLY DISTINCT: Each point must contribute a unique role (initiating condition, mechanism, constraint, evidence, consequence). Never paraphrase the takeaway.",
        "4. DOMAIN-NATIVE VOCABULARY: Use language natural to experts in this discipline. Avoid cross-domain terminology leakage.",
        "",
        f"WRITING STYLE: {writing_style}",
        f"EMPHASIS: {', '.join(emphasis)}",
        f"AVOID: {', '.join(avoid)}",
        f"AUDIENCE LANGUAGE: {audience_lang}",
        f"EXPLANATION DEPTH: {explanation_depth}",
        f"JARGON LEVEL: {jargon_level}",
        f"REASONING DIMENSIONS FOR THIS INTENT: {', '.join(dims)}",
        f"PREFERRED EXAMPLE TYPES: {', '.join(example_types)}",
    ]

    # Add concept packet if provided
    if packet:
        prompt_parts.append(f"\nSLIDE CONCEPT PACKET:")
        if packet.primary_concept:
            prompt_parts.append(f"  Primary Concept: {packet.primary_concept}")
        if packet.supporting_concepts:
            prompt_parts.append(f"  Supporting Concepts: {', '.join(packet.supporting_concepts)}")
        if packet.relationships:
            prompt_parts.append(f"  Grounded Relationships: {'; '.join(packet.relationships)}")
        if packet.domain_native_terms:
            prompt_parts.append(f"  Domain-Native Terms: {', '.join(packet.domain_native_terms)}")
        if packet.source_grounded_facts:
            prompt_parts.append(f"  Source-Grounded Facts: {'; '.join(packet.source_grounded_facts[:3])}")
        if packet.contextual_leakage_risks:
            prompt_parts.append(f"  Vocabulary Leakage Risks to Avoid: {', '.join(packet.contextual_leakage_risks)}")

    # Add topic intelligence context
    if context.get("canonical_concepts"):
        prompt_parts.append(f"\nCANONICAL CONCEPTS: {', '.join(context['canonical_concepts'][:8])}")
    if context.get("processes"):
        prompt_parts.append(f"KEY PROCESSES: {', '.join(context['processes'][:5])}")
    if context.get("misconceptions"):
        myths = [m.get("myth", "") if isinstance(m, dict) else str(m) for m in context["misconceptions"][:3]]
        prompt_parts.append(f"KNOWN MISCONCEPTIONS: {'; '.join(myths)}")
    if context.get("comparison_candidates"):
        comps = context["comparison_candidates"][:3]
        comp_strs = [f"{c.get('item_a','')} vs {c.get('item_b','')}" if isinstance(c, dict) else str(c) for c in comps]
        prompt_parts.append(f"COMPARISON CANDIDATES: {'; '.join(comp_strs)}")
    if context.get("formulas"):
        prompt_parts.append(f"RELEVANT FORMULAS: {'; '.join(context['formulas'][:3])}")
    if context.get("chronology"):
        prompt_parts.append(f"CHRONOLOGY: {'; '.join(context['chronology'][:5])}")

    # Source context
    if context.get("source_context"):
        prompt_parts.append(f"\nSOURCE MATERIAL:\n{context['source_context'][:2000]}")

    # Narrative continuity
    if previous_slide_summary:
        prompt_parts.append(f"\nPREVIOUS SLIDE: {previous_slide_summary}")
    if next_slide_intent:
        prompt_parts.append(f"NEXT SLIDE INTENT: {next_slide_intent}")

    return "\n".join(p for p in prompt_parts if p)
