"""
Content Quality Auditor V2 & Targeted Repair (Phase 2)
========================================================
Evaluates 12 scoring dimensions (0–100) for each slide.
Enforces hard fails and soft fails.
Performs field-level targeted repair without full deck regeneration.

QUALITY GATE MUST NOT BECOME SCORE GAMING:
- Hard factual/evidence failures override aggregate score.
- A slide with score=94 but an unsupported numeric claim still FAILS.
- Score is diagnostic, not permission to ignore hard defects.

TOPIC SPECIFICITY measures MEANING, not keyword density.
A slide repeating the topic name five times is NOT specific.
"""
import re
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from .schemas import (
    SlideIntent, ContentDensity, ClaimType, ClaimVerificationStatus,
    ClaimEvidence, ContentQualityScores, SlideContent,
    ContentOrigin, SemanticStatus, SemanticFailureReason, SlideConceptPacket,
)
from .content_budget_engine import count_words
from .claim_evidence_engine import (
    detect_numeric_claims, detect_fabricated_stat_phrases,
    classify_claim,
)

logger = logging.getLogger("teachgenie.presentation.content_quality_auditor")


# ═══════════════════════════════════════════════════════════════
# Expanded Banned Phrase List (Phase 2)
# ═══════════════════════════════════════════════════════════════

BANNED_PHRASES_PHASE2 = [
    # Phase 1 originals
    "key operational insight",
    "supporting structural mechanism",
    "lorem", "tbd", "placeholder",
    "content goes here",
    "overview of the topic",
    "in this slide we will",
    "this is important",
    "understanding x matters",
    "key educational insight",
    "synthesized understanding",
    "core takeaway summary",
    "key takeaway context",
    "core component analysis",
    # Phase 2 additions
    "in today's rapidly evolving world",
    "plays a crucial role",
    "it is important to note",
    "offers numerous benefits",
    "powerful and flexible",
    "robust and scalable",
    "revolutionary",
    "game-changing",
    "seamless",
    "unlocking potential",
    "key operational insight",
    "supporting mechanism",
    "let's delve into",
    "it goes without saying",
    "needless to say",
    "at the end of the day",
    "the fact of the matter is",
    "it is worth noting",
    "a paradigm shift",
    "leverage synergies",
    "think outside the box",
    "cutting-edge solution",
    "best-in-class",
    "world-class",
    "holistic approach",
    "deep dive into",
]

# Universal generic prefixes rejected as content-free repair wrappers
CONTENT_FREE_REPAIR_WRAPPERS = [
    "this framework establishes that",
    "the core concept is",
    "this demonstrates that",
    "this process highlights",
    "understanding this helps",
    "systematic execution of",
    "rigorous implementation of",
]


def detect_incomplete_title(title: str) -> Tuple[bool, str]:
    """Detect whether a title terminates in an incomplete phrase, clause, or dangling token."""
    if not title or not title.strip():
        return True, "Title is empty"
    t = title.strip().rstrip(".,:;- ")
    if t.endswith("...") or t.endswith("…"):
        return True, "Title terminates in ellipsis"
    words = t.split()
    if len(words) < 2:
        return False, ""
    last_word = words[-1].lower()
    last_two = " ".join(words[-2:]).lower()
    
    dangling_singles = {
        "into", "in", "to", "of", "for", "with", "by", "from", "through", "between",
        "under", "over", "about", "towards", "against", "upon", "a", "an", "the",
        "this", "that", "these", "those", "which", "and", "or", "but", "nor", "so",
        "yet", "because", "although", "since", "while", "where", "who", "whom",
        "whose", "fuels", "drives", "layers", "is", "are", "was", "were", "has", "have",
        "leads"
    }
    dangling_pairs = {
        "into a", "into the", "in a", "in the", "to a", "to the", "of a", "of the",
        "for a", "for the", "with a", "with the", "by a", "by the", "from a", "from the",
        "and a", "and the", "that fuels", "that drives", "that leads", "that creates",
        "that enables", "that supports", "which causes", "which leads", "leads to"
    }
    if last_two in dangling_pairs:
        return True, f"Title terminates in dangling phrase '{last_two}'"
    if last_word in dangling_singles:
        return True, f"Title terminates in dangling word '{last_word}'"
    return False, ""


def detect_ungrammatical_statement(text: str) -> Tuple[bool, str]:
    """Detect obvious ungrammatical statement constructions such as 'leads to establishes'."""
    if not text:
        return False, ""
    tl = text.lower()
    patterns = [
        (r"\bleads\s+to\s+(establishes|creates|ensures|causes|generates|initiates|drives|produces)\b", "Double finite verb after 'leads to'"),
        (r"\bresults\s+in\s+(establishes|creates|ensures|causes|generates|initiates|drives|produces)\b", "Double finite verb after 'results in'"),
        (r"\bcauses\s+to\s+(establishes|creates|ensures)\b", "Ungrammatical verb syntax after 'causes to'"),
    ]
    for pat, reason in patterns:
        if re.search(pat, tl):
            return True, reason
    return False, ""


def sanitize_and_complete_title(title: str, topic: str = "", fallback_concept: str = "") -> str:
    """Sanitize and ensure a title terminates grammatically and semantically completely."""
    if not title or len(title.strip()) < 3:
        return f"{fallback_concept or topic}: Overview"
    
    t = title.strip().rstrip(".,:;- ")
    while t.endswith("...") or t.endswith("…"):
        t = t.rstrip(".… ").strip()
    
    changed = True
    while changed and len(t.split()) > 2:
        changed = False
        words = t.split()
        last_word = words[-1].lower()
        last_two = " ".join(words[-2:]).lower() if len(words) >= 2 else ""
        
        dangling_pairs = {
            "into a", "into the", "in a", "in the", "to a", "to the", "of a", "of the",
            "for a", "for the", "with a", "with the", "by a", "by the", "from a", "from the",
            "and a", "and the", "that fuels", "that drives", "that leads", "that creates",
            "that enables", "that supports", "which causes", "which leads", "leads to"
        }
        dangling_singles = {
            "into", "in", "to", "of", "for", "with", "by", "from", "through", "between",
            "under", "over", "about", "towards", "against", "upon", "a", "an", "the",
            "this", "that", "these", "those", "which", "and", "or", "but", "nor", "so",
            "yet", "because", "although", "since", "while", "where", "who", "whom",
            "whose", "fuels", "drives", "layers", "is", "are", "was", "were", "has", "have",
            "leads"
        }
        
        if last_two in dangling_pairs:
            t = " ".join(words[:-2]).strip().rstrip(".,:;- ")
            changed = True
        elif last_word in dangling_singles:
            t = " ".join(words[:-1]).strip().rstrip(".,:;- ")
            changed = True

    if len(t.split()) < 3:
        if fallback_concept:
            t = f"{fallback_concept}: Core Principles"
        elif topic:
            t = f"{topic}: Core Mechanism and Architecture"
    
    if t:
        t = t[0].upper() + t[1:]
    return t


def contains_banned_phrase(text: str) -> Tuple[bool, List[str]]:
    """Check if text contains any banned filler phrases.
    Returns (has_banned, list_of_found_phrases)."""
    text_lower = text.lower().strip()
    found = []
    for phrase in BANNED_PHRASES_PHASE2:
        if phrase in text_lower:
            found.append(phrase)
    return len(found) > 0, found


# ═══════════════════════════════════════════════════════════════
# Semantic Genericity & Topic-Substitution Detection (§1, §11, §13)
# ═══════════════════════════════════════════════════════════════

TOPIC_SUBSTITUTION_PATTERNS = [
    r"\b{t}\s+defines\s+how\s+{t}\s+operates\b",
    r"\b{t}\s+is\s+important\s+because\b",
    r"\bwhen\s+explaining\s+{t}\b",
    r"\b{t}\s+consists\s+of\s+several\s+key\s+components\b",
    r"\b{t}\s+plays\s+a\s+(crucial|vital|key|central)\s+role\b",
    r"\bthe\s+{t}\s+operational\s+pipeline\b",
    r"\bunderstanding\s+{t}\s+(helps|requires|is\s+essential)\b",
    r"\bconsider\s+how\s+{t}\s+affects\s+outcomes\b",
    r"\b{t}\s+operates\s+through\s+interconnected\s+mechanisms\b",
    r"\b{t}\s+provides\s+foundational\s+principles\s+in\s+this\s+domain\b",
    r"\bsystematic\s+execution\s+of\b",
    r"\bestablishes\s+structural\s+stability\s+and\s+predictable\s+operational\s+outcomes\b",
    r"\bleads\s+to\s+establishes\b",
    r"\brigorous\s+implementation\s+of\b",
    r"\bensures\s+systemic\s+stability\s+and\s+predictable\s+performance\b",
]


def detect_genericity(
    content_dict: Dict[str, Any],
    topic: str,
    domain: str = "general",
    subdomain: str = "",
) -> Tuple[int, List[str]]:
    """
    Measure semantic genericity and topic-substitution behavior (§1, §11, §13).
    
    Answers the core question:
    'What does this tell me about THIS topic that would not remain true if the topic name were replaced?'
    Returns (genericity_penalty, issues_found).
    """
    issues: List[str] = []
    penalty = 0

    takeaway = content_dict.get("primary_takeaway", "")
    bullets = content_dict.get("supporting_points", [])
    steps = content_dict.get("process_steps", [])
    all_sentences = [takeaway] + bullets + steps
    combined = " ".join(s for s in all_sentences if s).lower()

    if not combined:
        return 0, []

    # 1. Topic-substitution pattern detection
    topic_clean = re.sub(r"[^\w\s]", "", topic).strip().lower()
    topic_words = [w for w in topic_clean.split() if len(w) >= 4]
    check_terms = [re.escape(topic_clean)] + [re.escape(w) for w in topic_words]

    for sent in all_sentences:
        sent_lower = sent.lower()
        for pat_template in TOPIC_SUBSTITUTION_PATTERNS:
            for term in check_terms:
                pat = pat_template.format(t=term)
                if re.search(pat, sent_lower):
                    issue = f"TOPIC_SUBSTITUTION_PROSE: '{sent[:60]}...'"
                    if issue not in issues:
                        issues.append(issue)
                        penalty += 35

    # 2. Check contextual vocabulary leakage (§3)
    from .domain_content_writer import check_contextual_vocabulary_leakage
    leakages = check_contextual_vocabulary_leakage(combined, domain, subdomain, topic)
    for lk in leakages:
        issue = f"VOCABULARY_LEAKAGE: '{lk}' inappropriate for {domain}"
        if issue not in issues:
            issues.append(issue)
            penalty += 20

    # 3. Topic name repetition without substantive sub-entities
    if topic_clean:
        topic_count = combined.count(topic_clean)
        words_count = len(combined.split())
        if words_count > 0:
            density = topic_count / words_count
            if density > 0.08 or topic_count > 4:
                issues.append(f"EXCESSIVE_TOPIC_NAME_REPETITION: {topic_count} mentions")
                penalty += 15

    # 4. Empty generic predicates and known fallback boilerplate
    generic_verb_phrases = [
        "enables predictable interaction between subsystem components",
        "provides the baseline model necessary to reason",
        "addresses core domain challenges",
        "governing rules",
        "system reliability",
        "variable operating constraints",
        "operational mechanisms",
        "measurable stability",
        "constraint verification",
        "modular expansion",
        "backward invariants",
        "core functional state",
        "theoretical predictions",
        "boundary parameters",
        "error budgets",
        "primary approach",
        "alternative model",
        "clarifies how governing rules ensure system reliability",
        "deliver measurable stability across varied workloads",
        "ensures compliance with core performance criteria",
        "support modular expansion without breaking",
    ]
    for gvp in generic_verb_phrases:
        if gvp in combined:
            issues.append(f"GENERIC_EMPTY_PREDICATE: '{gvp}'")
            penalty += 55  # Severe penalty for known bad template


    return min(100, penalty), issues


# ═══════════════════════════════════════════════════════════════
# Topic Specificity Scoring — Measures MEANING, Not Keyword Count
# ═══════════════════════════════════════════════════════════════

def score_topic_specificity(
    content_dict: Dict[str, Any],
    topic: str,
    domain: str,
    canonical_concepts: Optional[List[str]] = None,
    subdomain: str = "",
    intent: Optional[SlideIntent] = None,
) -> int:
    """Score content for topic specificity (0–100).
    
    Rewards:
    - Grounded concepts from topic intelligence & blueprint
    - Topic-specific mechanisms, entities, relationships
    - Concrete domain-appropriate examples & boundary constraints
    
    Penalizes:
    - Topic-substitution generic filler
    - Reusable sentence structures
    - Contextual vocabulary leakage
    """
    canonical_concepts = canonical_concepts or []
    
    texts = [
        content_dict.get("primary_takeaway", ""),
        content_dict.get("example", ""),
        content_dict.get("callout", ""),
    ]
    texts.extend(content_dict.get("supporting_points", []))
    texts.extend(content_dict.get("process_steps", []))
    combined = " ".join(t for t in texts if t).lower()
    
    if intent == SlideIntent.COVER:
        topic_lower = topic.lower()
        if topic_lower in combined or any(w in combined for w in topic_lower.split() if len(w) >= 4):
            return 94
        return 88

    if not combined or len(combined.split()) < 5:
        return 30
    
    score = 75  # Solid structured baseline for content
    
    # REWARD: Canonical concepts, topic terms, and domain-native emphasis (up to +20)
    from .domain_content_writer import get_domain_profile
    profile = get_domain_profile(domain)
    domain_emphasis = [t.lower() for t in profile.get("emphasis", [])]
    topic_words = [w.lower() for w in re.sub(r'[^\w\s]', '', topic).split() if len(w) >= 4]

    term_matches = sum(1 for c in canonical_concepts if c.lower() in combined)
    topic_matches = sum(1 for tw in topic_words if tw in combined)
    domain_matches = sum(1 for de in domain_emphasis if de in combined)
    total_concept_hits = term_matches + topic_matches + domain_matches
    score += min(20, total_concept_hits * 5)
    
    # REWARD: Domain-native mechanisms & relationship verbs (+10 max)
    relationship_verbs = [
        "converts", "transforms", "produces", "catalyzes", "inhibits",
        "triggers", "separates", "combines", "regulates", "activates",
        "prevents", "enables", "requires", "generates", "consumes",
        "couples", "synthesizes", "stabilizes", "constrains", "governs",
        "delegates", "offloads", "executes", "dispatches", "allocates",
        "binds", "coordinates", "drives", "dissipates", "equilibrates",
    ]
    rel_matches = sum(1 for v in relationship_verbs if v in combined)
    score += min(10, rel_matches * 4)
    
    # REWARD: Specific entities, numbers with context, or proper nouns (+5)
    has_specific_entity = bool(re.search(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', " ".join(t for t in texts if t)))
    if has_specific_entity:
        score += 5
    
    # PENALIZE: Genericity penalty (§13)
    gen_penalty, _ = detect_genericity(content_dict, topic, domain, subdomain)
    score -= gen_penalty
    
    return max(0, min(100, score))


# ═══════════════════════════════════════════════════════════════
# Content Quality Scoring — 12 Dimensions
# ═══════════════════════════════════════════════════════════════

def score_content_correctness(
    content_dict: Dict[str, Any],
    claims: Optional[List[ClaimEvidence]] = None,
    intent: Optional[SlideIntent] = None,
) -> int:
    """Score content correctness (0–100).
    Combines source agreement, claim verification status, and structural invariants.
    An LLM does NOT self-certify its own correctness."""
    if intent == SlideIntent.COVER:
        return 95

    score = 95  # Baseline for grounded slide content
    claims = claims or []
    
    # Deduct for unverified high-risk claims
    for claim in claims:
        if claim.claim_type in (ClaimType.NUMERIC_CLAIM, ClaimType.RESEARCH_FINDING):
            if claim.verification_status == ClaimVerificationStatus.SOURCE_PENDING:
                score -= 15
            elif claim.verification_status == ClaimVerificationStatus.UNVERIFIED_REMOVED:
                score -= 5  # Removed is better than pending
    
    # Check for placeholder content
    combined = " ".join([
        content_dict.get("primary_takeaway", ""),
        content_dict.get("example", ""),
    ] + content_dict.get("supporting_points", []))
    
    if "placeholder" in combined.lower() or "tbd" in combined.lower():
        score -= 30
    
    return max(0, min(100, score))


def score_primary_idea_clarity(
    content_dict: Dict[str, Any],
    topic: str = "",
    domain: str = "general",
    intent: Optional[SlideIntent] = None,
    concept_packet: Optional[Any] = None,
) -> int:
    """
    Score whether the slide expresses a clear, meaningful, and grounded proposition (0–100).
    Evaluates topic relevance, relationship validity, intent fit, and semantic grounding.
    Rejects content-free active-verb wrappers and bare noun phrases.
    """
    # 1. Intent-aware exceptions for intentionally fragmentary elements
    if intent in (SlideIntent.COVER, SlideIntent.AGENDA, SlideIntent.Q_AND_A, SlideIntent.REFERENCES):
        title = content_dict.get("title", "").strip()
        if not title:
            return 30
        wc = count_words(title)
        if 2 <= wc <= 12:
            return 90
        elif wc == 1:
            return 80
        else:
            return 78

    takeaway = content_dict.get("primary_takeaway", "").strip()
    if not takeaway:
        return 20  # No primary takeaway = failure for substantive slide

    takeaway_lower = takeaway.lower()

    # 2. Reject content-free generic repair wrappers
    for wrapper in CONTENT_FREE_REPAIR_WRAPPERS:
        if takeaway_lower.startswith(wrapper):
            return 25

    score = 60

    # 3. Length & focus (1 clear, focused sentence/proposition)
    wc = count_words(takeaway)
    if 8 <= wc <= 28:
        score += 15
    elif 5 <= wc <= 36:
        score += 10
    elif wc < 5:
        score -= 20  # Too short to be a substantive teaching proposition
    else:
        score -= 10  # Run-on or overly complex

    # 4. Semantic Proposition & Predicate Check (Active, Passive, Relational, Mathematical)
    words_cleaned = [w.strip(".,;:!?\"'()[]{}").lower() for w in takeaway.split()]
    relational_predicates = {
        "is", "are", "was", "were", "has", "have", "had", "does", "do", "did",
        "can", "could", "will", "would", "should", "may", "might", "shall",
        "uses", "enables", "provides", "requires", "allows", "creates", "generates",
        "processes", "converts", "transforms", "reduces", "increases", "improves",
        "detects", "prevents", "supports", "contains", "produces", "operates",
        "measures", "analyzes", "compares", "separates", "combines", "connects",
        "delivers", "manages", "controls", "defines", "describes", "explains",
        "runs", "works", "makes", "takes", "gives", "helps", "shows", "leads",
        "grows", "moves", "sends", "receives", "stores", "loads", "builds",
        "breaks", "sets", "gets", "puts", "keeps", "turns", "starts", "stops",
        "adds", "removes", "includes", "excludes", "represents", "identifies",
        "achieves", "performs", "executes", "implements", "integrates", "validates",
        "optimizes", "minimizes", "maximizes", "eliminates", "handles", "triggers",
        "ensures", "maintains", "monitors", "tracks", "logs", "reports", "maps",
        "absorbs", "reflects", "emits", "transfers", "releases", "binds",
        "regulates", "activates", "inhibits", "catalyzes", "synthesizes",
        "evolved", "developed", "invented", "discovered", "introduced", "launched",
        "adopted", "replaced", "causes", "drives", "balances", "couples", "encodes",
        "yields", "equals", "modulates", "terminates", "governs", "stabilizes",
        "coordinates", "delegates", "offloads", "advances", "distinguishes",
        "demonstrates", "initiates", "determines", "decreases", "mediates",
        "depends", "establishes", "relates", "characterizes", "arise", "arises",
        "manifest", "manifests", "stems", "originates", "emerges", "occurs",
        "applies", "relies", "functions", "differs", "varies", "contradicts",
        "challenges", "alters", "protects", "protect", "limits", "checks", "filters",
        "demands", "empowers", "expands", "redefines", "evolves", "remedies", "strikes",
    }
    has_relational_predicate = any(v in words_cleaned for v in relational_predicates) or any(
        len(w) > 4 and (w.endswith("izes") or w.endswith("ates") or w.endswith("fies") or w.endswith("cted") or w.endswith("ited") or w.endswith("ated"))
        for w in words_cleaned
    )
    has_passive_phrase = any(
        p in takeaway_lower for p in [
            "is governed by", "is regulated by", "is modulated by", "are mediated by",
            "is characterized by", "is driven by", "is catalyzed by", "is determined by",
            "are coupled to", "is defined as", "is composed of", "results from",
        ]
    )
    has_math_relation = any(sym in takeaway for sym in ["=", "\\approx", "\\equiv", "<=", ">=", "\\le", "\\ge", "\\rightarrow", "\\in", "\\propto", "\\neq", "\\nabla"])

    has_valid_predicate = has_relational_predicate or has_passive_phrase or has_math_relation

    if has_valid_predicate:
        score += 15
    else:
        score -= 25

    # 5. Topic Relevance & Knowledge Communication
    if topic:
        topic_clean = re.sub(r"[^\w\s]", " ", topic).strip().lower()
        topic_words = [w for w in topic_clean.split() if len(w) >= 3]
        cleaned_takeaway = re.sub(r"[^\w\s]", " ", takeaway_lower)
        takeaway_word_set = set(cleaned_takeaway.split())
        has_topic_reference = (
            any(
                w in takeaway_word_set 
                or any(tw.startswith(w) or (len(w) >= 5 and tw.startswith(w[:5])) or (len(tw) >= 5 and w.startswith(tw[:5])) for tw in takeaway_word_set) 
                for w in topic_words
            )
            or (topic_clean in cleaned_takeaway)
        )
        if not has_topic_reference and concept_packet:
            cp_concepts = getattr(concept_packet, "canonical_concepts", []) or []
            cp_terms = [c.get("term", "").lower() if isinstance(c, dict) else str(c).lower() for c in cp_concepts]
            cp_terms.extend([str(c).lower() for c in getattr(concept_packet, "supporting_concepts", []) or []])
            if getattr(concept_packet, "primary_concept", ""):
                cp_terms.append(getattr(concept_packet, "primary_concept").lower())
            if any(term and term in takeaway_lower for term in cp_terms):
                has_topic_reference = True

        if has_topic_reference:
            score += 10
        else:
            score -= 10

    # 6. Semantic Grounding (if concept packet is available)
    if concept_packet:
        cp_concepts = getattr(concept_packet, "canonical_concepts", []) or []
        cp_terms = [c.get("term", "").lower() if isinstance(c, dict) else str(c).lower() for c in cp_concepts]
        cp_terms.extend([str(c).lower() for c in getattr(concept_packet, "supporting_concepts", []) or []])
        if getattr(concept_packet, "primary_concept", ""):
            cp_terms.append(getattr(concept_packet, "primary_concept").lower())

        # Give points if takeaway communicates grounded concepts
        if any(term and term in takeaway_lower for term in cp_terms):
            score += 5

    # 7. Penalize Banned Phrases
    has_banned, _ = contains_banned_phrase(takeaway)
    if has_banned:
        score -= 25

    # 8. Penalize Topic Substitution Prose in takeaway (§1)
    if topic:
        topic_clean = re.sub(r"[^\w\s]", "", topic).strip().lower()
        topic_words = [w for w in topic_clean.split() if len(w) >= 4]
        check_terms = [re.escape(topic_clean)] + [re.escape(w) for w in topic_words]
        for pat_template in TOPIC_SUBSTITUTION_PATTERNS:
            for term in check_terms:
                if re.search(pat_template.format(t=term), takeaway_lower):
                    score -= 35
                    break

    return max(0, min(100, score))



def score_content_depth(
    content_dict: Dict[str, Any],
    intent: SlideIntent,
    reasoning_dimensions: Optional[List[str]] = None,
) -> int:
    """Score depth of content relative to intent and expected reasoning dimensions."""
    if intent == SlideIntent.COVER:
        return 92

    score = 60
    reasoning_dimensions = reasoning_dimensions or []
    
    # Check populated fields
    has_points = bool(content_dict.get("supporting_points"))
    has_example = bool(content_dict.get("example"))
    has_process = bool(content_dict.get("process_steps"))
    has_comparison = bool(content_dict.get("comparison_rows"))
    has_misconception = bool(content_dict.get("misconception"))
    has_data = bool(content_dict.get("data_points"))
    has_code = bool(content_dict.get("code"))
    has_formula = bool(content_dict.get("formula"))
    
    # Reward depth appropriate to intent
    if intent == SlideIntent.WORKED_EXAMPLE and has_example:
        score += 25
    elif intent == SlideIntent.PROCESS_EXPLANATION and has_process:
        score += 25
    elif intent == SlideIntent.COMPARISON and has_comparison:
        score += 25
    elif intent == SlideIntent.MISCONCEPTION and has_misconception:
        score += 25
    elif intent == SlideIntent.DATA_INSIGHT and has_data:
        score += 25
    elif intent == SlideIntent.CODE_EXAMPLE and has_code:
        score += 25
    elif intent == SlideIntent.FORMULA_EXPLANATION and has_formula:
        score += 25
    elif has_points:
        score += 20
    
    # Reward having an example or callout
    if (has_example or content_dict.get("callout")) and intent != SlideIntent.COVER:
        score += 10
    
    # Points count contribution
    points = content_dict.get("supporting_points", [])
    if 2 <= len(points) <= 4:
        score += 10
    elif len(points) > 5:
        score -= 5  # Too many = bullet dumping
    
    return max(0, min(100, score))


def score_audience_fit(
    content_dict: Dict[str, Any],
    education_level: str,
    intent: Optional[SlideIntent] = None,
) -> int:
    """Score whether content matches the target audience level."""
    if intent == SlideIntent.COVER:
        return 95

    score = 78  # High baseline for properly parameterized content
    combined = " ".join([
        content_dict.get("primary_takeaway", ""),
    ] + content_dict.get("supporting_points", []))
    
    combined_lower = combined.lower()
    wc = count_words(combined)
    
    if education_level in ("school", "beginner", "primary", "secondary"):
        complex_indicators = ["epistemological", "ontological", "hermeneutic"]
        if any(ind in combined_lower for ind in complex_indicators):
            score -= 15
        if wc < 90:
            score += 12
    else:
        # University, postgraduate, professional
        if wc >= 25:
            score += 12
        if any(k in combined_lower for k in ["constraint", "trade-off", "mechanism", "boundary", "condition", "protocol", "governs", "stabilizes"]):
            score += 8
    
    return max(0, min(100, score))


def score_slide_nativeness(
    content_dict: Dict[str, Any],
    intent: Optional[SlideIntent] = None,
) -> int:
    """Score whether content is presentation-native vs paragraph dump."""
    if intent == SlideIntent.COVER:
        return 95

    score = 75
    
    points = content_dict.get("supporting_points", [])
    for p in points:
        if count_words(p) > 28:
            score -= 5
    
    # Reward structured elements
    if content_dict.get("process_steps"):
        score += 15
    elif content_dict.get("comparison_rows"):
        score += 15
    elif content_dict.get("misconception"):
        score += 15
    elif 2 <= len(points) <= 4:
        score += 15
    
    if content_dict.get("callout") or content_dict.get("example"):
        score += 5
    
    return max(0, min(100, score))


def score_text_budget_compliance(
    content_dict: Dict[str, Any],
    budget_max: int,
) -> int:
    """Score text budget compliance. 100 = fully compliant, 0 = severe violation."""
    if budget_max <= 0:
        return 100
    
    body_parts = [content_dict.get("primary_takeaway", "")]
    body_parts.extend(content_dict.get("supporting_points", []))
    body_text = " ".join(p for p in body_parts if p)
    body_wc = count_words(body_text)
    
    if body_wc <= budget_max:
        return 100
    
    over_ratio = body_wc / budget_max
    if over_ratio <= 1.1:
        return 90
    elif over_ratio <= 1.25:
        return 70
    elif over_ratio <= 1.5:
        return 50
    else:
        return 20


def score_example_quality(content_dict: Dict[str, Any], topic: str) -> int:
    """Score the quality of examples used."""
    example = content_dict.get("example", "")
    if not example:
        return 80  # Neutral if no example expected
    
    score = 70
    example_lower = example.lower()
    
    # Reward specificity
    if count_words(example) >= 10:
        score += 15
    
    # Reward concrete details
    if re.search(r'\d', example):
        score += 10
    if re.search(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)', example):
        score += 5
    
    # Penalize generic examples
    generic_example_phrases = ["for example, consider", "imagine a scenario where things happen"]
    if any(p in example_lower for p in generic_example_phrases):
        score -= 15
    
    # Penalize banned phrases
    has_banned, _ = contains_banned_phrase(example)
    if has_banned:
        score -= 20
    
    return max(0, min(100, score))


def score_terminology_consistency(
    content_dict: Dict[str, Any],
    canonical_terms: Optional[Dict[str, List[str]]] = None,
) -> int:
    """Score terminology consistency within the slide."""
    if not canonical_terms:
        return 90  # High baseline
    
    score = 100
    combined = " ".join([
        content_dict.get("title", ""),
        content_dict.get("primary_takeaway", ""),
    ] + content_dict.get("supporting_points", []))
    combined_lower = combined.lower()
    
    for canonical, variants in canonical_terms.items():
        for variant in variants:
            if variant.lower() in combined_lower and canonical.lower() not in combined_lower:
                score -= 10
    
    return max(0, min(100, score))


def score_evidence_integrity(claims: Optional[List[ClaimEvidence]] = None) -> int:
    """Score evidence integrity. Hard failure if unsupported high-risk claims exist."""
    if not claims:
        return 100
    
    score = 100
    for claim in claims:
        if claim.source_required:
            if claim.verification_status == ClaimVerificationStatus.SOURCE_PENDING:
                score -= 20
            elif claim.verification_status == ClaimVerificationStatus.UNVERIFIED_REMOVED:
                score -= 5
    
    return max(0, min(100, score))


def score_speaker_note_value(
    content_dict: Dict[str, Any],
    intent: SlideIntent,
) -> int:
    """Score speaker note quality (§6, §7, §8)."""
    notes = content_dict.get("speaker_notes", "")
    if not notes:
        if intent in (SlideIntent.COVER, SlideIntent.Q_AND_A, SlideIntent.REFERENCES):
            return 85
        return 30
    
    score = 65
    wc = count_words(notes)
    
    from .speaker_notes_v2 import get_note_word_range, validate_note_not_duplicating_slide
    min_w, max_w = get_note_word_range(intent)
    if min_w <= wc <= max_w:
        score += 20
    elif wc >= min_w * 0.8:
        score += 10
    
    acceptable, overlap = validate_note_not_duplicating_slide(notes, content_dict)
    if acceptable:
        score += 15
    else:
        score -= 20

    # Reward presence of cues
    if content_dict.get("speaker_note_cues"):
        score += 5
    
    return max(0, min(100, score))


def score_cross_slide_novelty(novelty_score: float) -> int:
    """Convert deck memory novelty score (0.0–1.0) to quality score (0–100)."""
    return max(0, min(100, int(novelty_score * 100)))


# ═══════════════════════════════════════════════════════════════
# Blind Topic Identification & Cross-Topic Contrast Evaluators
# ═══════════════════════════════════════════════════════════════

def evaluate_blind_topic_identifiability(
    content_dict: Dict[str, Any],
    topic: str,
    domain: str,
) -> Tuple[bool, int, str]:
    """
    Blind Topic Identification Test (§12 & §15).
    Removes title and topic name; evaluates if remaining content contains
    enough distinctive entities, mechanisms, relationships, or terminology
    to infer the subject or its narrow domain.
    """
    parts = [
        content_dict.get("primary_takeaway", ""),
        content_dict.get("example", ""),
        content_dict.get("callout", ""),
    ]
    parts.extend(content_dict.get("supporting_points", []))
    parts.extend(content_dict.get("process_steps", []))
    blind_text = " ".join(p for p in parts if p)

    topic_clean = re.sub(r"[^\w\s]", "", topic).strip()
    blind_text = re.sub(re.escape(topic_clean), "[TOPIC]", blind_text, flags=re.IGNORECASE)
    for word in topic_clean.split():
        if len(word) >= 4:
            blind_text = re.sub(r'\b' + re.escape(word) + r'\b', "[TERM]", blind_text, flags=re.IGNORECASE)

    words = [w.lower() for w in re.findall(r'\b[a-zA-Z]{4,}\b', blind_text)]
    generic_stopwords = {
        "topic", "term", "this", "that", "with", "from", "have", "been",
        "their", "which", "about", "into", "through", "under", "system",
        "state", "level", "core", "baseline", "model", "parameter",
        "ensure", "ensures", "high", "performance", "reliable", "operations",
        "operation", "operational", "across", "components", "component",
        "proper", "configuration", "prevents", "prevent", "bottlenecks",
        "bottleneck", "regular", "monitoring", "monitor", "consistent",
        "efficiency", "efficient", "provides", "provide", "process",
        "approach", "method", "allows", "allow", "functions", "function",
        "overall", "critical", "important", "effective", "different",
        "various", "multiple", "several", "general", "standard", "analysis",
        "aspects", "details", "factors", "impacts", "results", "using",
        "rules", "governing", "mechanisms", "constraints", "measurable",
        "stability", "verification", "compliance", "criteria", "integration",
        "patterns", "modular", "expansion", "backward", "invariants",
        "functional", "theoretical", "predictions", "boundary", "parameters",
        "error", "budgets", "primary", "alternative", "workloads",
        "analyzing", "clarifies", "systematic", "deliver", "support", "breaking", "varied", "without"
    }
    distinctive_terms = [w for w in words if w not in generic_stopwords]

    from .domain_content_writer import get_domain_profile
    profile = get_domain_profile(domain)
    domain_emphasis = [t.lower() for t in profile.get("emphasis", [])]
    domain_hits = [w for w in distinctive_terms if any(e in w or w in e for e in domain_emphasis)]

    # We need stronger evidence than just 2 generic nouns.
    # We require either multiple domain hits or a large number of distinct distinctive terms.
    specificity_score = min(100, len(distinctive_terms) * 4 + len(domain_hits) * 15)
    
    # Non-general domains must show substantial domain-native concepts
    if domain and domain != "general_accessible" and not domain_hits and len(distinctive_terms) < 6:
        is_identifiable = False
        reason = f"Insufficient distinct concepts. Found {len(distinctive_terms)} terms, 0 domain markers for {domain}."
    else:
        is_identifiable = specificity_score >= 45 and (len(domain_hits) >= 2 or len(distinctive_terms) >= 6)
        reason = f"Found {len(domain_hits)} domain markers and {len(distinctive_terms)} distinctive terms."

    return is_identifiable, specificity_score, reason


def evaluate_domain_contamination(
    content_dict: Dict[str, Any],
    domain: str,
    topic: str
) -> Tuple[bool, str]:
    """
    Detects if the slide contains semantic terminology inappropriate for the domain.
    Examples: networking terms in biology, legislative terms in history.
    """
    parts = [
        content_dict.get("primary_takeaway", ""),
        content_dict.get("example", ""),
        content_dict.get("callout", ""),
    ]
    parts.extend(content_dict.get("supporting_points", []))
    parts.extend(content_dict.get("process_steps", []))
    combined = " ".join(p for p in parts if p).lower()

    if not combined:
        return False, ""

    if domain == "biology":
        # Software deployment language
        if "tcp" in combined or "handshake" in combined or "sliding window" in combined or "software deployment" in combined:
            return True, "Biology slide contains networking/software language"
    elif domain == "history":
        # Legislative procedure language
        if "legislative procedure" in combined or "committee referral" in combined or "bicameral" in combined or "supermajority" in combined:
            return True, "History slide contains legislative procedure language"
    elif domain == "literature_humanities":
        # Bounded-latency engineering language
        if "bounded-latency" in combined or "engineering language" in combined or "latency" in combined or "workload" in combined:
            return True, "Literature slide contains engineering latency language"
    elif domain == "law":
        # Workload/latency decisions
        if "workload" in combined or "latency" in combined or "throughput" in combined:
            return True, "Law slide contains workload/throughput language"
    elif domain == "mathematics":
        # Production validation/error-budget
        if "production validation" in combined or "error-budget" in combined or "error budget" in combined:
            return True, "Math slide contains production/engineering language"
    elif domain == "environmental_science" and "logistic equation" in combined:
        if "verified data" not in combined and "demonstrated evidence" not in combined and "empirical" not in combined:
            return True, "Data story formula without evidence"


    return False, ""



def evaluate_cross_topic_contrast(
    content_a: Dict[str, Any],
    content_b: Dict[str, Any],
) -> Tuple[bool, float, str]:
    """
    Cross-Topic Contrast Test (§13 & §14).
    Compares equivalent slide intents for unrelated topics.
    Fails if sentence structures remain nearly identical after changing nouns.
    """
    takeaway_a = content_a.get("primary_takeaway", "").strip()
    takeaway_b = content_b.get("primary_takeaway", "").strip()
    
    if not takeaway_a or not takeaway_b:
        return True, 0.0, "Empty takeaway in comparison"

    words_a = set(w.rstrip(".,;:!?").lower() for w in takeaway_a.split())
    words_b = set(w.rstrip(".,;:!?").lower() for w in takeaway_b.split())
    
    if not words_a or not words_b:
        return True, 0.0, "No words in comparison"
        
    jaccard = len(words_a & words_b) / len(words_a | words_b)
    
    prefix_a = " ".join(takeaway_a.split()[:4]).lower()
    prefix_b = " ".join(takeaway_b.split()[:4]).lower()
    prefix_identical = (prefix_a == prefix_b and len(prefix_a.split()) >= 4)
    
    is_distinct = (jaccard < 0.65) and not prefix_identical
    explanation = f"Jaccard word overlap: {round(jaccard, 3)}, identical opening prefix: {prefix_identical}"
    return is_distinct, round(jaccard, 3), explanation


# ═══════════════════════════════════════════════════════════════
# Full Slide Quality Audit
# ═══════════════════════════════════════════════════════════════

def audit_slide_content(
    content_dict: Dict[str, Any],
    intent: SlideIntent,
    topic: str,
    domain: str,
    education_level: str = "university",
    body_budget_max: int = 80,
    canonical_concepts: Optional[List[str]] = None,
    canonical_terms: Optional[Dict[str, List[str]]] = None,
    claims: Optional[List[ClaimEvidence]] = None,
    novelty_score: float = 1.0,
    reasoning_dimensions: Optional[List[str]] = None,
    subdomain: str = "",
    concept_packet: Optional[Any] = None,
) -> ContentQualityScores:
    """Run the full 12-dimension quality audit on a single slide."""
    hard_fails = []
    
    # 0. Domain Contamination check
    is_contaminated, contamination_reason = evaluate_domain_contamination(content_dict, domain, topic)
    if is_contaminated:
        hard_fails.append(f"DOMAIN_CONTAMINATION: {contamination_reason}")
    
    scores = ContentQualityScores(
        content_correctness=score_content_correctness(content_dict, claims, intent),
        topic_specificity=score_topic_specificity(content_dict, topic, domain, canonical_concepts, subdomain, intent),
        primary_idea_clarity=score_primary_idea_clarity(content_dict, topic, domain, intent=intent, concept_packet=concept_packet),
        content_depth=score_content_depth(content_dict, intent, reasoning_dimensions),
        audience_fit=score_audience_fit(content_dict, education_level, intent),
        slide_nativeness=score_slide_nativeness(content_dict, intent),
        text_budget_compliance=score_text_budget_compliance(content_dict, body_budget_max),
        example_quality=score_example_quality(content_dict, topic),
        terminology_consistency=score_terminology_consistency(content_dict, canonical_terms),
        evidence_integrity=score_evidence_integrity(claims),
        speaker_note_value=score_speaker_note_value(content_dict, intent),
        cross_slide_novelty=score_cross_slide_novelty(novelty_score),
    )
    
    # Compute aggregate
    dimension_scores = [
        scores.content_correctness, scores.topic_specificity,
        scores.primary_idea_clarity, scores.content_depth,
        scores.audience_fit, scores.slide_nativeness,
        scores.text_budget_compliance, scores.example_quality,
        scores.terminology_consistency, scores.evidence_integrity,
        scores.speaker_note_value, scores.cross_slide_novelty,
    ]
    scores.aggregate_score = sum(dimension_scores) // len(dimension_scores)
    
    # ─── Hard Fail Detection ──────────────────────────────────
    hard_fails = []
    
    # Semantic gap hard fail
    if (
        (content_dict.get("content_origin") in (ContentOrigin.CONTENT_SEMANTIC_GAP, "content_semantic_gap"))
        or (content_dict.get("semantic_status") in (SemanticStatus.GAP, "gap"))
        or (content_dict.get("fit_risk") == "CONTENT_SEMANTIC_GAP")
    ):
        hard_fails.append("CONTENT_SEMANTIC_GAP")

    # Generic repair wrapper hard fail
    takeaway = content_dict.get("primary_takeaway", "").strip()
    takeaway_lower = takeaway.lower()
    for wrapper in CONTENT_FREE_REPAIR_WRAPPERS:
        if takeaway_lower.startswith(wrapper):
            hard_fails.append(f"GENERIC_REPAIR_WRAPPER: {wrapper}")
            break

    # Unsupported numeric claim
    if claims:
        for claim in claims:
            if (claim.claim_type == ClaimType.NUMERIC_CLAIM and
                claim.verification_status == ClaimVerificationStatus.SOURCE_PENDING and
                claim.source_required):
                hard_fails.append(f"UNSUPPORTED_NUMERIC_CLAIM: {claim.claim_text[:60]}")
    
    # Placeholder text
    combined = content_dict.get("primary_takeaway", "") + " " + " ".join(content_dict.get("supporting_points", []))
    if any(p in combined.lower() for p in ["placeholder", "tbd", "content goes here", "lorem"]):
        hard_fails.append("PLACEHOLDER_TEXT_DETECTED")
    
    # Empty primary message for content slides
    if not content_dict.get("primary_takeaway") and intent not in (SlideIntent.COVER, SlideIntent.AGENDA, SlideIntent.Q_AND_A, SlideIntent.REFERENCES):
        hard_fails.append("EMPTY_PRIMARY_MESSAGE")
    
    # Text budget hard violation (> 150% of budget)
    if body_budget_max > 0:
        body_parts = [content_dict.get("primary_takeaway", "")]
        body_parts.extend(content_dict.get("supporting_points", []))
        body_wc = count_words(" ".join(p for p in body_parts if p))
        if body_wc > body_budget_max * 1.5:
            hard_fails.append(f"TEXT_BUDGET_HARD_VIOLATION: {body_wc}/{body_budget_max}")
    
    # Banned phrases in primary takeaway
    has_banned, banned_list = contains_banned_phrase(takeaway)
    if has_banned:
        hard_fails.append(f"BANNED_PHRASE_IN_TAKEAWAY: {banned_list[0]}")
    
    # Incomplete title check
    title = content_dict.get("title", "").strip()
    if intent not in (SlideIntent.COVER, SlideIntent.AGENDA, SlideIntent.Q_AND_A, SlideIntent.REFERENCES):
        is_inc, inc_reason = detect_incomplete_title(title)
        if is_inc:
            hard_fails.append(f"INCOMPLETE_TITLE: {inc_reason}")
            scores.primary_idea_clarity = min(scores.primary_idea_clarity, 40)

    # Ungrammatical statement check
    is_ungramm, ungramm_reason = detect_ungrammatical_statement(takeaway)
    if is_ungramm:
        hard_fails.append(f"UNGRAMMATICAL_TAKEAWAY: {ungramm_reason}")
        scores.primary_idea_clarity = min(scores.primary_idea_clarity, 40)

    # Cross-slide duplicate takeaway check
    prior_takeaways = content_dict.get("_prior_takeaways", [])
    for pt in prior_takeaways:
        if pt and pt.strip().lower() == takeaway.lower() and len(takeaway.split()) > 3:
            hard_fails.append("DUPLICATE_SLIDE_TAKEAWAY")
            scores.primary_idea_clarity = min(scores.primary_idea_clarity, 35)
            break

    # Topic substitution prose hard fail (§1)
    gen_penalty, gen_issues = detect_genericity(content_dict, topic, domain, subdomain)
    for issue in gen_issues:
        if any(w in issue.lower() for w in ["systematic execution of", "structural stability", "rigorous implementation"]):
            hard_fails.append(f"GENERIC_CROSS_TOPIC_TEMPLATE: {issue}")
            scores.topic_specificity = min(scores.topic_specificity, 40)
            scores.primary_idea_clarity = min(scores.primary_idea_clarity, 40)
            break
        if issue.startswith("TOPIC_SUBSTITUTION_PROSE") and (topic.lower() in takeaway.lower() or any(w in takeaway.lower() for w in topic.lower().split() if len(w) >= 4)):
            hard_fails.append(f"GENERIC_TOPIC_SUBSTITUTION: {issue}")
            break
    
    scores.has_hard_fail = len(hard_fails) > 0
    scores.hard_fail_reasons = hard_fails
    
    return scores


# ═══════════════════════════════════════════════════════════════
# Quality Gate
# ═══════════════════════════════════════════════════════════════

# Recommended initial gate thresholds
QUALITY_GATE = {
    "content_correctness": 92,
    "topic_specificity": 90,
    "primary_idea_clarity": 90,
    "slide_nativeness": 88,
    "audience_fit": 88,
    "text_budget_compliance": 100,
    "evidence_integrity": 100,  # For cited claims
}


def passes_quality_gate(scores: ContentQualityScores) -> Tuple[bool, List[str]]:
    """Check if a slide passes the quality gate.
    Hard fails override aggregate score."""
    
    if scores.has_hard_fail:
        return False, scores.hard_fail_reasons
    
    failures = []
    for dimension, threshold in QUALITY_GATE.items():
        dim_score = getattr(scores, dimension, 100)
        if dim_score < threshold:
            failures.append(f"{dimension}: {dim_score}/{threshold}")
    
    return len(failures) == 0, failures


# ═══════════════════════════════════════════════════════════════
# Targeted Content Repair
# ═══════════════════════════════════════════════════════════════

class RepairType:
    TITLE_REPAIR = "TITLE_REPAIR"
    BODY_REPAIR = "BODY_REPAIR"
    TAKEAWAY_SEMANTIC_REPAIR = "TAKEAWAY_SEMANTIC_REPAIR"
    EXAMPLE_REPAIR = "EXAMPLE_REPAIR"
    CLAIM_REPAIR = "CLAIM_REPAIR"
    COMPARISON_REPAIR = "COMPARISON_REPAIR"
    CODE_REPAIR = "CODE_REPAIR"
    FORMULA_REPAIR = "FORMULA_REPAIR"
    QUIZ_REPAIR = "QUIZ_REPAIR"
    SPEAKER_NOTE_REPAIR = "SPEAKER_NOTE_REPAIR"


def identify_needed_repairs(
    scores: ContentQualityScores,
    content_dict: Dict[str, Any],
) -> List[str]:
    """Identify which targeted repairs are needed based on quality scores.
    Repairs only failed fields — not the entire slide."""
    repairs = []
    
    # Title repair
    title = content_dict.get("title", "")
    has_banned, _ = contains_banned_phrase(title)
    if has_banned or not title:
        repairs.append(RepairType.TITLE_REPAIR)
    
    # Takeaway semantic repair
    takeaway = content_dict.get("primary_takeaway", "")
    has_wrapper = any(takeaway.lower().startswith(w) for w in CONTENT_FREE_REPAIR_WRAPPERS)
    raw_intent = content_dict.get("intent") or content_dict.get("slide_intent")
    is_exempt_intent = False
    if isinstance(raw_intent, SlideIntent) and raw_intent in (SlideIntent.COVER, SlideIntent.AGENDA, SlideIntent.Q_AND_A, SlideIntent.REFERENCES):
        is_exempt_intent = True
    elif isinstance(raw_intent, str) and raw_intent.lower() in ("cover", "agenda", "q_and_a", "qa", "references"):
        is_exempt_intent = True

    if not is_exempt_intent:
        if scores.primary_idea_clarity < 88 or has_wrapper or "EMPTY_PRIMARY_MESSAGE" in scores.hard_fail_reasons:
            repairs.append(RepairType.TAKEAWAY_SEMANTIC_REPAIR)
    elif has_wrapper:
        repairs.append(RepairType.TAKEAWAY_SEMANTIC_REPAIR)

    # Body repair (low specificity, banned phrases, or budget violation)
    if scores.topic_specificity < 70 or scores.text_budget_compliance < 80:
        repairs.append(RepairType.BODY_REPAIR)
    
    # Example repair
    if scores.example_quality < 60 and content_dict.get("example"):
        repairs.append(RepairType.EXAMPLE_REPAIR)
    
    # Claim repair (unsupported statistics)
    if scores.evidence_integrity < 80:
        repairs.append(RepairType.CLAIM_REPAIR)
    
    # Speaker note repair
    if scores.speaker_note_value < 50:
        repairs.append(RepairType.SPEAKER_NOTE_REPAIR)
    
    return repairs


def apply_deterministic_repairs(
    content_dict: Dict[str, Any],
    repairs: List[str],
    topic: str,
    domain: str,
    concept_packet: Optional[Any] = None,
    intent: Optional[SlideIntent] = None,
) -> Tuple[Dict[str, Any], List[str]]:
    """Apply deterministic (non-LLM) repairs to content.
    Returns (repaired_content, repairs_applied).
    
    Only repairs failed fields. Does not regenerate neighboring slides.
    Never manufactures unsupported semantic relationships.
    """
    repaired = dict(content_dict)
    applied = []
    
    # CLAIM_REPAIR: Remove unsupported statistics
    if RepairType.CLAIM_REPAIR in repairs:
        from .claim_evidence_engine import guard_unsupported_statistics
        
        for field in ["primary_takeaway", "callout", "example"]:
            text = repaired.get(field, "")
            if text:
                cleaned, changes = guard_unsupported_statistics(text)
                if changes:
                    repaired[field] = cleaned
                    applied.extend(changes)
        
        # Clean supporting points
        cleaned_points = []
        for point in repaired.get("supporting_points", []):
            cleaned, changes = guard_unsupported_statistics(point)
            cleaned_points.append(cleaned)
            applied.extend(changes)
        repaired["supporting_points"] = cleaned_points
    
    # TITLE_REPAIR: Remove banned phrases from title
    if RepairType.TITLE_REPAIR in repairs:
        title = repaired.get("title", "")
        for phrase in BANNED_PHRASES_PHASE2:
            if phrase in title.lower():
                title = re.sub(re.escape(phrase), "", title, flags=re.IGNORECASE).strip()
        if title:
            repaired["title"] = title
            applied.append("TITLE_REPAIR: removed banned phrases")

    # TAKEAWAY_SEMANTIC_REPAIR: True semantic repair without manufacturing fake relationships
    if RepairType.TAKEAWAY_SEMANTIC_REPAIR in repairs:
        takeaway = repaired.get("primary_takeaway", "").strip()

        # 1. Strip generic repair wrappers
        for wrapper in CONTENT_FREE_REPAIR_WRAPPERS:
            if takeaway.lower().startswith(wrapper):
                takeaway = takeaway[len(wrapper):].strip().lstrip(":").strip()
                if takeaway and takeaway[0].islower():
                    takeaway = takeaway[0].upper() + takeaway[1:]
                applied.append(f"TAKEAWAY_REPAIR: stripped generic wrapper '{wrapper}'")

        prior_takeaways = content_dict.get("_prior_takeaways", [])
        is_duplicate = any(pt and pt.strip().lower() == takeaway.lower() for pt in prior_takeaways if pt)

        # 2. Check if remaining takeaway expresses a complete, supported proposition
        wc = count_words(takeaway)
        relational_predicates = {
            "is", "are", "was", "were", "has", "have", "had", "does", "do", "did",
            "can", "could", "will", "would", "should", "may", "might", "shall",
            "uses", "enables", "provides", "requires", "allows", "creates", "generates",
            "processes", "converts", "transforms", "reduces", "increases", "improves",
            "detects", "prevents", "supports", "contains", "produces", "operates",
            "measures", "analyzes", "compares", "separates", "combines", "connects",
            "delivers", "manages", "controls", "defines", "describes", "explains",
            "runs", "works", "makes", "takes", "gives", "helps", "shows", "leads",
            "grows", "moves", "sends", "receives", "stores", "loads", "builds",
            "breaks", "sets", "gets", "puts", "keeps", "turns", "starts", "stops",
            "adds", "removes", "includes", "excludes", "represents", "identifies",
            "achieves", "performs", "executes", "implements", "integrates", "validates",
            "optimizes", "minimizes", "maximizes", "eliminates", "handles", "triggers",
            "ensures", "maintains", "monitors", "tracks", "logs", "reports", "maps",
            "absorbs", "reflects", "emits", "transfers", "releases", "binds",
            "regulates", "activates", "inhibits", "catalyzes", "synthesizes",
            "evolved", "developed", "invented", "discovered", "introduced", "launched",
            "adopted", "replaced", "causes", "drives", "balances", "couples", "encodes",
            "yields", "equals", "modulates", "terminates", "governs", "stabilizes",
            "coordinates", "delegates", "offloads", "advances", "distinguishes",
            "demonstrates", "initiates", "determines", "decreases", "mediates",
            "depends", "establishes", "relates", "characterizes", "arise", "arises",
            "manifest", "manifests", "stems", "originates", "emerges", "occurs",
            "applies", "relies", "functions", "differs", "varies", "contradicts",
            "challenges", "alters", "protects", "protect", "limits", "checks", "filters",
            "demands", "empowers", "expands", "redefines", "evolves", "remedies", "strikes",
        }
        words_cleaned = [w.strip(".,;:!?\"'()[]{}").lower() for w in takeaway.split()]
        has_verb_or_rel = any(w in relational_predicates for w in words_cleaned) or any(
            len(w) > 4 and (w.endswith("izes") or w.endswith("ates") or w.endswith("fies") or w.endswith("cted") or w.endswith("ited") or w.endswith("ated"))
            for w in words_cleaned
        ) or any(
            sym in takeaway for sym in ["=", "\\approx", "\\equiv", "<=", ">=", "\\le", "\\ge", "\\rightarrow", "->"]
        )

        if intent in (SlideIntent.COVER, SlideIntent.AGENDA, SlideIntent.Q_AND_A, SlideIntent.REFERENCES):
            is_substantive = bool(takeaway)
        else:
            is_substantive = bool(takeaway and wc >= 5 and has_verb_or_rel)

        # 3. If takeaway is incomplete, generic, or duplicated, inspect SlideConceptPacket & Blueprint
        if not is_substantive or is_duplicate:
            repaired_from_packet = False

            # Check distinct blueprint primary message first
            bp_msg = content_dict.get("_blueprint_message", "")
            if bp_msg and count_words(bp_msg) >= 4 and not any(pt.strip().lower() == bp_msg.strip().lower() for pt in prior_takeaways if pt):
                cand_bp = sanitize_and_complete_title(bp_msg, topic=topic)
                c_words = [w.strip(".,;:!?\"'()[]{}").lower() for w in cand_bp.split()]
                has_pred = any(w in relational_predicates for w in c_words) or any(
                    len(w) > 4 and (w.endswith("izes") or w.endswith("ates") or w.endswith("fies") or w.endswith("cted") or w.endswith("ited") or w.endswith("ated"))
                    for w in c_words
                )
                if not has_pred:
                    if cand_bp.lower().startswith("comparing ") or cand_bp.lower().startswith("contrasting "):
                        takeaway = f"{cand_bp} highlights distinct approaches within {topic}."
                    elif cand_bp.lower().startswith("how "):
                        takeaway = f"Analysis reveals {cand_bp[0].lower() + cand_bp[1:]}."
                    elif cand_bp.lower().startswith("why "):
                        takeaway = f"Domain evidence clarifies {cand_bp[0].lower() + cand_bp[1:]}."
                    elif " as the " in cand_bp.lower():
                        takeaway = re.sub(r"\bas the\b", "operates as the", cand_bp, flags=re.IGNORECASE)
                        if not takeaway.endswith("."):
                            takeaway += "."
                    else:
                        takeaway = f"Foundational principles govern {cand_bp[0].lower() + cand_bp[1:]}."
                else:
                    takeaway = cand_bp
                repaired_from_packet = True
                applied.append("TAKEAWAY_SEMANTIC_REPAIR: restored distinct blueprint primary message")

            if not repaired_from_packet and concept_packet:
                # Priority A: Supported relationship from packet that is NOT in prior_takeaways
                rels = getattr(concept_packet, "relationships", []) or []
                for r in rels:
                    if isinstance(r, str) and count_words(r) >= 4 and not any(pt.strip().lower() == r.strip().lower() for pt in prior_takeaways if pt):
                        takeaway = r.strip()
                        repaired_from_packet = True
                        applied.append("TAKEAWAY_SEMANTIC_REPAIR: restored supported relationship from concept packet")
                        break

                # Priority B: Validated cause-effect pair that is NOT in prior_takeaways
                if not repaired_from_packet:
                    ce_pairs = getattr(concept_packet, "cause_effect_pairs", []) or []
                    for pair in ce_pairs:
                        if isinstance(pair, dict) and pair.get("cause") and pair.get("effect"):
                            c = pair['cause'].strip()
                            e = pair['effect'].strip()
                            eff_words = e.split()
                            first_eff = eff_words[0].lower() if eff_words else ""
                            finite_verbs = {
                                "prevents", "creates", "ensures", "causes", "generates", "initiates",
                                "drives", "produces", "establishes", "requires", "allows", "enables",
                                "regulates", "modulates", "inhibits", "activates", "catalyzes", "governs",
                                "applies", "relies", "functions", "balances", "couples", "transforms", "converts"
                            }
                            c_words_set = set(w.strip(".,;:!?\"'()[]{}").lower() for w in c.split())
                            c_has_verb = any(w in finite_verbs for w in c_words_set)
                            if first_eff in finite_verbs:
                                if c_has_verb:
                                    cand = f"When {c[0].lower() + c[1:]}, it {first_eff} {' '.join(eff_words[1:])}."
                                else:
                                    cand = f"{c} {first_eff} {' '.join(eff_words[1:])}."
                            else:
                                if c_has_verb:
                                    cand = f"When {c[0].lower() + c[1:]}, it leads to {e}."
                                else:
                                    cand = f"{c} leads to {e}."
                            if not any(pt.strip().lower() == cand.strip().lower() for pt in prior_takeaways if pt):
                                takeaway = cand
                                repaired_from_packet = True
                                applied.append("TAKEAWAY_SEMANTIC_REPAIR: restored validated cause-effect pair")
                                break

                # Priority C: Validated process sequence (at least 2 stages)
                if not repaired_from_packet and intent in (SlideIntent.PROCESS_EXPLANATION, SlideIntent.SYSTEM_OVERVIEW):
                    stages = getattr(concept_packet, "process_stages", []) or []
                    if len(stages) >= 2:
                        cand = f"The initial stage '{stages[0]}' transitions into '{stages[1]}'."
                        if not any(pt.strip().lower() == cand.strip().lower() for pt in prior_takeaways if pt):
                            takeaway = cand
                            repaired_from_packet = True
                            applied.append("TAKEAWAY_SEMANTIC_REPAIR: restored validated process sequence")

                # Priority D: Source-grounded facts
                if not repaired_from_packet:
                    facts = getattr(concept_packet, "source_grounded_facts", []) or []
                    for f in facts:
                        f_str = f if isinstance(f, str) else str(f)
                        if count_words(f_str) >= 5 and not any(pt.strip().lower() == f_str.strip().lower() for pt in prior_takeaways if pt):
                            takeaway = f_str.strip()
                            repaired_from_packet = True
                            applied.append("TAKEAWAY_SEMANTIC_REPAIR: restored source-grounded fact")
                            break

                # Priority E: Validated misconception reality
                if not repaired_from_packet and intent in (SlideIntent.MISCONCEPTION, SlideIntent.COMMON_MISTAKES):
                    misconceptions = getattr(concept_packet, "misconceptions", []) or []
                    for m in misconceptions:
                        if isinstance(m, dict) and m.get("reality"):
                            cand = f"Common misconception clarified: in reality, {m['reality'].strip().rstrip('.')}."
                            if not any(pt.strip().lower() == cand.strip().lower() for pt in prior_takeaways if pt):
                                takeaway = cand
                                repaired_from_packet = True
                                applied.append("TAKEAWAY_SEMANTIC_REPAIR: restored validated misconception reality")
                                break

                # Priority F: Validated comparison dimension
                if not repaired_from_packet and intent in (SlideIntent.COMPARISON, SlideIntent.TRADEOFF):
                    dims = getattr(concept_packet, "comparison_dimensions", []) or []
                    for dim in dims:
                        if isinstance(dim, str):
                            cand = f"Evaluating operational tradeoffs reveals critical structural distinctions in {dim.strip()}."
                            if not any(pt.strip().lower() == cand.strip().lower() for pt in prior_takeaways if pt):
                                takeaway = cand
                                repaired_from_packet = True
                                applied.append("TAKEAWAY_SEMANTIC_REPAIR: restored validated comparison dimension")
                                break

                # Priority G: Validated example candidate
                if not repaired_from_packet and intent in (SlideIntent.WORKED_EXAMPLE, SlideIntent.CASE_STUDY, SlideIntent.REAL_WORLD_APPLICATION):
                    examples = getattr(concept_packet, "example_candidates", []) or []
                    for ex in examples:
                        if isinstance(ex, str):
                            cand = f"Practical application in {ex.strip()} demonstrates core operational principles."
                            if not any(pt.strip().lower() == cand.strip().lower() for pt in prior_takeaways if pt):
                                takeaway = cand
                                repaired_from_packet = True
                                applied.append("TAKEAWAY_SEMANTIC_REPAIR: restored validated example candidate")
                                break


            if repaired_from_packet:
                repaired["primary_takeaway"] = takeaway
                if repaired.get("content_origin") in (ContentOrigin.CONTENT_SEMANTIC_GAP, "content_semantic_gap"):
                    repaired["content_origin"] = ContentOrigin.DETERMINISTIC_STRUCTURE
                if repaired.get("semantic_status") in (SemanticStatus.GAP, "gap"):
                    repaired["semantic_status"] = SemanticStatus.GROUNDED
                if repaired.get("fit_risk") == "CONTENT_SEMANTIC_GAP":
                    repaired["fit_risk"] = ""
                if "CONTENT_SEMANTIC_GAP" in repaired.get("semantic_failure_reasons", []):
                    repaired["semantic_failure_reasons"] = [r for r in repaired["semantic_failure_reasons"] if r != "CONTENT_SEMANTIC_GAP"]
            else:
                # CRITICAL: DO NOT manufacture fake relationships!
                # Mark as semantic gap
                repaired["primary_takeaway"] = ""
                repaired["content_origin"] = ContentOrigin.CONTENT_SEMANTIC_GAP
                repaired["semantic_status"] = SemanticStatus.GAP
                repaired["fit_risk"] = "CONTENT_SEMANTIC_GAP"
                repaired["semantic_failure_reasons"] = [
                    SemanticFailureReason.MISSING_RELATIONSHIP.value,
                    SemanticFailureReason.INSUFFICIENT_CONCEPT_PACKET.value,
                ]
                applied.append("TAKEAWAY_REPAIR_FAILED: Insufficient supported relationship in packet; marked CONTENT_SEMANTIC_GAP")
        else:
            repaired["primary_takeaway"] = takeaway

        # 4. Consistency check: Ensure repaired takeaway does not contradict supporting points
        if repaired.get("primary_takeaway"):
            clean_pts = []
            takeaway_text = repaired["primary_takeaway"].lower()
            negation_terms = {"not", "never", "cannot", "independent", "without"}
            takeaway_neg = any(f" {w} " in f" {takeaway_text} " for w in negation_terms)
            takeaway_keywords = {w for w in re.findall(r'\b\w{4,}\b', takeaway_text)}

            for pt in repaired.get("supporting_points", []):
                pt_lower = pt.lower()
                pt_neg = any(f" {w} " in f" {pt_lower} " for w in negation_terms)
                shared_keywords = takeaway_keywords.intersection(re.findall(r'\b\w{4,}\b', pt_lower))
                # If one asserts negation and the other positive on shared core keywords, it is a contradiction
                if (takeaway_neg != pt_neg) and len(shared_keywords) >= 2:
                    applied.append(f"DEPENDENT_FIELD_CONSISTENCY: removed contradictory supporting point '{pt[:50]}...'")
                    continue
                clean_pts.append(pt)
            repaired["supporting_points"] = clean_pts
    
    # BODY_REPAIR: Remove banned phrases from body
    if RepairType.BODY_REPAIR in repairs:
        takeaway = repaired.get("primary_takeaway", "")
        for phrase in BANNED_PHRASES_PHASE2:
            if phrase in takeaway.lower():
                takeaway = re.sub(re.escape(phrase), "", takeaway, flags=re.IGNORECASE).strip()
        repaired["primary_takeaway"] = takeaway

        cleaned_points = []
        for point in repaired.get("supporting_points", []):
            for phrase in BANNED_PHRASES_PHASE2:
                if phrase in point.lower():
                    point = re.sub(re.escape(phrase), "", point, flags=re.IGNORECASE).strip()
            if point:
                cleaned_points.append(point)
        repaired["supporting_points"] = cleaned_points
        applied.append("BODY_REPAIR: cleaned banned phrases")
    
    return repaired, applied
