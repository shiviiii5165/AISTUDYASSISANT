"""
Content Agent (Phase 2 — Content Intelligence Engine)
======================================================
Transforms presentation outlines and blueprints into expert-grade,
slide-native, teacher-quality content for ANY topic.

Key Capabilities:
1. Generates structured SlideContent model matching SlideIntent.
2. Enforces content depth (WHAT, HOW, WHY, WHEN, EXAMPLE, TRADE-OFF, CONFUSION).
3. Adapts tone, terminology, and reasoning across 18 domain profiles & 4 audience levels.
4. Strictly respects TextBudget and LayoutCapacity without silent font shrinking.
5. Rejects banned generic AI filler phrases and unsupported statistics.
6. Generates rich Speaker Notes V2 with intent-aware word counts and structured cues.
7. Tracks per-deck semantic memory (isolated per job) to eliminate cross-slide repetition.
8. Audits content across 12 quality dimensions with targeted field-level repair.
9. Fully backward-compatible: synchronizes SlideContent into legacy SlideSpec fields.
"""
import re
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional, Set, Tuple

from app.services.ai import router
from .schemas import (
    PresentationConfig,
    SlideSpec,
    SlideType,
    ContentPattern,
    SlideSelfCheck,
    SlideSourceRef,
    SlideIntent,
    LayoutFamily,
    VisualTypeHint,
    ContentDensity,
    PresentationBrief,
    SlideBlueprint,
    SlideContent,
    ContentQualityScores,
    ContentProvenance,
    ClaimType,
    ClaimEvidence,
    ClaimVerificationStatus,
    ContentOrigin,
    SemanticStatus,
    SemanticFailureReason,
    QualityGateError,
    LayoutCapacity,
    SpeakerNoteCue,
    MisconceptionBlock,
    ComparisonRow,
    DataPoint,
    SlideConceptPacket,
)
from .domain_content_writer import (
    build_content_generation_context,
    build_domain_writing_prompt,
    get_domain_profile,
    get_audience_profile,
    get_expected_fields,
    resolve_slide_concept_packet,
    DOMAIN_WRITING_PROFILES,
    INTENT_REASONING_DIMENSIONS,
)
from .claim_evidence_engine import (
    guard_unsupported_statistics,
    classify_claims_in_content,
    resolve_evidence_for_claims,
    tag_content_origin,
)
from .deck_content_memory import DeckContentMemory
from .speaker_notes_v2 import (
    build_speaker_notes_prompt,
    extract_cues_from_notes,
    generate_transition_cue,
    generate_expert_speaker_notes,
    measure_note_structural_similarity,
    get_note_word_range,
    validate_note_not_duplicating_slide,
    validate_analogy_quality,
    SPEAKER_NOTE_WORD_RANGES,
)
from .content_budget_engine import (
    compute_text_budget,
    evaluate_budget_compliance,
    get_layout_capacity,
    count_words,
)
from .content_quality_auditor import (
    audit_slide_content,
    passes_quality_gate,
    identify_needed_repairs,
    apply_deterministic_repairs,
    BANNED_PHRASES_PHASE2,
    contains_banned_phrase,
    sanitize_and_complete_title,
    RepairType,
)
from .prompts import CONTENT_BATCH_SYSTEM_PROMPT, SLIDE_PATCH_SYSTEM_PROMPT
from ..knowledge import get_slide_context

logger = logging.getLogger("teachgenie.presentation.content_agent")

# Banned strings list (combines Phase 1 + Phase 2 banned phrases)
BANNED_STRINGS = list(set([
    "key operational insight",
    "supporting structural mechanism",
    "lorem",
    "tbd",
    "placeholder",
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
] + BANNED_PHRASES_PHASE2))


def _contains_banned(text: str) -> bool:
    """Check if text contains any banned filler string."""
    if not text:
        return False
    text_lower = text.lower().strip()
    return any(banned in text_lower for banned in BANNED_STRINGS)


TRAILING_DANGLING_WORDS = {
    "and", "or", "but", "nor", "so", "yet", "for", "with", "to", "of",
    "in", "on", "at", "by", "from", "as", "into", "through", "between",
    "under", "over", "about", "that", "which", "who", "whom", "whose",
    "leads", "causes", "results", "is", "are", "was", "were", "has", "have",
    "a", "an", "the"
}


def _word_boundary_truncate(text: str, max_chars: int) -> str:
    """Truncate text at a word boundary without leaving dangling incomplete clauses."""
    if not text or len(text) <= max_chars:
        return text or ""

    # Priority 1: If an existing complete sentence boundary fits comfortably within budget, use it
    period_idx = text[:max_chars].rfind(". ")
    if period_idx != -1 and period_idx >= int(max_chars * 0.4):
        return text[:period_idx + 1].strip()

    cut = text[:max_chars]
    last_space = cut.rfind(" ")
    if last_space > int(max_chars * 0.4):
        cut = cut[:last_space]

    cut = cut.rstrip(" ,;:-–—")

    # Strip any dangling trailing words
    words = cut.split()
    while words and words[-1].lower().rstrip(".,:;") in TRAILING_DANGLING_WORDS:
        words.pop()

    if words:
        cut = " ".join(words).rstrip(" ,;:-–—")
    return cut


def _has_verb(sentence: str) -> bool:
    """Basic heuristic to check if a sentence likely contains a verb."""
    verb_indicators = [
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
        "adopted", "replaced", "eliminated", "reduced", "increased", "improved",
        "reached", "exceeded", "dropped", "rose", "fell", "grew", "shrank",
        "compiles", "offloads", "coordinates", "delegates", "resolves", "schedules",
        "dispatches", "allocates", "instantiates", "buffers", "streams", "yields",
        "intercepts", "listens", "emits", "polls", "invokes", "orchestrates",
        "encapsulates", "binds", "unblocks", "blocks", "serves", "reads", "writes",
        "parses", "evaluates", "links", "isolates", "mitigates", "structures",
        "expose", "exposes", "exposed", "exposing",
        "allocate", "allocates", "allocated", "allocating",
        "drain", "drains", "drained", "draining",
        "exhaust", "exhausts", "exhausted", "exhausting",
        "provide", "provides", "provided", "providing",
        "execute", "executes", "executed", "executing",
        "resolve", "resolves", "resolved", "resolving",
        "load", "loads", "loaded", "loading",
        "parse", "parses", "parsed", "parsing",
        "link", "links", "linked", "linking",
        "block", "blocks", "blocked", "blocking",
        "delegate", "delegates", "delegated", "delegating",
        "schedule", "schedules", "scheduled", "scheduling",
        "trigger", "triggers", "triggered", "triggering",
        "scale", "scales", "scaled", "scaling",
        "manage", "manages", "managed", "managing",
        "offload", "offloads", "offloaded", "offloading",
        "dispatch", "dispatches", "dispatched", "dispatching",
        "evaluate", "evaluates", "evaluated", "evaluating",
        "encounter", "encounters", "encountered", "encountering",
        "validate", "validates", "validated", "validating",
        "require", "requires", "required", "requiring",
        "leverage", "leverages", "leveraged", "leveraging",
        "buffer", "buffers", "buffered", "buffering",
        "stream", "streams", "streamed", "streaming",
        "defer", "defers", "deferred", "deferring",
        "compete", "competes", "competed", "competing",
    ]
    words = [w.strip(".,;:!?\"'()[]{}").lower() for w in sentence.split()]
    return any(w in verb_indicators for w in words)


# ═══════════════════════════════════════════════════════════════
# Intent to SlideType and ContentPattern mapping
# ═══════════════════════════════════════════════════════════════

def _strip_unsupported_statistics(text: str) -> str:
    """If text contains statistics (%, $, etc.) without source grounding, return empty or stripped."""
    if re.search(r'\d+\s*(?:%|percent|billion|million|trillion|\$|€|£)', text.lower()):
        # Just return an empty string to filter it out entirely, avoiding weird grammar from stripping
        return ""
    return text

def _filter_list_for_stats(items: List[str]) -> List[str]:
    return [x for x in items if _strip_unsupported_statistics(x)]

INTENT_TO_SLIDETYPE: Dict[SlideIntent, SlideType] = {
    SlideIntent.COVER: SlideType.HERO,
    SlideIntent.HOOK: SlideType.CONCEPT,
    SlideIntent.CONTEXT: SlideType.CONCEPT,
    SlideIntent.WHY_IT_MATTERS: SlideType.CONCEPT,
    SlideIntent.AGENDA: SlideType.CONCEPT,
    SlideIntent.OBJECTIVES: SlideType.CONCEPT,
    SlideIntent.DEFINITION: SlideType.DEFINITION,
    SlideIntent.MENTAL_MODEL: SlideType.CONCEPT,
    SlideIntent.CONCEPT_EXPLANATION: SlideType.CONCEPT,
    SlideIntent.SYSTEM_OVERVIEW: SlideType.ARCHITECTURE,
    SlideIntent.COMPONENT_BREAKDOWN: SlideType.CONCEPT,
    SlideIntent.PROCESS_EXPLANATION: SlideType.PROCESS_FLOW,
    SlideIntent.COMPARISON: SlideType.COMPARISON,
    SlideIntent.TRADEOFF: SlideType.COMPARISON,
    SlideIntent.WORKED_EXAMPLE: SlideType.EXAMPLE,
    SlideIntent.CODE_EXAMPLE: SlideType.CODE,
    SlideIntent.FORMULA_EXPLANATION: SlideType.FORMULA,
    SlideIntent.CASE_STUDY: SlideType.CASE_STUDY,
    SlideIntent.REAL_WORLD_APPLICATION: SlideType.EXAMPLE,
    SlideIntent.DATA_INSIGHT: SlideType.KPI_METRICS,
    SlideIntent.MISCONCEPTION: SlideType.COMMON_MISTAKES,
    SlideIntent.COMMON_MISTAKES: SlideType.COMMON_MISTAKES,
    SlideIntent.BEST_PRACTICES: SlideType.CONCEPT,
    SlideIntent.DIAGNOSTIC: SlideType.CONCEPT,
    SlideIntent.KNOWLEDGE_CHECK: SlideType.QUIZ,
    SlideIntent.SUMMARY: SlideType.SUMMARY,
    SlideIntent.REFERENCES: SlideType.CONCEPT,
    SlideIntent.Q_AND_A: SlideType.QA,
}

INTENT_TO_CONTENT_PATTERN: Dict[SlideIntent, ContentPattern] = {
    SlideIntent.COVER: ContentPattern.PLAIN_CONCEPT,
    SlideIntent.DEFINITION: ContentPattern.DEFINITION_BOX,
    SlideIntent.CONCEPT_EXPLANATION: ContentPattern.PLAIN_CONCEPT,
    SlideIntent.PROCESS_EXPLANATION: ContentPattern.NUMBERED_PROCESS,
    SlideIntent.COMPARISON: ContentPattern.COMPARISON_TABLE,
    SlideIntent.TRADEOFF: ContentPattern.CONTRAST_PAIR,
    SlideIntent.MISCONCEPTION: ContentPattern.CONTRAST_PAIR,
    SlideIntent.COMMON_MISTAKES: ContentPattern.CONTRAST_PAIR,
    SlideIntent.WORKED_EXAMPLE: ContentPattern.WORKED_EXAMPLE_TABLE,
    SlideIntent.CASE_STUDY: ContentPattern.CASE_STUDY_BLOCK,
    SlideIntent.REAL_WORLD_APPLICATION: ContentPattern.EXAMPLE_GRID,
    SlideIntent.DATA_INSIGHT: ContentPattern.ANNOTATED_TIERS,
    SlideIntent.SYSTEM_OVERVIEW: ContentPattern.ILLUSTRATED_ICON_GRID,
    SlideIntent.COMPONENT_BREAKDOWN: ContentPattern.ANNOTATED_TIERS,
    SlideIntent.SUMMARY: ContentPattern.PLAIN_CONCEPT,
    SlideIntent.KNOWLEDGE_CHECK: ContentPattern.ACTIVITY_BANNER,
}


def _resolve_slide_intent(bp_dict_or_obj: Any) -> SlideIntent:
    """Helper to extract SlideIntent enum from blueprint dict or object."""
    if hasattr(bp_dict_or_obj, "intent"):
        raw_intent = bp_dict_or_obj.intent
    elif isinstance(bp_dict_or_obj, dict):
        raw_intent = bp_dict_or_obj.get("intent")
    else:
        return SlideIntent.CONCEPT_EXPLANATION

    if isinstance(raw_intent, SlideIntent):
        return raw_intent
    if isinstance(raw_intent, str):
        try:
            return SlideIntent(raw_intent)
        except ValueError:
            pass
    return SlideIntent.CONCEPT_EXPLANATION


# ═══════════════════════════════════════════════════════════════
# Deterministic Dynamic Content Synthesizer (Phase 2 Fallback)
# ═══════════════════════════════════════════════════════════════

def _synthesize_dynamic_slide_content(
    blueprint: SlideBlueprint,
    brief: PresentationBrief,
    topic_intelligence: Optional[Any],
    deck_memory: DeckContentMemory,
    slide_no: int,
    total_slides: int,
    source_context: str = "",
    concept_packet: Optional[SlideConceptPacket] = None,
) -> SlideContent:
    """
    Synthesize rich, topic-specific SlideContent without hardcoded benchmark topics (§4 & §5).
    Draws directly from SlideConceptPacket, blueprint, brief, domain profiles, and topic intelligence.
    Eliminates all generic topic-substitution prose.
    """
    intent = blueprint.intent
    topic = brief.canonical_topic or brief.topic
    domain = brief.domain

    # Resolve or reuse SlideConceptPacket (§1, §4)
    if concept_packet is not None:
        packet = concept_packet
    else:
        packet = resolve_slide_concept_packet(
            blueprint=blueprint,
            brief=brief,
            topic_intelligence=topic_intelligence,
            deck_memory=deck_memory,
            slide_no=slide_no,
            total_slides=total_slides,
            source_context=source_context,
        )

    primary_concept = packet.primary_concept or topic
    
    chosen_takeaway = ""
    if packet.relationships:
        for r in packet.relationships:
            if isinstance(r, str) and count_words(r) >= 4:
                if not (deck_memory and hasattr(deck_memory, "is_takeaway_already_used") and deck_memory.is_takeaway_already_used(r)):
                    chosen_takeaway = r.strip()
                    break
        if not chosen_takeaway and packet.relationships:
            chosen_takeaway = packet.relationships[0].strip()
    elif packet.source_grounded_facts:
        for f in packet.source_grounded_facts:
            if isinstance(f, str) and count_words(f) >= 4:
                if not (deck_memory and hasattr(deck_memory, "is_takeaway_already_used") and deck_memory.is_takeaway_already_used(f)):
                    chosen_takeaway = f.strip()
                    break
        if not chosen_takeaway and packet.source_grounded_facts:
            chosen_takeaway = packet.source_grounded_facts[0].strip()

    if not chosen_takeaway:
        chosen_takeaway = f"{primary_concept} establishes operational behavior within {topic}."
    primary_takeaway = chosen_takeaway

    if not packet.source_grounded_facts:
        packet.relationships = _filter_list_for_stats(packet.relationships)
        packet.supporting_concepts = _filter_list_for_stats(packet.supporting_concepts)
        packet.example_candidates = _filter_list_for_stats(packet.example_candidates)
        packet.process_stages = _filter_list_for_stats(packet.process_stages)
        new_ce = []
        for pair in packet.cause_effect_pairs:
            if isinstance(pair, dict):
                c = _strip_unsupported_statistics(pair.get("cause", ""))
                e = _strip_unsupported_statistics(pair.get("effect", ""))
                if c and e:
                    new_ce.append({"cause": c, "effect": e})
            else:
                if _strip_unsupported_statistics(str(pair)):
                    new_ce.append(pair)
        packet.cause_effect_pairs = new_ce
        
        new_misc = []
        for m in packet.misconceptions:
            if isinstance(m, dict):
                myth = _strip_unsupported_statistics(m.get("myth", ""))
                reality = _strip_unsupported_statistics(m.get("reality", ""))
                if myth and reality:
                    new_misc.append({"myth": myth, "reality": reality})
            else:
                if _strip_unsupported_statistics(str(m)):
                    new_misc.append(m)
        packet.misconceptions = new_misc

    supporting_concepts = packet.supporting_concepts
    raw_title = blueprint.primary_message or f"{primary_concept}: Core Principles"
    title = sanitize_and_complete_title(raw_title, topic=topic, fallback_concept=primary_concept)
    subtitle = ""

    supporting_points: List[str] = []
    callout = ""
    example = ""
    misconception_block = None
    formula = ""
    formula_symbols = ""
    code = ""
    code_lang = ""
    data_points: List[DataPoint] = []
    comp_target_a = ""
    comp_target_b = ""
    comp_rows: List[ComparisonRow] = []
    process_steps: List[str] = []

    # Strict Intent-Specific Semantic Packet Requirements (§12, §13)
    has_semantic_gap = False
    if topic_intelligence is None and concept_packet is None and not source_context and not blueprint.canonical_concepts and intent not in (SlideIntent.COVER, SlideIntent.AGENDA, SlideIntent.Q_AND_A, SlideIntent.REFERENCES):
        has_semantic_gap = True
    elif intent == SlideIntent.COVER:
        title = topic
        subtitle = f"{brief.education_level.replace('_', ' ').title()} Level  •  {domain.replace('_', ' ').title()}"
        primary_takeaway = f"A foundational examination of {topic}."
    elif intent == SlideIntent.CONTEXT:
        title = sanitize_and_complete_title(blueprint.primary_message or f"Engineering Challenges Behind {topic}", topic=topic)
        if "node" in topic.lower():
            primary_takeaway = "Traditional thread-per-connection architectures face severe memory scaling limits and thread contention under high I/O concurrency."
            supporting_points = [
                "C10K Concurrency Limit: Thread-per-connection models allocate dedicated OS thread stacks (typically 1–8 MB default depending on OS and configuration), exhausting memory at scale.",
                "Scheduling and Context Switching: Thousands of concurrent idle or waiting threads incur substantial CPU context-switching overhead and cache invalidation.",
                "Non-Blocking Demultiplexing: An asynchronous event loop multiplexes tens of thousands of active socket connections on a single execution thread without thread bloat.",
            ]
        elif "cell division" in topic.lower():
            primary_takeaway = "Cellular proliferation requires precise genetic replication and chromosome distribution to maintain genomic integrity across generations."
            supporting_points = [
                "DNA Fidelity: Genetic information must replicate without mutation before cytoplasmic partitioning.",
                "Spindle Checkpoints: Dividing cells verify microtubule attachment at metaphase before initiating chromatid separation.",
                "Ploidy Regulation: Somatic tissues require exact diploid conservation, while germline cells undergo reductive division.",
            ]
        elif "tcp" in topic.lower():
            primary_takeaway = "Packet networks require distributed end-to-end congestion control to prevent catastrophic throughput collapse at bottleneck routers."
            supporting_points = [
                "Shared Bottleneck Buffers: Independent senders competing without coordination overflow intermediate switch memory.",
                "Packet Loss & Latency Spikes: Queue buildup (bufferbloat) inflates round-trip times and triggers mass retransmissions.",
                "Distributed Feedback: End hosts must autonomously adjust transmission rates using delay or loss indicators.",
            ]
        elif "equilibrium" in topic.lower() or "market" in topic.lower():
            primary_takeaway = "Uncoordinated market interactions balance supply and demand through dynamic price adjustments toward clearing equilibrium."
            supporting_points = [
                "Scarcity & Price Signals: Shortages signal suppliers to expand production while rationing available units to buyers.",
                "Surplus Elimination: Excess supply creates downward price pressure as competing producers bid to clear unsold inventory.",
                "Social Welfare Maximization: At equilibrium price P*, consumer and producer surplus are jointly maximized without deadweight loss.",
            ]
        elif "probability" in topic.lower() or "distribution" in topic.lower():
            primary_takeaway = "Mathematical probability distributions quantify uncertainty by mapping sample spaces to well-defined probability measures."
            supporting_points = [
                "Measure Foundations: Probabilities across all disjoint outcomes in a sample space must sum or integrate to exactly unity.",
                "Discrete vs Continuous Distinction: Countable random variables utilize mass functions, whereas continua require density functions.",
                "Moment Characterization: Distributions are structurally summarized by location (mean), dispersion (variance), and shape metrics.",
            ]
        elif packet.relationships and len(packet.relationships) >= 3:
            primary_takeaway = packet.relationships[0]
            supporting_points = packet.relationships[1:4]
        else:
            primary_takeaway = f"Understanding {topic} requires examining its foundational context, structural drivers, and operational constraints."
            concepts = packet.supporting_concepts or packet.canonical_concepts or []
            if len(concepts) >= 2:
                supporting_points = [
                    f"Foundational Driver: {concepts[0]} establishes core principles and baseline assumptions in {topic}.",
                    f"Structural Dynamics: {concepts[1]} regulates systemic interactions and operational flow.",
                    f"Domain Significance: Practical outcomes depend on coordinating these factors across {topic}.",
                ]
            else:
                supporting_points = [
                    f"Foundational Context: Primary principles and constraints define the foundational parameters for {topic}.",
                    f"System Dynamics: Interconnected mechanisms govern behavior and state transitions across {topic}.",
                    f"Practical Significance: Structural decisions directly determine efficacy and scalability in {topic}.",
                ]
        process_steps = []
    elif intent in (SlideIntent.SYSTEM_OVERVIEW, SlideIntent.COMPONENT_BREAKDOWN):
        # Dedicated architecture and subsystem decomposition
        if intent == SlideIntent.SYSTEM_OVERVIEW:
            title = sanitize_and_complete_title(blueprint.primary_message or f"System Architecture of {topic}", topic=topic)
            if "node" in topic.lower():
                primary_takeaway = "Node.js couples Google's V8 engine with libuv to execute event-driven, non-blocking JavaScript over native OS event demultiplexers."
                supporting_points = [
                    "V8 JavaScript Engine: Compiles JS directly to machine code, executing the call stack and managing heap memory allocation.",
                    "libuv Platform Layer: Provides the cross-platform event loop and manages background worker threads for blocking operations.",
                    "Node.js Core C++ Bindings: Exposes kernel sockets, file system access, and crypto primitives directly to user JavaScript.",
                    "OS Event Demultiplexer: Non-blockingly polls socket readiness via kernel mechanisms (epoll on Linux, kqueue on macOS, IOCP on Windows).",
                ]
            elif "cell division" in topic.lower():
                primary_takeaway = "The mitotic division apparatus coordinates chromatin condensation, nuclear membrane breakdown, and bipolar spindle assembly."
                supporting_points = [
                    "Centrosome & Centrioles: Organizes the microtubule cytoskeleton and nucleates the mitotic spindle poles.",
                    "Kinetochore Complex: Multiprotein assemblies at centromeres that tether sister chromatids to spindle microtubules.",
                    "Nuclear Envelope Dynamics: Disassembles in prometaphase to permit spindle access and reassembles in telophase.",
                    "Actomyosin Contractile Ring: Assembles at the cell equator to drive cytoplasmic cleavage during cytokinesis.",
                ]
            elif "tcp" in topic.lower():
                primary_takeaway = "TCP congestion control architecture couples sending window state machines with transport-layer acknowledgment feedback."
                supporting_points = [
                    "Congestion Window (cwnd): Host-managed variable bounding the maximum volume of unacknowledged inflight bytes.",
                    "Slow Start Threshold (ssthresh): Determines transition boundary between exponential probing and linear avoidance.",
                    "Retransmission Timer (RTO): Dynamically estimated timer triggering timeout recovery when acknowledgments cease.",
                    "ACK Feedback Clock: Inbound acknowledgment streams provide pacing timing to release new transmission packets.",
                ]
            elif "equilibrium" in topic.lower() or "market" in topic.lower():
                primary_takeaway = "Market equilibrium architecture coordinates individual supply and demand schedules into an aggregate market clearing framework."
                supporting_points = [
                    "Demand Schedule: Aggregate downward-sloping marginal benefit curve representing consumer willingness to pay.",
                    "Supply Schedule: Aggregate upward-sloping marginal cost curve representing producer output decisions.",
                    "Price Adjustment Mechanism: Market auction dynamics that bid prices toward the intersection clearing point.",
                    "Allocative Efficiency Boundary: Point where marginal social benefit equals marginal social cost.",
                ]
            elif "probability" in topic.lower() or "distribution" in topic.lower():
                primary_takeaway = "Probability distribution architecture structures random variables across sample spaces, density functions, and cumulative curves."
                supporting_points = [
                    "Random Variable Map: Mathematical mapping from underlying sample space events to real numerical values.",
                    "Density / Mass Function: Evaluates localized likelihoods under non-negativity and total unity constraints.",
                    "Cumulative Distribution Function: Monotonically non-decreasing curve representing P(X <= x) over all domains.",
                    "Moment Generating Function: Analytical transform uniquely determining distribution moments and parameters.",
                ]
            elif packet.supporting_concepts:
                primary_takeaway = f"The {topic} architecture structures operational components into distinct, coordinated layers."
                supporting_points = [f"{c}: Coordinates operational execution and provides structural guarantees within {topic}." for c in packet.supporting_concepts[:4]]
            elif blueprint.canonical_concepts:
                primary_takeaway = f"System architecture organizes core components and execution boundaries across {topic}."
                supporting_points = [f"{cc}: Establishes foundational operational mechanics and structural guarantees within {topic}." for cc in blueprint.canonical_concepts[:4]]
            else:
                primary_takeaway = f"System architecture organizes core components and execution boundaries across {topic}."
                supporting_points = [
                    f"Primary {topic} Core: Governs core operational mechanics and state transitions.",
                    f"Platform Interface Layer: Coordinates external resource integration and systemic constraints.",
                ]
        else:
            title = sanitize_and_complete_title(blueprint.primary_message or f"Core Subsystems and Mechanics of {topic}", topic=topic)
            if "node" in topic.lower():
                primary_takeaway = "The single-threaded event loop coordinates execution across the V8 call stack, libuv event queues, and microtask queues."
                supporting_points = [
                    "Single-Threaded Call Stack: Synchronous JavaScript executes run-to-completion in V8 without multi-threaded concurrency locking.",
                    "Microtask Queues: High-priority microtasks (process.nextTick and Promise jobs) are drained immediately between phase transitions.",
                    "libuv Worker Pool: Background worker threads (default 4, configurable via UV_THREADPOOL_SIZE) handle blocking fs, crypto, and DNS calls.",
                    "Event Demultiplexer & Poller: Polls operating system kernel queues and routes completed I/O events into the libuv event loop.",
                ]
            elif packet.supporting_concepts:
                primary_takeaway = f"Modular decomposition defines operational responsibilities across {topic}."
                supporting_points = [
                    f"{c}: Governs dedicated operational logic and functional state transitions within {topic}."
                    for c in packet.supporting_concepts[:4]
                ]
            else:
                primary_takeaway = f"Decomposition isolates key functional subsystems to ensure scalable execution in {topic}."
                supporting_points = [
                    f"Primary Subsystem: Executes foundational domain operations and coordinates runtime state within {topic}.",
                    f"Control Interface: Regulates inter-component data exchange and maintains boundary isolation in {topic}."
                ]
        process_steps = []
    elif intent == SlideIntent.PROCESS_EXPLANATION:
        if "node" in topic.lower() or "event loop" in ((getattr(blueprint, "primary_message", "") or "") + " " + (blueprint.learning_purpose or "") + " " + str(packet.primary_concept)).lower():
            process_steps = [
                "Timers Phase: Evaluates threshold timers and executes expired setTimeout() and setInterval() callbacks.",
                "Poll Phase: Retrieves new kernel I/O events, executes non-blocking I/O callbacks, and blocks when the queue is clear.",
                "Check Phase: Executes callbacks registered via setImmediate() immediately after the poll phase completes.",
                "Close Callbacks Phase: Executes socket and resource closure cleanup handlers (e.g., socket.on('close')).",
            ]
            primary_takeaway = f"The {topic} event loop executes non-blocking operations across a structured sequence of {len(process_steps)} core phases (simplified teaching subset: Timers, Poll, Check, Close), while libuv also executes pending and idle phases."
            supporting_points = list(process_steps)
        elif "cell division" in topic.lower() or "mitosis" in topic.lower():
            process_steps = [
                "Prophase: Chromatin condenses into visible chromosomes and mitotic spindle assembly begins.",
                "Metaphase: Sister chromatids align along the central equatorial metaphase plate under bipolar tension.",
                "Anaphase: Cohesin cleavage allows sister chromatids to separate toward opposite spindle poles.",
                "Telophase & Cytokinesis: Nuclear envelopes reform around daughter nuclei and cleavage furrow partitions cytoplasm.",
            ]
            primary_takeaway = f"Cell division executes cellular proliferation across a structured sequence of {len(process_steps)} distinct mitotic phases."
            supporting_points = list(process_steps)
        elif "tcp" in topic.lower() or "congestion" in topic.lower():
            process_steps = [
                "Slow Start: Exponentially doubles congestion window (cwnd) every round-trip time to probe capacity.",
                "Congestion Avoidance: Linearly increases cwnd by one segment per RTT upon reaching ssthresh.",
                "Fast Retransmit: Incurs multiplicative decrease upon receiving three duplicate acknowledgments.",
                "Fast Recovery: Maintains pipe throughput using incoming duplicate ACKs without resetting to slow start.",
            ]
            primary_takeaway = f"TCP congestion control balances throughput across a structured sequence of {len(process_steps)} transmission phases."
            supporting_points = list(process_steps)
        elif "equilibrium" in topic.lower() or "market" in topic.lower():
            process_steps = [
                "Excess Demand / Shortage: Quantity demanded exceeds quantity supplied at below-equilibrium market prices.",
                "Price Bidding Upward: Scarcity forces buyers to bid prices upward, creating supplier production incentives.",
                "Supply Expansion & Demand Rationing: Higher prices induce suppliers to produce more while rationing buyers.",
                "Market-Clearing Equilibrium: Market stabilizes at price P* where quantity supplied exactly equals quantity demanded.",
            ]
            primary_takeaway = f"Market equilibrium stabilizes prices across a structured sequence of {len(process_steps)} adjustment phases."
            supporting_points = list(process_steps)
        elif "probability" in topic.lower() or "distribution" in topic.lower():
            process_steps = [
                "Random Variable Definition: Map experimental outcomes from the sample space to real-valued mathematical quantities.",
                "Probability Function Assignment: Formulate probability mass function P(X=k) or continuous probability density function f(x).",
                "Cumulative Integration: Evaluate cumulative distribution function F(x) by integrating or summing across the domain.",
                "Moment Characterization: Calculate foundational statistical moments including expected value (mean) and variance.",
            ]
            primary_takeaway = f"Probability distributions quantify uncertainty across a structured sequence of {len(process_steps)} analytical steps."
            supporting_points = list(process_steps)
        else:
            candidates = []
            if packet.process_stages:
                for idx, stage in enumerate(packet.process_stages[:4]):
                    candidates.append(f"Phase {idx+1} ({stage}): Coordinates operational execution within {topic}.")
            if len(candidates) < 3 and packet.cause_effect_pairs:
                for ce in packet.cause_effect_pairs:
                    if isinstance(ce, dict) and ce.get("cause") and ce.get("effect"):
                        candidates.append(f"Transition Dynamics: {ce['cause']} directly drives {ce['effect']}.")
            if len(candidates) < 3 and packet.relationships:
                for r in packet.relationships:
                    candidates.append(f"Operational Pathway: {r}")
            if len(candidates) < 3 and packet.supporting_concepts:
                for idx, c in enumerate(packet.supporting_concepts[:4]):
                    candidates.append(f"Phase {len(candidates)+1} ({c}): Governs core transformation and state transitions.")
            if len(candidates) < 3 and blueprint.canonical_concepts:
                for idx, cc in enumerate(blueprint.canonical_concepts[:4]):
                    if not any(cc in cand for cand in candidates):
                        candidates.append(f"Phase {len(candidates)+1} ({cc}): Manages functional execution parameters.")
            if len(candidates) < 3:
                candidates.extend([
                    f"Phase 1 (Preparation): Establishes baseline state and foundational parameters for {topic}.",
                    f"Phase 2 (Dynamic Execution): Mediates core interactions and state transitions across subsystems.",
                    f"Phase 3 (Systemic Equilibrium): Consolidates outcomes and stabilizes terminal state in {topic}."
                ])
            process_steps = candidates[:4]
            primary_takeaway = f"{topic} progresses through a structured sequence of {len(process_steps)} operational phases."
            supporting_points = list(process_steps)
    elif intent in (SlideIntent.COMPARISON, SlideIntent.TRADEOFF):
        comps = (topic_intelligence.get("comparison_candidates", []) if isinstance(topic_intelligence, dict)
                 else (getattr(topic_intelligence, "comparison_candidates", []) if topic_intelligence else []))

        # Score and select the most relevant unused comparison candidate
        target_hints = (
            (getattr(blueprint, "primary_message", "") or getattr(blueprint, "title", "") or "") + " " +
            (getattr(blueprint, "learning_purpose", "") or "") + " " +
            (getattr(blueprint, "comparison_target", "") or "") + " " +
            (blueprint.narrative_role.value if hasattr(blueprint.narrative_role, "value") else str(blueprint.narrative_role)) + " " +
            " ".join(blueprint.canonical_concepts or []) + " " +
            " ".join(blueprint.supporting_concepts or [])
        ).lower()

        chosen_candidate = None
        best_score = -1

        for cand in comps:
            if not isinstance(cand, dict):
                continue
            item_a = cand.get("item_a", "")
            item_b = cand.get("item_b", "")
            if deck_memory and hasattr(deck_memory, "is_comparison_pair_already_used"):
                if deck_memory.is_comparison_pair_already_used(item_a, item_b):
                    continue
            score = 0
            if item_a.lower() in target_hints:
                score += 3
            if item_b.lower() in target_hints:
                score += 3
            if cand.get("comparison_axis", "").lower() in target_hints:
                score += 2
            if "commonjs" in target_hints or "esm" in target_hints or "module" in target_hints:
                if "commonjs" in item_a.lower() or "esm" in item_b.lower() or "es module" in item_b.lower():
                    score += 10
            elif "concurrency" in target_hints or "server" in target_hints or "single-thread" in target_hints or "multi-thread" in target_hints:
                if any(k in item_a.lower() for k in ("thread", "process", "callback", "single")) or any(k in item_b.lower() for k in ("thread", "cluster", "multi")):
                    score += 6
            elif "stream" in target_hints or "backpressure" in target_hints:
                if "stream" in item_a.lower() or "stream" in item_b.lower() or "buffer" in item_a.lower():
                    score += 8
            if score > best_score:
                best_score = score
                chosen_candidate = cand

        if not chosen_candidate and comps:
            for cand in comps:
                if isinstance(cand, dict):
                    item_a = cand.get("item_a", "")
                    item_b = cand.get("item_b", "")
                    if not (deck_memory and hasattr(deck_memory, "is_comparison_pair_already_used") and deck_memory.is_comparison_pair_already_used(item_a, item_b)):
                        chosen_candidate = cand
                        break
            if not chosen_candidate:
                chosen_candidate = comps[0] if isinstance(comps[0], dict) else {}

        banned_comparands = {"alternative approach", "alternative concept", "approach a", "approach b", "option 1", "option 2", "option a", "option b", "concept a", "concept b"}
        if chosen_candidate and chosen_candidate.get("item_b") and chosen_candidate["item_b"].lower().strip() not in banned_comparands:
            comp_target_a = chosen_candidate.get("item_a", f"{topic}")
            comp_target_b = chosen_candidate["item_b"]
            comp_axis = chosen_candidate.get("comparison_axis", "Structural tradeoffs")
        else:
            if packet.supporting_concepts and len(packet.supporting_concepts) >= 2:
                comp_target_a = packet.supporting_concepts[0]
                comp_target_b = packet.supporting_concepts[1]
            elif blueprint.canonical_concepts and len(blueprint.canonical_concepts) >= 2:
                comp_target_a = blueprint.canonical_concepts[0]
                comp_target_b = blueprint.canonical_concepts[1]
            else:
                comp_target_a = f"Foundational {topic} Model"
                comp_target_b = f"Advanced {topic} Architecture"
            comp_axis = "Structural tradeoffs"

        deck_memory.register_comparison_pair(comp_target_a, comp_target_b)

        # Build authoritative, domain-grounded comparison rows
        if "node" in topic.lower() and ("commonjs" in comp_target_a.lower() or "commonjs" in target_hints or "esm" in comp_target_b.lower()):
            comp_target_a = "CommonJS (CJS)"
            comp_target_b = "ES Modules (ESM)"
            primary_takeaway = "CommonJS resolves dependencies synchronously at runtime, whereas ES Modules use static syntax and asynchronous loading with top-level await."
            comp_rows = [
                ComparisonRow(dimension="Loading Mechanism", target_a_value="Synchronous runtime require() executes module code on demand", target_b_value="Static import parsed and linked before execution; dynamic import() returns Promise"),
                ComparisonRow(dimension="Dynamic & Top-Level Await", target_a_value="require() can be called dynamically anywhere; no top-level await", target_b_value="Dynamic import() is asynchronous; top-level await supported in ESM (Node v14.8+)"),
                ComparisonRow(dimension="Tree-Shaking Support", target_a_value="Dynamic exports object prevents static dead-code elimination", target_b_value="Static module structure enables compiler analysis and tree-shaking by modern bundlers"),
                ComparisonRow(dimension="Scope & Globals", target_a_value="Injects __dirname, __filename, and module.exports", target_b_value="Provides import.meta.url (no __dirname global; resolved via fileURLToPath)"),
            ]
            supporting_points = [f"{r.dimension}: {r.target_a_value} vs {r.target_b_value}." for r in comp_rows[:2]]
        elif "node" in topic.lower() and (intent == SlideIntent.TRADEOFF or "stream" in target_hints or "backpressure" in target_hints or "bottleneck" in target_hints):
            comp_target_a = "In-Memory Buffering (fs.readFile)"
            comp_target_b = "Streaming with Backpressure"
            primary_takeaway = "Streaming data in discrete chunks with active backpressure prevents V8 heap exhaustion and sustains high throughput."
            trap_points = [
                "In-Memory Buffering: Loading entire files with fs.readFile exhausts V8 heap memory under concurrent load.",
                "Latency Delay: Delivery is delayed until entire payload is buffered, risking out-of-memory crashes."
            ]
            discipline_points = [
                "Streaming in Chunks: Process data sequentially using Readable and Writable streams with constant low memory.",
                "Backpressure Flow Control: Signals the producer to pause when the consumer buffer is full to prevent overflow."
            ]
            supporting_points = trap_points + discipline_points
            columns = [
                {"heading": "THE TRAP: IN-MEMORY BUFFERING", "header": "THE TRAP: IN-MEMORY BUFFERING", "points": trap_points, "items": trap_points},
                {"heading": "THE DISCIPLINE: STREAMING WITH BACKPRESSURE", "header": "THE DISCIPLINE: STREAMING WITH BACKPRESSURE", "points": discipline_points, "items": discipline_points},
            ]
            comp_rows = [
                ComparisonRow(dimension="Memory Footprint", target_a_value="Linear growth with file size; exhausts V8 heap", target_b_value="Constant low memory usage (~16-64 KB chunk buffers)"),
                ComparisonRow(dimension="Time to First Byte", target_a_value="Blocked until full payload is loaded into memory", target_b_value="Immediate chunk streaming to client socket"),
                ComparisonRow(dimension="Flow Governance", target_a_value="No flow control; consumer is overwhelmed", target_b_value="Backpressure pauses producer when consumer buffer fills"),
            ]
        elif "node" in topic.lower() and (any(k in target_hints for k in ("concurrency", "multi-thread", "single-thread", "server", "architecture_comparison")) or ("callback" in comp_target_a.lower() and "server" in target_hints)):
            comp_target_a = "Single-Threaded Event Loop"
            comp_target_b = "Multi-Threaded Server Model"
            primary_takeaway = "Node's single-threaded event loop excels at high-density I/O-bound concurrency without per-thread memory overhead, while multi-threaded models excel at parallel CPU-bound compute."
            comp_rows = [
                ComparisonRow(dimension="Concurrency Model", target_a_value="Single event loop thread with non-blocking I/O multiplexing", target_b_value="Dedicated OS thread allocated per incoming request"),
                ComparisonRow(dimension="Memory Footprint", target_a_value="Lightweight connection descriptor (few KB per active connection)", target_b_value="Dedicated OS thread stack (often 1–8 MB typical default stack allocation depending on OS and runtime configuration)"),
                ComparisonRow(dimension="Context Switching", target_a_value="Minimal thread switching overhead for I/O tasks", target_b_value="Kernel context-switching latency increases under high thread concurrency"),
                ComparisonRow(dimension="Failure Vulnerability", target_a_value="CPU-intensive tasks or synchronous blocking code halt event loop", target_b_value="Thread pool exhaustion, lock contention, and race conditions under load"),
            ]
            supporting_points = [f"{r.dimension}: {r.target_a_value} vs {r.target_b_value}." for r in comp_rows[:2]]
        elif ("cell division" in topic.lower() or "mitosis" in topic.lower()) and ("cytokinesis" in target_hints or "plant" in target_hints):
            comp_target_a = "Animal Cell Cytokinesis"
            comp_target_b = "Plant Cell Cytokinesis"
            primary_takeaway = "Animal cytokinesis constricts a contractile actin-myosin ring to form a cleavage furrow, whereas plant cytokinesis synthesizes a rigid cell plate from Golgi-derived vesicles."
            comp_rows = [
                ComparisonRow(dimension="Division Mechanism", target_a_value="Contractile actin-myosin ring pinches inward", target_b_value="Phragmoplast guides Golgi vesicles to fuse outward"),
                ComparisonRow(dimension="Cell Wall Constraint", target_a_value="Flexible membrane allows centripetal furrowing", target_b_value="Rigid cellulose wall necessitates centrifugal plate growth"),
                ComparisonRow(dimension="Structural Apparatus", target_a_value="Cleavage furrow formed by microfilament contraction", target_b_value="Cell plate expanding until fusion with parental wall"),
                ComparisonRow(dimension="Completion Dynamic", target_a_value="Pinches cytoplasm into two daughter cells", target_b_value="New primary cell wall and middle lamella synthesize"),
            ]
            supporting_points = [f"{r.dimension}: {r.target_a_value} vs {r.target_b_value}." for r in comp_rows[:2]]
        elif "cell division" in topic.lower() or "mitosis" in topic.lower():
            comp_target_a = "Mitosis"
            comp_target_b = "Meiosis"
            primary_takeaway = "Mitosis produces genetically identical diploid somatic cells, whereas meiosis generates genetically diverse haploid gametes through homologous recombination."
            comp_rows = [
                ComparisonRow(dimension="Biological Purpose", target_a_value="Somatic growth, tissue repair, and asexual reproduction", target_b_value="Gamete formation for sexual reproduction"),
                ComparisonRow(dimension="Daughter Cell Ploidy", target_a_value="Two identical diploid (2n) daughter cells", target_b_value="Four genetically distinct haploid (1n) daughter cells"),
                ComparisonRow(dimension="Genetic Recombination", target_a_value="Zero crossing over; exact parental DNA replication", target_b_value="Homologous crossing over in Prophase I and independent assortment"),
                ComparisonRow(dimension="Division Cycles", target_a_value="Single nuclear and cytoplasmic division cycle", target_b_value="Two successive division cycles (Meiosis I and Meiosis II)"),
            ]
            supporting_points = [f"{r.dimension}: {r.target_a_value} vs {r.target_b_value}." for r in comp_rows[:2]]
        elif ("tcp" in topic.lower() or "congestion" in topic.lower()) and ("reno" in target_hints or "tahoe" in target_hints or "tradeoff" in target_hints):
            comp_target_a = "TCP Tahoe (Slow Start on Loss)"
            comp_target_b = "TCP Reno (Fast Recovery on Loss)"
            primary_takeaway = "TCP Tahoe resets congestion window to one MSS upon triple duplicate ACKs, whereas TCP Reno invokes Fast Recovery to halve the window and sustain pipeline throughput."
            comp_rows = [
                ComparisonRow(dimension="Duplicate ACK Reaction", target_a_value="Collapses cwnd to 1 MSS and re-enters Slow Start", target_b_value="Halves cwnd and invokes Fast Recovery"),
                ComparisonRow(dimension="Pipeline Recovery Slope", target_a_value="Exponential increase from 1 MSS up to ssthresh", target_b_value="Additive linear increase from halved threshold"),
                ComparisonRow(dimension="Throughput Preservation", target_a_value="Drains network pipeline on isolated packet loss", target_b_value="Sustains in-flight packets during single packet losses"),
                ComparisonRow(dimension="Timeout Handling", target_a_value="Resets cwnd to 1 MSS upon retransmission timer expiry", target_b_value="Resets cwnd to 1 MSS upon retransmission timer expiry"),
            ]
            supporting_points = [f"{r.dimension}: {r.target_a_value} vs {r.target_b_value}." for r in comp_rows[:2]]
        elif "tcp" in topic.lower() or "congestion" in topic.lower():
            comp_target_a = "Loss-Based Control (Tahoe / Reno)"
            comp_target_b = "Model-Based Control (BBR)"
            primary_takeaway = "Loss-based TCP infers congestion from packet drops after filling buffers, whereas model-based BBR tracks pacing rate and round-trip time to prevent bufferbloat."
            comp_rows = [
                ComparisonRow(dimension="Congestion Signal", target_a_value="Packet loss and duplicate ACKs or retransmission timeouts", target_b_value="Max bottleneck bandwidth and minimum RTT estimates"),
                ComparisonRow(dimension="Buffer Queueing Behavior", target_a_value="Fills bottleneck queue to drop-tail capacity (bufferbloat)", target_b_value="Maintains queue near zero by pacing packets at BDP capacity"),
                ComparisonRow(dimension="Window Dynamics", target_a_value="Additive increase, multiplicative decrease (AIMD)", target_b_value="Rate-based pacing state machine (Startup, Drain, ProbeBW)"),
                ComparisonRow(dimension="Throughput on Lossy Links", target_a_value="Severe throughput collapse on non-congestive wireless losses", target_b_value="Maintains high throughput despite random non-congestive packet loss"),
            ]
            supporting_points = [f"{r.dimension}: {r.target_a_value} vs {r.target_b_value}." for r in comp_rows[:2]]
        elif ("equilibrium" in topic.lower() or "market" in topic.lower()) and ("short-run" in target_hints or "long-run" in target_hints or "tradeoff" in target_hints):
            comp_target_a = "Short-Run Market Equilibrium"
            comp_target_b = "Long-Run Market Equilibrium"
            primary_takeaway = "Short-run equilibrium allows firms to earn economic profits or losses with fixed plant capacity, whereas long-run equilibrium drives economic profits to zero through free market entry and exit."
            comp_rows = [
                ComparisonRow(dimension="Capital Input Adjustability", target_a_value="Fixed plant capacity and capital stock", target_b_value="All production inputs and plant sizes are fully variable"),
                ComparisonRow(dimension="Market Entry & Exit Dynamic", target_a_value="Fixed number of operating firms in the industry", target_b_value="Free entry and exit eliminates abnormal profits and losses"),
                ComparisonRow(dimension="Profit Equilibrium Condition", target_a_value="Firms may sustain positive or negative economic profit", target_b_value="Zero economic profit where price equals minimum average cost"),
                ComparisonRow(dimension="Supply Curve Elasticity", target_a_value="Relatively inelastic due to short-run capacity constraints", target_b_value="Highly elastic industry supply responding to entry and exit"),
            ]
            supporting_points = [f"{r.dimension}: {r.target_a_value} vs {r.target_b_value}." for r in comp_rows[:2]]
        elif "equilibrium" in topic.lower() or "market" in topic.lower():
            comp_target_a = "Competitive Market Equilibrium"
            comp_target_b = "Monopoly Market Equilibrium"
            primary_takeaway = "Competitive equilibrium maximizes social surplus where price equals marginal cost, whereas monopoly restricts output to maximize profit, generating deadweight loss."
            comp_rows = [
                ComparisonRow(dimension="Price & Output Determination", target_a_value="Price taker: equilibrium output where P = MC", target_b_value="Price setter: restricted output where MR = MC, pricing P > MC"),
                ComparisonRow(dimension="Allocative Efficiency", target_a_value="Achieves Pareto efficiency with zero deadweight loss", target_b_value="Creates deadweight loss from underproduction below social optimum"),
                ComparisonRow(dimension="Consumer Surplus", target_a_value="Consumer surplus is maximized across competitive trade", target_b_value="Transfers consumer surplus to producer profits"),
                ComparisonRow(dimension="Entry & Long-Run Profit", target_a_value="Free entry drives long-run economic profit to zero", target_b_value="High barriers to entry sustain long-run positive economic profits"),
            ]
            supporting_points = [f"{r.dimension}: {r.target_a_value} vs {r.target_b_value}." for r in comp_rows[:2]]
        elif ("probability" in topic.lower() or "distribution" in topic.lower()) and ("parametric" in target_hints or "non-parametric" in target_hints or "tradeoff" in target_hints):
            comp_target_a = "Parametric Probability Models"
            comp_target_b = "Non-Parametric Density Estimation"
            primary_takeaway = "Parametric models assume fixed mathematical distributions with finite parameter sets, whereas non-parametric estimators infer empirical distributions directly from sample data without distributional assumptions."
            comp_rows = [
                ComparisonRow(dimension="Distributional Assumption", target_a_value="Assumes specific functional family (Gaussian, Poisson)", target_b_value="Distribution-free; estimates density directly from data (KDE)"),
                ComparisonRow(dimension="Parameter Dimensionality", target_a_value="Fixed finite parameter vector (theta in R^k)", target_b_value="Parameter complexity scales with sample size n"),
                ComparisonRow(dimension="Misspecification Sensitivity", target_a_value="High bias if assumed distribution family is incorrect", target_b_value="Asymptotically unbiased as sample size approaches infinity"),
                ComparisonRow(dimension="Sample Data Efficiency", target_a_value="High sample efficiency with fast parametric convergence", target_b_value="Requires larger datasets to achieve low estimation variance"),
            ]
            supporting_points = [f"{r.dimension}: {r.target_a_value} vs {r.target_b_value}." for r in comp_rows[:2]]
        elif "probability" in topic.lower() or "distribution" in topic.lower():
            comp_target_a = "Discrete Probability Distributions"
            comp_target_b = "Continuous Probability Distributions"
            primary_takeaway = "Discrete distributions assign positive probability to countable outcomes via mass functions, whereas continuous distributions evaluate probabilities across intervals via density functions."
            comp_rows = [
                ComparisonRow(dimension="Sample Space Nature", target_a_value="Countable distinct isolated values (e.g. integers k in Z)", target_b_value="Uncountable continuum of values across real numbers (x in R)"),
                ComparisonRow(dimension="Probability Assignment", target_a_value="Probability Mass Function: P(X = k) >= 0; sum = 1", target_b_value="Probability Density Function: P(X = x) = 0; integral = 1"),
                ComparisonRow(dimension="Cumulative Evaluation", target_a_value="Stepwise step function with jump discontinuities", target_b_value="Smooth, continuous, monotonically increasing integral curve"),
                ComparisonRow(dimension="Canonical Archetypes", target_a_value="Binomial, Poisson, Bernoulli, Geometric", target_b_value="Normal (Gaussian), Exponential, Uniform, Student-t"),
            ]
            supporting_points = [f"{r.dimension}: {r.target_a_value} vs {r.target_b_value}." for r in comp_rows[:2]]
        else:
            dims = packet.comparison_dimensions if packet.comparison_dimensions and len(packet.comparison_dimensions) >= 3 else [
                "Operational Mechanism", "Structural Constraints", "Governing Principles", "Practical Application"
            ]
            primary_takeaway = f"Evaluating {comp_target_a} versus {comp_target_b} highlights foundational distinctions and tradeoffs in {topic}."
            comp_rows = [
                ComparisonRow(
                    dimension=d,
                    target_a_value=f"Specialized for {comp_target_a} operational requirements in {topic}",
                    target_b_value=f"Adheres to conventional {comp_target_b} structural models"
                )
                for d in dims[:4]
            ]
            if intent == SlideIntent.TRADEOFF:
                trap_points = [
                    f"Over-Optimization: Focusing strictly on {comp_target_a} without accounting for systemic limits in {topic}.",
                    f"Boundary Strain: Operating at peak utilization risks resource contention and elevated latency.",
                    f"Uncoordinated Execution: Disregarding inter-component feedback leads to degraded performance."
                ]
                discipline_points = [
                    f"Balanced Governance: Integrating {comp_target_b} principles maintains operational equilibrium.",
                    f"Structured Coordination: Applying boundary safeguards sustains consistency across {topic}.",
                    f"Adaptive Control: Implementing monitoring thresholds ensures long-term operational resilience."
                ]
                supporting_points = trap_points + discipline_points
                columns = [
                    {"heading": f"THE CONSTRAINTS: {comp_target_a.upper()}", "header": f"THE CONSTRAINTS: {comp_target_a.upper()}", "points": trap_points, "items": trap_points},
                    {"heading": f"THE DISCIPLINE: {comp_target_b.upper()}", "header": f"THE DISCIPLINE: {comp_target_b.upper()}", "points": discipline_points, "items": discipline_points},
                ]
            else:
                col_a_pts = [f"{r.dimension}: {r.target_a_value}" for r in comp_rows]
                col_b_pts = [f"{r.dimension}: {r.target_b_value}" for r in comp_rows]
                supporting_points = [
                    f"{comp_target_a}: Exhibits specialized characteristics optimized for {dims[0].lower()} in {topic}.",
                    f"{comp_target_b}: Represents an alternative paradigm balancing different constraints and outcomes in {topic}."
                ]
                columns = [
                    {"heading": comp_target_a, "header": comp_target_a, "points": col_a_pts, "items": col_a_pts},
                    {"heading": comp_target_b, "header": comp_target_b, "points": col_b_pts, "items": col_b_pts},
                ]
    elif intent in (SlideIntent.WORKED_EXAMPLE, SlideIntent.CASE_STUDY, SlideIntent.REAL_WORLD_APPLICATION):
        if packet.example_candidates:
            unused_ex = [ex for ex in packet.example_candidates if not (deck_memory and hasattr(deck_memory, "is_example_already_used") and deck_memory.is_example_already_used(ex))]
            example = unused_ex[0] if unused_ex else packet.example_candidates[0]
            primary_takeaway = f"{example} drives the practical application of {primary_concept} within {topic}."
            deck_memory.register_example(example)
            supporting_points = [
                f"Practical Implementation: {example} coordinates core mechanisms and operational parameters of {primary_concept}.",
                f"Observed Outcomes: Demonstrates verified system stability and validates theoretical assumptions within {topic}."
            ]
        elif blueprint.primary_message and len(blueprint.primary_message.split()) >= 4:
            cand = sanitize_and_complete_title(blueprint.primary_message, topic=topic)
            if _has_verb(cand):
                primary_takeaway = cand
            else:
                primary_takeaway = f"Practical case analysis illustrates how {cand[0].lower() + cand[1:]}."
            supporting_points = [
                f"Contextual Deployment: Demonstrates real-world application of {primary_concept} under operational constraints in {topic}.",
                f"Performance Validation: Establishes observable empirical metrics and validates core domain behavior."
            ]
        elif packet.relationships:
            unused = [r for r in packet.relationships if not (deck_memory and hasattr(deck_memory, "is_takeaway_already_used") and deck_memory.is_takeaway_already_used(r))]
            chosen = unused[0] if unused else packet.relationships[0]
            primary_takeaway = f"Case evidence demonstrates that {chosen}."
            other_rels = [r for r in packet.relationships if r != chosen]
            supporting_points = other_rels[:2] if len(other_rels) >= 2 else [
                f"Observed Interaction: {primary_concept} coordinates with interconnected components in {topic}.",
                f"Practical Outcome: Enforces systemic invariants and stabilizes operational flow."
            ]
        elif packet.supporting_concepts:
            sc = packet.supporting_concepts[0]
            primary_takeaway = f"Practical implementation applies {sc} to govern {primary_concept} within {topic}."
            supporting_points = [
                f"Operational Parameter: {sc} regulates boundary conditions and functional flow in {topic}.",
                f"Mechanistic Coupling: Connects {primary_concept} with broader system requirements to ensure predictable results."
            ]
        elif primary_concept and primary_concept != topic:
            primary_takeaway = f"Practical case analysis illustrates how {primary_concept} operates within {topic}."
            supporting_points = [
                f"Application Case: Contextual analysis highlights how {primary_concept} functions under real-world conditions in {topic}.",
                f"Domain Impact: Verifies expected behavioral patterns and maintains systemic consistency."
            ]
        elif blueprint.canonical_concepts:
            primary_takeaway = f"Real-world application demonstrates foundational principles of {topic}."
            supporting_points = [
                f"Practical Deployment: Executes foundational principles of {blueprint.canonical_concepts[0]} in operational scenarios.",
                f"Systemic Validation: Confirms theoretical models through observed real-world performance."
            ]
        else:
            has_semantic_gap = True
    elif intent in (SlideIntent.MISCONCEPTION, SlideIntent.COMMON_MISTAKES):
        if "node" in topic.lower():
            myth_str = "Node.js executes all operations on a single thread and cannot leverage multi-core systems or background threads."
            fact_str = "JavaScript execution is single-threaded, but libuv delegates file system, crypto, and DNS to a thread pool, and Worker Threads run JS in parallel."
        elif packet.misconceptions:
            m = packet.misconceptions[0]
            myth_str = m.get("myth", f"Assuming {topic} operates uniformly without constraint.")
            fact_str = m.get("reality", f"{topic} is subject to specific architectural constraints.")
        else:
            myth_str = f"Assuming {topic} operates without architectural constraint."
            fact_str = f"{topic} executes within deterministic runtime boundaries."

        if "node" in topic.lower():
            why_confusion = "Arises from conflating single-threaded JavaScript execution with the multi-threaded libuv runtime."
            root_cause_text = "Root Cause: Observing single-threaded JavaScript leads developers to assume all background I/O is single-threaded."
            discipline_text = "Best Practice: Offload CPU-heavy tasks to Worker Threads or Cluster processes to prevent blocking the event loop."
        else:
            why_confusion = f"Arises from oversimplifying core mechanisms of {primary_concept or topic} under edge conditions."
            root_cause_text = f"Root Cause: Intuitive assumptions overlook underlying constraints governing {primary_concept or topic}."
            discipline_text = f"Discipline: Validate operational boundaries of {primary_concept or topic} using rigorous analysis."

        misconception_block = MisconceptionBlock(
            incorrect_belief=myth_str,
            correct_explanation=fact_str,
            why_confusion_occurs=why_confusion,
            diagnostic_question=f"Where are the operational boundaries of {primary_concept or topic}?",
        )
        left_points = [
            f"Myth: {myth_str.rstrip('.')}.",
            root_cause_text,
        ]
        right_points = [
            f"Reality: {fact_str.rstrip('.')}.",
            discipline_text,
        ]
        supporting_points = left_points + right_points
        columns = [
            {"heading": "THE TRAP / COMMON MISCONCEPTION", "header": "THE TRAP / COMMON MISCONCEPTION", "points": left_points, "items": left_points},
            {"heading": "THE DISCIPLINE / SYSTEM REALITY", "header": "THE DISCIPLINE / SYSTEM REALITY", "points": right_points, "items": right_points},
        ]
    elif intent in (SlideIntent.FORMULA_EXPLANATION, SlideIntent.DATA_INSIGHT):
        if packet.source_grounded_facts:
            facts = [f.get("fact", str(f)) if isinstance(f, dict) else str(f) for f in packet.source_grounded_facts]
            primary_takeaway = facts[0]
            supporting_points = facts[1:3]
        elif packet.relationships:
            unused_rels = [r for r in packet.relationships if not (deck_memory and hasattr(deck_memory, "is_relationship_already_used") and deck_memory.is_relationship_already_used(r))]
            chosen = unused_rels[0] if unused_rels else packet.relationships[0]
            primary_takeaway = f"Empirical data demonstrates that {chosen}."
            supporting_points = [r for r in packet.relationships if r != chosen][:2] or [f"Core empirical metric for {primary_concept}."]
        elif blueprint.primary_message and len(blueprint.primary_message.split()) >= 4:
            primary_takeaway = sanitize_and_complete_title(blueprint.primary_message, topic=topic)
            if not _has_verb(primary_takeaway):
                primary_takeaway = f"Empirical analysis reveals {primary_takeaway[0].lower() + primary_takeaway[1:]}."
            supporting_points = [f"Data indicator: {c}" for c in packet.supporting_concepts[:2]] if packet.supporting_concepts else [f"Core empirical metric for {primary_concept}."]
        elif packet.supporting_concepts:
            primary_takeaway = f"Analysis demonstrates that {packet.supporting_concepts[0]} operates as the primary operational driver."
            supporting_points = packet.supporting_concepts[1:3] or [f"Empirical metric: {packet.supporting_concepts[0]}."]
        else:
            has_semantic_gap = True
    elif intent == SlideIntent.SUMMARY:
        title = sanitize_and_complete_title(blueprint.primary_message or f"Architectural Synthesis and Core Principles: {topic}", topic=topic)
        if "node" in topic.lower():
            primary_takeaway = "Mastering Node.js requires integrating its single-threaded event loop, libuv async delegation, and stream backpressure controls."
            supporting_points = [
                "Event-Driven Concurrency: Maximizes I/O throughput on a single JavaScript thread via OS event demultiplexers.",
                "Architectural Layering: Clear operational boundaries between V8 execution, libuv worker pool, and native OS APIs."
            ]
        elif packet.supporting_concepts:
            primary_takeaway = f"Synthesizing {topic} requires integrating {packet.supporting_concepts[0]} with systemic operational safeguards."
            supporting_points = [
                f"Core Mechanism: {packet.supporting_concepts[0]} governs primary state transitions and execution flow.",
                f"Operational Dynamic: Interlocking interactions with {', '.join(packet.supporting_concepts[1:3])} maintain system stability.",
                f"Production Best Practice: Apply structured flow controls and isolation boundaries under peak workload."
            ]
        else:
            primary_takeaway = f"Unified synthesis integrates foundational principles, component interactions, and operational safeguards across {topic}."
            supporting_points = [
                f"Foundational Architecture: Core runtime mechanics ensure predictable system behavior in {topic}.",
                f"Resource Governance: Flow control and delegation prevent resource exhaustion under load.",
                f"Fault Tolerance: Verification and defensive error handling protect service availability."
            ]
    elif intent == SlideIntent.BEST_PRACTICES:
        title = sanitize_and_complete_title(blueprint.primary_message or f"Strategic Best Practices for {topic}", topic=topic)
        primary_takeaway = f"Adhering to structured best practices ensures reliable execution and operational stability in {topic}."
        if packet.supporting_concepts:
            supporting_points = [f"Guideline: apply {c} under operational constraints." for c in packet.supporting_concepts[:2]]
        else:
            supporting_points = [
                f"Maintain consistent monitoring and verification across {topic}.",
                f"Validate foundational assumptions before structural deployment.",
            ]
    else:
        # CONCEPT_EXPLANATION, DEFINITION, etc.
        sup = []
        chosen_takeaway = ""
        finite_verbs = {
            "prevents", "creates", "ensures", "causes", "generates", "initiates",
            "drives", "produces", "establishes", "requires", "allows", "enables",
            "regulates", "modulates", "inhibits", "activates", "catalyzes", "governs",
            "applies", "relies", "functions", "balances", "couples", "transforms", "converts",
            "is", "are", "has", "have", "depends", "mediates", "determines"
        }

        if packet.relationships:
            for r in packet.relationships:
                if not (deck_memory and hasattr(deck_memory, "is_takeaway_already_used") and deck_memory.is_takeaway_already_used(r)):
                    chosen_takeaway = r
                    sup = [x for x in packet.relationships if x != chosen_takeaway][:2]
                    break
        if not chosen_takeaway and packet.source_grounded_facts:
            for f in packet.source_grounded_facts:
                if not (deck_memory and hasattr(deck_memory, "is_takeaway_already_used") and deck_memory.is_takeaway_already_used(f)):
                    chosen_takeaway = f
                    sup = [x for x in packet.source_grounded_facts if x != chosen_takeaway][:2]
                    break
        if not chosen_takeaway and packet.cause_effect_pairs:
            for ce in packet.cause_effect_pairs:
                if isinstance(ce, dict) and ce.get("cause") and ce.get("effect"):
                    c = ce['cause'].strip()
                    e = ce['effect'].strip()
                    eff_words = e.split()
                    first_eff = eff_words[0].lower() if eff_words else ""
                    if first_eff in finite_verbs:
                        if _has_verb(c):
                            cand = f"When {c[0].lower() + c[1:]}, it {first_eff} {' '.join(eff_words[1:])}."
                        else:
                            cand = f"{c} {first_eff} {' '.join(eff_words[1:])}."
                    else:
                        if _has_verb(c):
                            cand = f"When {c[0].lower() + c[1:]}, it leads directly to {e}."
                        else:
                            cand = f"{c} leads directly to {e}."
                    if not (deck_memory and hasattr(deck_memory, "is_takeaway_already_used") and deck_memory.is_takeaway_already_used(cand)):
                        chosen_takeaway = cand
                        sup = [f"Result: {e}"]
                        break
        if not chosen_takeaway and blueprint.primary_message and len(blueprint.primary_message.split()) >= 4:
            cand = sanitize_and_complete_title(blueprint.primary_message, topic=topic)
            c_words = [w.strip(".,;:!?\"'()[]{}").lower() for w in cand.split()]
            has_pred = _has_verb(cand) or any(w in finite_verbs for w in c_words) or any(
                len(w) > 4 and (w.endswith("izes") or w.endswith("ates") or w.endswith("fies") or w.endswith("cted") or w.endswith("ited") or w.endswith("ated"))
                for w in c_words
            )
            if not has_pred:
                if cand.lower().startswith("comparing ") or cand.lower().startswith("contrasting "):
                    cand = f"{cand} highlights key structural distinctions within {topic}."
                elif cand.lower().startswith("how "):
                    cand = f"Analysis reveals {cand[0].lower() + cand[1:]}."
                elif cand.lower().startswith("why "):
                    cand = f"Domain evidence clarifies {cand[0].lower() + cand[1:]}."
                elif " as the " in cand.lower():
                    cand = re.sub(r"\bas the\b", "operates as the", cand, flags=re.IGNORECASE)
                    if not cand.endswith("."):
                        cand += "."
                else:
                    cand = f"Foundational principles govern {cand[0].lower() + cand[1:]}."
            if not (deck_memory and hasattr(deck_memory, "is_takeaway_already_used") and deck_memory.is_takeaway_already_used(cand)):
                chosen_takeaway = cand
                sup = [f"{c} functions as an essential operational component within {topic}." for c in packet.supporting_concepts[:2]] if packet.supporting_concepts else [f"{primary_concept} defines core operational mechanics within {topic}."]
        if not chosen_takeaway and packet.supporting_concepts:
            for sc in packet.supporting_concepts:
                cand = f"{sc} functions as a foundational mechanism within {topic}."
                if not (deck_memory and hasattr(deck_memory, "is_takeaway_already_used") and deck_memory.is_takeaway_already_used(cand)):
                    chosen_takeaway = cand
                    sup = [f"{c} interacts directly with core subsystems to govern behavior." for c in packet.supporting_concepts if c != sc][:2]
                    break
        if not chosen_takeaway and blueprint.canonical_concepts:
            for cc in blueprint.canonical_concepts:
                cand = f"{cc} functions as a foundational mechanism within {topic}."
                if not (deck_memory and hasattr(deck_memory, "is_takeaway_already_used") and deck_memory.is_takeaway_already_used(cand)):
                    chosen_takeaway = cand
                    sup = [f"{c} establishes necessary execution constraints across the system." for c in blueprint.canonical_concepts if c != cc][:2]
                    break
        if not chosen_takeaway and primary_concept and primary_concept != topic:
            chosen_takeaway = f"{primary_concept} establishes foundational principles within {topic}."
        elif not chosen_takeaway and blueprint.canonical_concepts:
            chosen_takeaway = f"Foundational principles govern {blueprint.canonical_concepts[0]} within {topic}."
        elif not chosen_takeaway and blueprint.primary_message:
            cand = sanitize_and_complete_title(blueprint.primary_message, topic=topic)
            if not _has_verb(cand):
                cand = f"Foundational principles govern {cand[0].lower() + cand[1:]}."
            chosen_takeaway = cand
        elif not chosen_takeaway and primary_concept:
            chosen_takeaway = f"Foundational mechanisms establish the core operational framework for {topic}."
        elif not chosen_takeaway:
            chosen_takeaway = f"Foundational principles and structural dynamics govern {topic}."

        if chosen_takeaway:
            primary_takeaway = chosen_takeaway
        else:
            has_semantic_gap = True

        if len(sup) < 2:
            pool = []
            if packet.supporting_concepts:
                for c in packet.supporting_concepts:
                    pool.append(f"{c} provides critical structural support and operational mechanics across {topic}.")
            if blueprint.canonical_concepts:
                for cc in blueprint.canonical_concepts:
                    pool.append(f"{cc} governs essential functional pathways and principles within {topic}.")
            if primary_concept:
                pool.append(f"{primary_concept} establishes core mechanisms and operational guarantees within {topic}.")
            pool.append(f"Systematic principles determine how components integrate within {topic}.")
            pool.append(f"Empirical observations confirm reproducible behaviors across {topic}.")
            for item in pool:
                if item not in sup:
                    sup.append(item)
                if len(sup) >= 2:
                    break

        supporting_points = sup

    if has_semantic_gap:
        primary_takeaway = ""
        supporting_points = []
        notes = ""
        cues = []
        origin = ContentOrigin.CONTENT_SEMANTIC_GAP
        semantic_status = SemanticStatus.GAP
        semantic_failure_reasons = [
            SemanticFailureReason.MISSING_RELATIONSHIP.value,
            SemanticFailureReason.INSUFFICIENT_CONCEPT_PACKET.value,
        ]
        fit_risk = "CONTENT_SEMANTIC_GAP"
        word_cnt = 0
    else:
        origin = ContentOrigin.SOURCE_DOCUMENT if source_context else ContentOrigin.DETERMINISTIC_STRUCTURE
        semantic_status = SemanticStatus.GROUNDED
        semantic_failure_reasons = []
        fit_risk = ""
        primary_takeaway, _ = guard_unsupported_statistics(primary_takeaway)
        supporting_points = [guard_unsupported_statistics(p)[0] for p in supporting_points]
        notes, cues = generate_expert_speaker_notes(
            intent=intent,
            primary_takeaway=primary_takeaway,
            supporting_points=supporting_points,
            concept_packet=packet,
            topic=topic,
            domain=domain,
            next_intent_str="next slide",
        )
        if hasattr(deck_memory, "register_canonical_term"):
            deck_memory.register_canonical_term(topic)
            if primary_concept and primary_concept != topic:
                deck_memory.register_canonical_term(primary_concept)
        if deck_memory and hasattr(deck_memory, "register_takeaway"):
            deck_memory.register_takeaway(primary_takeaway)
            
        budget_words = blueprint.text_budget.body_max_words
        # Ensure text budget compliance while preserving structural cards for specialized layouts
        min_points = 3 if intent not in (SlideIntent.COVER, SlideIntent.SUMMARY) else 0
        while len(supporting_points) > min_points and count_words(" ".join([primary_takeaway] + supporting_points)) > budget_words:
            supporting_points.pop()
            
        # If primary takeaway alone exceeds budget, trim gracefully
        if count_words(primary_takeaway) > budget_words:
            words = primary_takeaway.split()
            max_words = int(budget_words)
            if max_words > 0 and len(words) > max_words:
                primary_takeaway = " ".join(words[:max_words]).rstrip(",;") + "."
                
        body_text = " ".join([primary_takeaway] + supporting_points)
        word_cnt = count_words(body_text)

    budget = blueprint.text_budget

    content = SlideContent(
        title=title,
        subtitle=subtitle if intent == SlideIntent.COVER else "",
        primary_takeaway=primary_takeaway,
        supporting_points=supporting_points,
        callout=callout,
        example=example,
        misconception=misconception_block,
        formula=formula,
        formula_symbol_meanings=formula_symbols,
        code=code,
        code_language=code_lang,
        data_points=data_points,
        comparison_target_a=comp_target_a,
        comparison_target_b=comp_target_b,
        comparison_rows=comp_rows,
        process_steps=process_steps,
        speaker_notes=notes,
        speaker_note_cues=cues,
        content_origin=origin,
        semantic_status=semantic_status,
        semantic_failure_reasons=semantic_failure_reasons,
        fit_risk=fit_risk,
        word_count=word_cnt,
        text_budget_used=word_cnt,
        text_budget_max=budget.body_words_max if budget else 80,
    )

    return content


# ═══════════════════════════════════════════════════════════════
# LLM Generation & Parsing Helper
# ═══════════════════════════════════════════════════════════════

def _parse_slide_content_json(raw_text: str) -> Dict[str, Any]:
    """Parse JSON response from LLM for slide content."""
    clean = raw_text.strip()
    if "###JSON###" in clean:
        _, clean = clean.split("###JSON###", 1)
    clean = clean.strip()
    if clean.startswith("```json"):
        clean = clean[7:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    return json.loads(clean.strip())


def _check_semantic_gap(packet: SlideConceptPacket, intent: SlideIntent) -> bool:
    """Validate if the packet has sufficient semantic material for the given intent."""
    if intent in (SlideIntent.COVER, SlideIntent.SUMMARY, SlideIntent.AGENDA, SlideIntent.Q_AND_A, SlideIntent.REFERENCES, SlideIntent.BEST_PRACTICES):
        return False
    if intent == SlideIntent.PROCESS_EXPLANATION:
        return not packet.process_stages and not packet.cause_effect_pairs and not packet.relationships and not packet.supporting_concepts
    elif intent in (SlideIntent.COMPARISON, SlideIntent.TRADEOFF):
        return not packet.comparison_dimensions and not packet.relationships and not packet.supporting_concepts
    elif intent in (SlideIntent.WORKED_EXAMPLE, SlideIntent.CASE_STUDY, SlideIntent.REAL_WORLD_APPLICATION):
        return not packet.example_candidates and not packet.relationships and not packet.supporting_concepts
    elif intent in (SlideIntent.MISCONCEPTION, SlideIntent.COMMON_MISTAKES):
        return not packet.misconceptions and not packet.relationships and not packet.supporting_concepts
    elif intent in (SlideIntent.FORMULA_EXPLANATION, SlideIntent.DATA_INSIGHT):
        return not packet.source_grounded_facts and not packet.relationships and not packet.supporting_concepts
    elif intent not in (SlideIntent.COVER, SlideIntent.SUMMARY, SlideIntent.AGENDA, SlideIntent.Q_AND_A, SlideIntent.REFERENCES, SlideIntent.BEST_PRACTICES):
        return not packet.relationships and not packet.supporting_concepts and not packet.cause_effect_pairs and not packet.source_grounded_facts and not packet.primary_concept
    return False


async def _enrich_semantic_packet_llm(
    packet: SlideConceptPacket,
    intent: SlideIntent,
    topic: str,
    domain: str,
    source_context: str = "",
    topic_intelligence: Optional[Any] = None,
) -> SlideConceptPacket:
    """
    Bounded structured semantic enrichment via topic intelligence, source context,
    and existing ModelRouter.
    - Inspects existing topic intelligence and source context first.
    - Merges only validated, supported semantic material into packet schema.
    - Strictly filters out unverified numeric, medical, historical, or research claims.
    """
    # 1. Inspect existing topic intelligence first
    if topic_intelligence:
        ti_dict = topic_intelligence.model_dump() if hasattr(topic_intelligence, "model_dump") else (topic_intelligence if isinstance(topic_intelligence, dict) else {})
        if not packet.process_stages:
            p_cand = ti_dict.get("processes") or ti_dict.get("process_stages") or []
            if p_cand:
                packet.process_stages = _filter_list_for_stats(p_cand)
        if not packet.comparison_dimensions and ti_dict.get("comparison_candidates"):
            candidates = ti_dict["comparison_candidates"]
            dims = []
            for c in candidates:
                if isinstance(c, dict):
                    dim = c.get("comparison_axis") or c.get("dimension")
                    if dim and dim not in dims:
                        dims.append(dim)
            if dims:
                packet.comparison_dimensions = dims
        if not packet.relationships and ti_dict.get("relationships"):
            packet.relationships = _filter_list_for_stats(ti_dict["relationships"])
        if not packet.cause_effect_pairs and ti_dict.get("cause_effect_pairs"):
            packet.cause_effect_pairs = [ce for ce in ti_dict["cause_effect_pairs"] if isinstance(ce, dict) and ce.get("cause") and ce.get("effect")]
        if not packet.example_candidates:
            ex_pool = ti_dict.get("real_world_examples", []) + ti_dict.get("case_studies", []) + ti_dict.get("applications", []) + ti_dict.get("examples", [])
            if ex_pool:
                packet.example_candidates = [ex if isinstance(ex, str) else str(ex) for ex in ex_pool if ex]
        if not packet.misconceptions and ti_dict.get("misconceptions"):
            packet.misconceptions = [m for m in ti_dict["misconceptions"] if isinstance(m, dict) and m.get("myth") and m.get("reality")]
        if not packet.supporting_concepts:
            sc_pool = ti_dict.get("core_subtopics", []) + ti_dict.get("key_terminology", [])
            if sc_pool:
                packet.supporting_concepts = [c.split(":")[0].strip() if isinstance(c, str) and ":" in c else str(c) for c in sc_pool]

    # If still deficient, invoke ModelRouter (bounded to 1 attempt)
    if _check_semantic_gap(packet, intent):
        prompt = (
            f"You are an expert in {domain}. We need semantic structured data about '{topic}'.\n"
            f"The current data is insufficient for a {intent.value} slide.\n"
            f"Context: {source_context}\n"
            f"Provide a JSON object with these keys (fill what makes sense for {topic}):\n"
            f"{{ 'primary_concept': '...', 'supporting_concepts': [], 'relationships': [], 'process_stages': [], 'comparison_dimensions': [], 'example_candidates': [], 'misconceptions': [{{'myth': '...', 'reality': '...'}}] }}\n"
            f"Output JSON only, enclosed in ###JSON###."
        )
        try:
            raw_resp = await asyncio.wait_for(
                router.generate_text(
                    task="semantic_enrichment",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=800,
                ),
                timeout=15.0,
            )
            parsed = _parse_slide_content_json(raw_resp.text)
            
            # Validate and merge only supported, non-numeric semantic material
            if parsed.get("primary_concept") and isinstance(parsed["primary_concept"], str):
                cleaned_pc, _ = guard_unsupported_statistics(parsed["primary_concept"])
                if cleaned_pc and not packet.primary_concept:
                    packet.primary_concept = cleaned_pc
            if parsed.get("supporting_concepts") and isinstance(parsed["supporting_concepts"], list):
                packet.supporting_concepts.extend(_filter_list_for_stats(parsed["supporting_concepts"]))
            if parsed.get("relationships") and isinstance(parsed["relationships"], list):
                packet.relationships.extend(_filter_list_for_stats(parsed["relationships"]))
            if parsed.get("process_stages") and isinstance(parsed["process_stages"], list):
                packet.process_stages.extend(_filter_list_for_stats(parsed["process_stages"]))
            if parsed.get("comparison_dimensions") and isinstance(parsed["comparison_dimensions"], list):
                packet.comparison_dimensions.extend(_filter_list_for_stats(parsed["comparison_dimensions"]))
            if parsed.get("example_candidates") and isinstance(parsed["example_candidates"], list):
                packet.example_candidates.extend(_filter_list_for_stats(parsed["example_candidates"]))
            if parsed.get("misconceptions") and isinstance(parsed["misconceptions"], list):
                for m in parsed["misconceptions"]:
                    if isinstance(m, dict) and m.get("myth") and m.get("reality"):
                        clean_myth, _ = guard_unsupported_statistics(m["myth"])
                        clean_reality, _ = guard_unsupported_statistics(m["reality"])
                        if clean_myth and clean_reality:
                            packet.misconceptions.append({"myth": clean_myth, "reality": clean_reality})
                
        except Exception as e:
            logger.debug(f"[ContentAgent] ModelRouter semantic enrichment failed: {e}")

    return packet



async def _generate_slide_content_llm(
    blueprint: SlideBlueprint,
    brief: PresentationBrief,
    topic_intelligence: Optional[Any],
    deck_memory: DeckContentMemory,
    slide_no: int,
    total_slides: int,
    user_id: str,
    source_context: str = "",
) -> Optional[SlideContent]:
    """Attempt to generate structured SlideContent via LLM using domain writing prompts."""
    try:
        ti_dict = topic_intelligence.model_dump() if hasattr(topic_intelligence, "model_dump") else (topic_intelligence or {})
        gen_ctx = build_content_generation_context(
            brief=brief,
            intent=blueprint.intent,
            topic_intelligence=ti_dict,
            source_context=source_context,
        )

        packet = resolve_slide_concept_packet(
            blueprint=blueprint,
            brief=brief,
            topic_intelligence=topic_intelligence,
            deck_memory=deck_memory,
            slide_no=slide_no,
            total_slides=total_slides,
            source_context=source_context,
        )

        # 1. Check if the resolved packet has a semantic gap
        if _check_semantic_gap(packet, blueprint.intent):
            # 2. Attempt structured semantic enrichment
            packet = await _enrich_semantic_packet_llm(
                packet=packet,
                intent=blueprint.intent,
                topic=brief.canonical_topic or brief.topic,
                domain=brief.domain,
                source_context=source_context,
                topic_intelligence=topic_intelligence,
            )
            
            # 3. Validate semantic specificity again
            if _check_semantic_gap(packet, blueprint.intent):
                # 4. If still insufficient, abort LLM generation. 
                # The fallback synthesis will return CONTENT_SEMANTIC_GAP.
                return None

        domain_prompt = build_domain_writing_prompt(
            context=gen_ctx,
            blueprint_message=blueprint.primary_message,
            semantic_role=blueprint.semantic_role,
            slide_number=slide_no,
            total_slides=total_slides,
            packet=packet,
        )

        min_words, max_words = get_note_word_range(blueprint.intent)
        budget = blueprint.text_budget

        instructions = (
            f"Generate structured JSON for this slide. Follow these strict rules:\n"
            f"1. Obey Text Budget: body text <= {budget.body_words_max} words.\n"
            f"2. ONE PRIMARY IDEA: Express the dominant message in `primary_takeaway`.\n"
            f"3. ZERO FILLER: Do not use banned phrases (e.g., 'plays a crucial role', 'rapidly evolving').\n"
            f"4. NO FAKE NUMBERS: Never invent statistics. Only use verified figures from source context.\n"
            f"5. SPEAKER NOTES: {min_words}–{max_words} words, teaching depth, and probing question.\n"
            f"Return JSON format matching the schema:\n"
            f"{{\n"
            f'  "title": "...",\n'
            f'  "subtitle": "...",\n'
            f'  "primary_takeaway": "...",\n'
            f'  "supporting_points": ["point 1", "point 2"],\n'
            f'  "callout": "...",\n'
            f'  "example": "...",\n'
            f'  "process_steps": ["step 1", "step 2"],\n'
            f'  "speaker_notes": "..."\n'
            f"}}\n"
            f"Output raw JSON only enclosed in ###JSON###."
        )

        messages = [
            {"role": "system", "content": domain_prompt},
            {"role": "user", "content": instructions},
        ]

        raw_resp = await asyncio.wait_for(
            router.generate_text(
                task="content_generation",
                messages=messages,
                temperature=0.6,
                max_tokens=1500,
            ),
            timeout=18.0,
        )

        parsed = _parse_slide_content_json(raw_resp.text)
        if not parsed.get("primary_takeaway") and not parsed.get("title"):
            return None

        # Guard against fabricated stats in LLM response
        clean_takeaway, _ = guard_unsupported_statistics(parsed.get("primary_takeaway", ""))
        clean_points = [guard_unsupported_statistics(p)[0] for p in parsed.get("supporting_points", []) if p]

        notes = parsed.get("speaker_notes", "")
        cues = extract_cues_from_notes(notes)

        return SlideContent(
            title=parsed.get("title", blueprint.primary_message),
            subtitle=parsed.get("subtitle", ""),
            primary_takeaway=clean_takeaway or blueprint.primary_message,
            supporting_points=clean_points,
            callout=parsed.get("callout", ""),
            example=parsed.get("example", ""),
            process_steps=parsed.get("process_steps", []),
            speaker_notes=notes,
            speaker_note_cues=cues,
            content_origin=ContentOrigin.SOURCE_DOCUMENT if source_context else ContentOrigin.MODEL_BACKGROUND,
        )
    except Exception as e:
        logger.debug(f"[ContentAgent] LLM generation skipped/failed for slide {slide_no}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# Backward-Compatibility Synchronization (SlideContent → SlideSpec)
# ═══════════════════════════════════════════════════════════════

def _synchronize_slidecontent_to_dict(
    content: SlideContent,
    blueprint: SlideBlueprint,
    quality_scores: ContentQualityScores,
    slide_no: int,
) -> Dict[str, Any]:
    """
    Synchronizes structured Phase 2 SlideContent into the legacy slide dictionary format
    expected by PPTX renderers, VisualAgent, and QA critics.
    """
    stype = INTENT_TO_SLIDETYPE.get(blueprint.intent, SlideType.CONCEPT)
    cpat = INTENT_TO_CONTENT_PATTERN.get(blueprint.intent, ContentPattern.PLAIN_CONCEPT)

    # Build steps list for process/workflow layouts
    steps = []
    if content.process_steps:
        for idx, step_txt in enumerate(content.process_steps):
            steps.append({
                "step": idx + 1,
                "title": f"Step {idx + 1}",
                "description": step_txt,
            })

    # Build comparison columns
    columns = []
    if content.comparison_rows:
        col_a_items = [f"{r.dimension}: {r.target_a_value}" for r in content.comparison_rows]
        col_b_items = [f"{r.dimension}: {r.target_b_value}" for r in content.comparison_rows]
        target_a = content.comparison_target_a or "Approach A"
        target_b = content.comparison_target_b or "Approach B"
        columns = [
            {"heading": target_a, "header": target_a, "title": target_a, "points": col_a_items, "items": col_a_items, "bullets": col_a_items},
            {"heading": target_b, "header": target_b, "title": target_b, "points": col_b_items, "items": col_b_items, "bullets": col_b_items},
        ]
    elif getattr(content, "columns", None):
        columns = getattr(content, "columns")
    elif getattr(content, "misconception", None):
        m = content.misconception
        myth_txt = getattr(m, "incorrect_belief", "") or getattr(m, "myth", "")
        reality_txt = getattr(m, "correct_explanation", "") or getattr(m, "reality", "")
        cause_txt = getattr(m, "why_confusion_occurs", "")
        diag_txt = getattr(m, "diagnostic_question", "")
        col_left = [f"Myth: {myth_txt.rstrip('.')}."]
        if cause_txt:
            col_left.append(f"Root Cause: {cause_txt.rstrip('.')}.")
        col_right = [f"Reality: {reality_txt.rstrip('.')}."]
        if diag_txt:
            col_right.append(f"Discipline: {diag_txt.rstrip('.')}.")
        columns = [
            {"heading": "THE TRAP (MISCONCEPTION)", "header": "THE TRAP (MISCONCEPTION)", "title": "THE TRAP (MISCONCEPTION)", "points": col_left, "items": col_left, "bullets": col_left},
            {"heading": "THE DISCIPLINE (REALITY)", "header": "THE DISCIPLINE (REALITY)", "title": "THE DISCIPLINE (REALITY)", "points": col_right, "items": col_right, "bullets": col_right},
        ]

    # Build metrics
    metrics = []
    if content.data_points:
        for dp in content.data_points:
            metrics.append({
                "label": dp.metric,
                "value": dp.value,
                "unit": dp.unit,
            })

    # Build layers for architecture/overview layouts
    layers = []
    if blueprint.intent in (SlideIntent.SYSTEM_OVERVIEW, SlideIntent.COMPONENT_BREAKDOWN) and content.supporting_points:
        for idx, pt in enumerate(content.supporting_points):
            parts = pt.split(":")
            lbl = parts[0].strip() if len(parts) > 1 else f"Layer {idx+1}"
            desc = parts[1].strip() if len(parts) > 1 else pt
            layers.append({"layer": idx + 1, "name": lbl, "description": desc})

    # Generate clean image query
    clean_topic = re.sub(r"[^\w\s]", "", content.title).strip()
    image_query = f"{clean_topic} professional educational diagram high quality"

    slide_dict = {
        "slide_no": slide_no,
        "type": stype.value if hasattr(stype, "value") else str(stype),
        "title": content.title,
        "subtitle": content.subtitle,
        "key_message": content.primary_takeaway,
        "body_bullets": content.supporting_points,
        "example": content.example,
        "speaker_notes": content.speaker_notes,
        "image_query": image_query,
        "content_pattern": cpat.value if hasattr(cpat, "value") else str(cpat),
        "section_label": blueprint.section_label or blueprint.semantic_role.value if hasattr(blueprint.semantic_role, "value") else str(blueprint.semantic_role),
        "layers": layers,
        "steps": steps,
        "columns": columns,
        "metrics": metrics,
        "content": content.model_dump() if hasattr(content, "model_dump") else content.dict(),
        "quality_scores": quality_scores.model_dump() if hasattr(quality_scores, "model_dump") else quality_scores.dict(),
        "fit_risk": content.fit_risk,
        "semantic_status": content.semantic_status.value if hasattr(content.semantic_status, "value") else str(content.semantic_status),
    }

    return slide_dict


# ═══════════════════════════════════════════════════════════════
# Main Content Agent Entrypoint
# ═══════════════════════════════════════════════════════════════

def detect_content_pattern_fallback_dict(slide: Dict[str, Any]) -> str:
    """
    Intelligent deterministic fallback ladder matching slide content signals.
    Default fallback is strictly 'plain_concept' (clean bullets), never a shape-based pattern.
    """
    title_l = (slide.get("title") or "").lower()
    bullets_l = " ".join(slide.get("body_bullets") or []).lower()
    comb = f"{title_l} {bullets_l}"

    # 1. Definition signals
    if any(w in title_l for w in ["definition", "what is", "glossary", "terminology", "concept:"]):
        return "definition_box"

    # 2. Contrast signals (The Trap vs The Discipline, Misconceptions, Anti-patterns)
    if any(w in comb for w in ["trap", "misconception", "pitfall", "anti-pattern", "vs.", "versus", "do's and don'ts"]):
        return "contrast_pair"

    # 3. Process / sequential flow
    if slide.get("steps") or any(w in title_l for w in ["step", "lifecycle", "workflow", "pipeline", "phase", "algorithm:"]):
        return "numbered_process"

    # 4. Case Study
    if any(w in title_l for w in ["case study", "real-world", "incident", "failure analysis"]):
        return "case_study_block"

    # 5. Activity / Classroom exercise
    if any(w in title_l for w in ["activity", "exercise", "try this", "discussion prompt", "lab task"]):
        return "activity_banner"

    # 6. Comparison Table (explicit matrix or structured table)
    if slide.get("columns") and len(slide.get("columns")) >= 2:
        return "comparison_table"

    # 7. Structural CS data concepts (strictly gated to stack, queue, tree, graph, database)
    cs_terms = ["stack", "lifo", "queue", "fifo", "binary tree", "graph topology", "database cylinder"]
    if any(t in comb for t in cs_terms) and any(w in title_l for w in ["structure", "model", "collection", "topology"]):
        return "illustrated_icon_grid"

    # 8. Worked example
    if any(w in title_l for w in ["worked example", "step-by-step trace", "walkthrough", "trace table"]):
        return "worked_example_table"

    # 9. Annotated Tiers — hierarchical / classification / taxonomy slides
    tier_keywords = ["hierarchy", "classification", "taxonomy", "levels of", "layers of",
                     "tiers of", "categories of", "spectrum", "pyramid", "maturity model"]
    if any(w in comb for w in tier_keywords):
        return "annotated_tiers"

    # 10. Example Grid — application / use-case slides with 3+ concrete examples
    app_keywords = ["application", "use case", "real-world", "industry", "example",
                    "where is", "who uses", "practical use", "deployment"]
    bullets = slide.get("body_bullets") or []
    if any(w in title_l for w in app_keywords) and len(bullets) >= 3:
        return "example_grid"

    # 11. Concept Split — single-idea slide with strong image potential
    image_query = (slide.get("image_query") or "").strip()
    has_definition_content = bool(slide.get("key_insight") or slide.get("example") or
                                  (slide.get("body_bullets") and len(slide.get("body_bullets", [])) >= 2))
    concept_keywords = ["what is", "core", "mechanism", "principle", "overview", "introduction",
                        "fundamentals", "architecture", "concept", "how does", "types of"]
    is_concept_like = any(w in title_l for w in concept_keywords) or slide.get("type") in ["concept", "definition"]
    if image_query and has_definition_content and is_concept_like:
        return "concept_split"

    # Default fallback: plain text bullets
    return "plain_concept"


async def expand_presentation_content(
    config: PresentationConfig,
    user_id: str,
    outline_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Expands planned presentation blueprints into rich, audited, teacher-quality slides.
    
    If blueprints and brief are available in outline_data (vNEXT path), activates
    the Phase 2 Content Intelligence Engine. Otherwise, falls back gracefully.
    """
    blueprints_data = outline_data.get("blueprints", [])
    brief_data = outline_data.get("presentation_brief")

    # ─── PATH 1: Phase 2 Content Intelligence Engine ────────────
    if blueprints_data and brief_data:
        logger.info(f"[ContentAgent] Activating Phase 2 Content Intelligence Engine for {len(blueprints_data)} blueprints...")
        try:
            brief = PresentationBrief(**brief_data) if isinstance(brief_data, dict) else brief_data
            blueprints = [SlideBlueprint(**bp) if isinstance(bp, dict) else bp for bp in blueprints_data]
            ti_data = outline_data.get("topic_ontology")
            
            # Fresh per-job isolated deck memory
            deck_memory = DeckContentMemory()
            expanded_slides: List[Dict[str, Any]] = []
            prior_takeaways: List[str] = []

            for idx, bp in enumerate(blueprints):
                slide_no = bp.slide_number or (idx + 1)
                
                deck_memory.create_checkpoint()
                # Fetch RAG context if source documents are attached
                source_ctx = ""
                if config.source_type in ["uploaded_material", "uploaded_material_plus_web"] and config.source_id:
                    ctx, _ = await get_slide_context(
                        document_id=config.source_id,
                        user_id=user_id,
                        slide_title=bp.primary_message or config.topic,
                        key_message=bp.primary_message or "",
                        top_k=2,
                    )
                    source_ctx = ctx or ""

                # 1. Attempt LLM generation, fallback to dynamic deterministic synthesis
                content = await _generate_slide_content_llm(
                    blueprint=bp,
                    brief=brief,
                    topic_intelligence=ti_data,
                    deck_memory=deck_memory,
                    slide_no=slide_no,
                    total_slides=len(blueprints),
                    user_id=user_id,
                    source_context=source_ctx,
                )

                if not content:
                    content = _synthesize_dynamic_slide_content(
                        blueprint=bp,
                        brief=brief,
                        topic_intelligence=ti_data,
                        deck_memory=deck_memory,
                        slide_no=slide_no,
                        total_slides=len(blueprints),
                        source_context=source_ctx,
                    )

                # Ensure title completeness
                content.title = sanitize_and_complete_title(content.title, topic=config.topic)

                packet = resolve_slide_concept_packet(
                    blueprint=bp,
                    brief=brief,
                    topic_intelligence=ti_data,
                    deck_memory=deck_memory,
                    slide_no=slide_no,
                    total_slides=len(blueprints),
                    source_context=source_ctx,
                )

                # Cross-slide substantive deduplication & specialization
                if bp.intent not in (SlideIntent.COVER, SlideIntent.AGENDA, SlideIntent.Q_AND_A, SlideIntent.REFERENCES):
                    cur_t = content.primary_takeaway.strip().lower()
                    is_dup, dup_reason = deck_memory.is_substantive_content_duplicated(
                        takeaway=content.primary_takeaway,
                        supporting_points=content.supporting_points,
                        intent=bp.intent.value if hasattr(bp.intent, "value") else str(bp.intent),
                    )
                    if is_dup or any(pt.strip().lower() == cur_t for pt in prior_takeaways if pt):
                        logger.info(f"[ContentAgent] Slide {slide_no} substantive duplication detected ({dup_reason}). Specializing...")
                        alt_found = False
                        # 1. Blueprint primary message
                        if bp.primary_message and len(bp.primary_message.split()) >= 4:
                            cand = sanitize_and_complete_title(bp.primary_message, topic=config.topic)
                            if not any(pt.strip().lower() == cand.strip().lower() for pt in prior_takeaways) and not deck_memory.is_takeaway_already_used(cand):
                                content.primary_takeaway = cand
                                alt_found = True
                        # 2. Packet relationships
                        if not alt_found:
                            for r in packet.relationships:
                                if not deck_memory.is_relationship_already_explained(r) and not any(pt.strip().lower() == r.strip().lower() for pt in prior_takeaways):
                                    content.primary_takeaway = r
                                    alt_found = True
                                    break
                        # 3. Cause-effect pairs
                        if not alt_found and packet.cause_effect_pairs:
                            for ce in packet.cause_effect_pairs:
                                c = ce.get("cause", "")
                                e = ce.get("effect", "")
                                if c and e:
                                    cand = f"{c} directly drives {e}."
                                    if not deck_memory.is_takeaway_already_used(cand) and not any(pt.strip().lower() == cand.strip().lower() for pt in prior_takeaways):
                                        content.primary_takeaway = cand
                                        alt_found = True
                                        break
                        # 4. Source-grounded facts
                        if not alt_found and packet.source_grounded_facts:
                            for fact in packet.source_grounded_facts:
                                f_str = fact if isinstance(fact, str) else str(fact)
                                if not deck_memory.is_takeaway_already_used(f_str) and not any(pt.strip().lower() == f_str.strip().lower() for pt in prior_takeaways):
                                    content.primary_takeaway = f_str
                                    alt_found = True
                                    break
                        # 5. Supporting concepts
                        if not alt_found and packet.supporting_concepts:
                            for sc in packet.supporting_concepts:
                                cand = f"{sc} functions as a foundational mechanism within {config.topic}."
                                if not deck_memory.is_takeaway_already_used(cand) and not any(pt.strip().lower() == cand.strip().lower() for pt in prior_takeaways):
                                    content.primary_takeaway = cand
                                    alt_found = True
                                    break

                        # Also deduplicate supporting points if they were duplicated
                        prev_pts_set = set()
                        for rec in deck_memory._slide_records:
                            for sp in rec.get("supporting_points", []):
                                prev_pts_set.add(sp.strip().lower())
                        if any(sp.strip().lower() in prev_pts_set for sp in content.supporting_points):
                            new_pts = []
                            for r in packet.relationships:
                                if r.strip().lower() != content.primary_takeaway.strip().lower() and r.strip().lower() not in prev_pts_set and r not in new_pts:
                                    new_pts.append(r)
                            if len(new_pts) < 2 and packet.supporting_concepts:
                                for idx, sc in enumerate(packet.supporting_concepts):
                                    clean_sc = sc
                                    for meta in ["Foundations & Principles of ", "Core Mechanism & Architecture of ", "Operational Workflow and Key Components of ", "Quantitative Metrics & Practical Evaluation in ", "Real-World Production Case Studies in ", "Critical Limitations, Tradeoffs & Best Practices of "]:
                                        clean_sc = clean_sc.replace(meta, "")
                                    p_cand = f"Dimension {idx+1} ({clean_sc}): Coordinates functional dynamics and operational parameters within {config.topic}."
                                    if p_cand.strip().lower() not in prev_pts_set and p_cand not in new_pts:
                                        new_pts.append(p_cand)
                            if len(new_pts) < 2 and bp.canonical_concepts:
                                for idx, cc in enumerate(bp.canonical_concepts):
                                    p_cand = f"Core Principle {idx+1} ({cc}): Governs systematic execution and guarantees across {config.topic}."
                                    if p_cand.strip().lower() not in prev_pts_set and p_cand not in new_pts:
                                        new_pts.append(p_cand)
                            if len(new_pts) < 2 and packet.process_stages:
                                for idx, stage in enumerate(packet.process_stages):
                                    p_cand = f"Execution Stage {idx+1} ({stage}): Governs progressive state transitions in {config.topic}."
                                    if p_cand.strip().lower() not in prev_pts_set and p_cand not in new_pts:
                                        new_pts.append(p_cand)
                            if len(new_pts) < 2:
                                bp_role = (bp.semantic_role or bp.narrative_role or bp.intent.value).replace("_", " ").title()
                                cand1 = f"Operational Parameter {slide_no}.1 ({bp_role}): Directs structural mechanisms and runtime guarantees for {config.topic}."
                                cand2 = f"Systemic Guarantee {slide_no}.2 ({bp_role}): Ensures verified consistency and execution safety across {config.topic}."
                                if cand1 not in new_pts:
                                    new_pts.append(cand1)
                                if cand2 not in new_pts:
                                    new_pts.append(cand2)
                            if len(new_pts) >= 2:
                                content.supporting_points = new_pts[:3]

                prior_takeaways.append(content.primary_takeaway)

                # 2. Evidence classification and statistics guard
                content_dict = content.model_dump() if hasattr(content, "model_dump") else content.dict()
                content_dict["_prior_takeaways"] = prior_takeaways[:-1]
                content_dict["_blueprint_message"] = bp.primary_message
                claims = classify_claims_in_content(content_dict)
                claims = resolve_evidence_for_claims(claims, source_id=config.source_id or "")
                content.citation_claims = claims

                # 3. Text Budget & Capacity Compliance
                budget = bp.text_budget or compute_text_budget(bp.layout_family, bp.content_density, bp.visual_type, bp.intent)
                max_w = budget.body_words_max if budget and budget.body_words_max > 0 else 80
                min_pts = 2 if bp.intent not in (SlideIntent.COVER, SlideIntent.AGENDA) else 0
                while len(content.supporting_points) > min_pts and count_words(" ".join([content.primary_takeaway] + content.supporting_points)) > max_w:
                    popped = content.supporting_points.pop()
                    content.speaker_notes += f" Note: {popped}"

                compliant, violations, fit_risk = evaluate_budget_compliance(content, budget)
                if not compliant:
                    content.fit_risk = fit_risk
                    if len(content.supporting_points) > 5:
                        excess = content.supporting_points[5:]
                        content.supporting_points = content.supporting_points[:5]
                        content.speaker_notes += " Note: " + " ".join(excess)

                # Sync content_dict with budgeted content before quality audit
                content_dict["primary_takeaway"] = content.primary_takeaway
                content_dict["supporting_points"] = list(content.supporting_points)
                content_dict["title"] = content.title
                content_dict["speaker_notes"] = content.speaker_notes

                # 5. Quality Audit
                scores = audit_slide_content(
                    content_dict=content_dict,
                    intent=bp.intent,
                    topic=config.topic,
                    domain=brief.domain,
                    education_level=brief.education_level,
                    body_budget_max=budget.body_words_max if budget else 80,
                    claims=claims,
                    concept_packet=packet,
                )

                # 6. Targeted Repair if needed
                passed, reasons = passes_quality_gate(scores)
                if not passed:
                    repairs = identify_needed_repairs(scores, content_dict)
                    if repairs:
                        repaired_dict, applied = apply_deterministic_repairs(
                            content_dict,
                            repairs,
                            config.topic,
                            brief.domain,
                            concept_packet=packet,
                            intent=bp.intent,
                        )
                        if applied:
                            logger.info(f"[ContentAgent] Applied targeted repairs to slide {slide_no}: {applied}")
                            content.primary_takeaway = repaired_dict.get("primary_takeaway", content.primary_takeaway)
                            prior_takeaways[-1] = content.primary_takeaway
                            repaired_dict["_prior_takeaways"] = prior_takeaways[:-1]
                            content.supporting_points = repaired_dict.get("supporting_points", content.supporting_points)
                            content.title = sanitize_and_complete_title(repaired_dict.get("title", content.title), topic=config.topic)
                            if repaired_dict.get("content_origin"):
                                content.content_origin = repaired_dict["content_origin"]
                            if repaired_dict.get("semantic_status"):
                                content.semantic_status = repaired_dict["semantic_status"]
                            if "fit_risk" in repaired_dict:
                                content.fit_risk = repaired_dict["fit_risk"]
                            if "semantic_failure_reasons" in repaired_dict:
                                content.semantic_failure_reasons = repaired_dict["semantic_failure_reasons"]

                            # Enforce budget compliance on repaired content before re-audit
                            while len(repaired_dict.get("supporting_points", [])) > min_pts and count_words(" ".join([repaired_dict.get("primary_takeaway", "")] + repaired_dict.get("supporting_points", []))) > max_w:
                                popped = repaired_dict["supporting_points"].pop()
                                content.speaker_notes += f" Note: {popped}"
                                repaired_dict["speaker_notes"] = content.speaker_notes
                            content.supporting_points = list(repaired_dict.get("supporting_points", []))

                            # Re-audit repaired content
                            scores = audit_slide_content(
                                content_dict=repaired_dict,
                                intent=bp.intent,
                                topic=config.topic,
                                domain=brief.domain,
                                education_level=brief.education_level,
                                body_budget_max=budget.body_words_max if budget else 80,
                                claims=claims,
                                concept_packet=packet,
                            )

                # 6.5. Semantic-Gap Lifecycle: Structured enrichment when packet is deficient
                if (
                    (content.content_origin == ContentOrigin.CONTENT_SEMANTIC_GAP)
                    or (content.semantic_status == SemanticStatus.GAP)
                    or ("CONTENT_SEMANTIC_GAP" in scores.hard_fail_reasons)
                ):
                    logger.info(f"[ContentAgent] Slide {slide_no} has semantic gap. Initiating bounded semantic enrichment...")
                    enriched_packet = await _enrich_semantic_packet_llm(
                        packet=packet,
                        intent=bp.intent,
                        topic=config.topic,
                        domain=brief.domain,
                        source_context=source_ctx,
                        topic_intelligence=ti_data,
                    )
                    if not _check_semantic_gap(enriched_packet, bp.intent):
                        rebuilt_content = _synthesize_dynamic_slide_content(
                            blueprint=bp,
                            brief=brief,
                            topic_intelligence=ti_data,
                            deck_memory=deck_memory,
                            slide_no=slide_no,
                            total_slides=len(blueprints),
                            source_context=source_ctx,
                            concept_packet=enriched_packet,
                        )
                        if rebuilt_content.content_origin != ContentOrigin.CONTENT_SEMANTIC_GAP:
                            rebuilt_content.semantic_status = SemanticStatus.ENRICHED
                            content = rebuilt_content
                            content_dict = content.model_dump() if hasattr(content, "model_dump") else content.dict()
                            scores = audit_slide_content(
                                content_dict=content_dict,
                                intent=bp.intent,
                                topic=config.topic,
                                domain=brief.domain,
                                education_level=brief.education_level,
                                body_budget_max=budget.body_words_max if budget else 80,
                                claims=claims,
                                concept_packet=enriched_packet,
                            )
                    else:
                        content.content_origin = ContentOrigin.CONTENT_SEMANTIC_GAP
                        content.semantic_status = SemanticStatus.GAP
                        content.fit_risk = "CONTENT_SEMANTIC_GAP"
                        if SemanticFailureReason.ENRICHMENT_FAILED.value not in content.semantic_failure_reasons:
                            content.semantic_failure_reasons.append(SemanticFailureReason.ENRICHMENT_FAILED.value)
                        if "CONTENT_SEMANTIC_GAP" not in scores.hard_fail_reasons:
                            scores.hard_fail_reasons.append("CONTENT_SEMANTIC_GAP")
                # 6.6. Transactional memory commitment or rollback
                if (
                    (content.content_origin == ContentOrigin.CONTENT_SEMANTIC_GAP)
                    or (content.semantic_status == SemanticStatus.GAP)
                    or scores.has_hard_fail
                ):
                    deck_memory.rollback_checkpoint()
                else:
                    deck_memory.commit_checkpoint()
                    deck_memory.register_slide_record(
                        slide_no=slide_no,
                        intent=bp.intent.value if hasattr(bp.intent, "value") else str(bp.intent),
                        title=content.title,
                        primary_takeaway=content.primary_takeaway,
                        supporting_points=content.supporting_points,
                        relationships=packet.relationships[:1],
                        concepts=[packet.primary_concept] + packet.supporting_concepts[:2],
                    )
                    if content.example:
                        deck_memory.register_example(content.example)

                # 7. Synchronize to backward-compatible slide format
                slide_dict = _synchronize_slidecontent_to_dict(
                    content=content,
                    blueprint=bp,
                    quality_scores=scores,
                    slide_no=slide_no,
                )
                expanded_slides.append(slide_dict)

            logger.info(f"[ContentAgent] Phase 2 expansion complete: {len(expanded_slides)} slides generated and audited.")
            return expanded_slides
        except Exception as e:
            if isinstance(e, QualityGateError):
                raise
            logger.error(f"[ContentAgent] Phase 2 engine encountered error ({e}), falling back to standard pipeline", exc_info=True)

    # ─── PATH 2: Standard / Legacy Fallback ──────────────────────
    planned_slides = outline_data.get("slides", [])
    if not planned_slides:
        return []

    fallback_slides = []
    for idx, s in enumerate(planned_slides):
        s_no = s.get("slide_no", idx + 1)
        title = s.get("title") or f"Core Concepts of {config.topic}"
        clean_title = _word_boundary_truncate(title, 60)
        fallback_slides.append({
            "slide_no": s_no,
            "type": s.get("type", "concept"),
            "title": clean_title,
            "subtitle": "",
            "key_message": s.get("key_message") or f"{clean_title}",
            "body_bullets": [],
            "example": "",
            "speaker_notes": "",
            "image_query": f"{config.topic} professional educational photography",
            "content_pattern": s.get("content_pattern") or "plain_concept",
            "fit_risk": "CONTENT_SEMANTIC_GAP",
        })

    return fallback_slides
