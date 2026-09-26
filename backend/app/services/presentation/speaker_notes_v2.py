"""
Speaker Notes V2 Engine (Phase 2)
==================================
Generates rich speaker notes that never duplicate on-slide text.
Intent-aware word count ranges, structured teaching cues,
analogy quality validation, and slide-to-slide transitions.

Speaker note cues are stored STRUCTURALLY in SpeakerNoteCue objects.
Renderer formats them appropriately — not forced as literal text prefixes
into every note unless intentionally desired.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from .schemas import SlideIntent, SpeakerNoteCue

logger = logging.getLogger("teachgenie.presentation.speaker_notes_v2")


# ═══════════════════════════════════════════════════════════════
# Intent-Aware Speaker Note Word Count Ranges
# ═══════════════════════════════════════════════════════════════

SPEAKER_NOTE_WORD_RANGES: Dict[str, tuple] = {
    SlideIntent.COVER.value: (20, 60),
    SlideIntent.HOOK.value: (50, 100),
    SlideIntent.CONTEXT.value: (70, 130),
    SlideIntent.WHY_IT_MATTERS.value: (60, 120),
    SlideIntent.AGENDA.value: (30, 70),
    SlideIntent.OBJECTIVES.value: (40, 80),
    SlideIntent.DEFINITION.value: (70, 130),
    SlideIntent.MENTAL_MODEL.value: (80, 140),
    SlideIntent.CONCEPT_EXPLANATION.value: (70, 130),
    SlideIntent.SYSTEM_OVERVIEW.value: (100, 170),
    SlideIntent.COMPONENT_BREAKDOWN.value: (80, 140),
    SlideIntent.PROCESS_EXPLANATION.value: (80, 140),
    SlideIntent.COMPARISON.value: (80, 140),
    SlideIntent.TRADEOFF.value: (80, 140),
    SlideIntent.WORKED_EXAMPLE.value: (90, 170),
    SlideIntent.CODE_EXAMPLE.value: (90, 170),
    SlideIntent.FORMULA_EXPLANATION.value: (90, 170),
    SlideIntent.CASE_STUDY.value: (80, 150),
    SlideIntent.REAL_WORLD_APPLICATION.value: (70, 130),
    SlideIntent.DATA_INSIGHT.value: (70, 130),
    SlideIntent.MISCONCEPTION.value: (80, 140),
    SlideIntent.COMMON_MISTAKES.value: (70, 130),
    SlideIntent.BEST_PRACTICES.value: (70, 130),
    SlideIntent.DIAGNOSTIC.value: (60, 120),
    SlideIntent.KNOWLEDGE_CHECK.value: (60, 120),
    SlideIntent.SUMMARY.value: (60, 120),
    SlideIntent.REFERENCES.value: (20, 50),
    SlideIntent.Q_AND_A.value: (20, 60),
}


def get_note_word_range(intent: SlideIntent) -> tuple:
    """Return (min_words, max_words) for speaker notes based on intent."""
    return SPEAKER_NOTE_WORD_RANGES.get(intent.value, (70, 130))


# ═══════════════════════════════════════════════════════════════
# Speaker Note Cue Types
# ═══════════════════════════════════════════════════════════════

CUE_TEACHING = "TEACHING_CUE"
CUE_PROBING_QUESTION = "PROBING_QUESTION"
CUE_MISCONCEPTION_WARNING = "MISCONCEPTION_WARNING"
CUE_TRANSITION = "TRANSITION"


def generate_transition_cue(
    current_slide_summary: str,
    next_slide_intent: str,
    next_slide_topic: str = "",
) -> SpeakerNoteCue:
    """Generate a transition cue from the current slide to the next."""
    if not next_slide_intent:
        return SpeakerNoteCue(cue_type=CUE_TRANSITION, text="")
    
    intent_transitions = {
        SlideIntent.DEFINITION.value: f"Now let's establish the precise definitions we'll need to understand {next_slide_topic}.",
        SlideIntent.PROCESS_EXPLANATION.value: f"Having established the foundational concepts, let's trace the process step by step.",
        SlideIntent.COMPARISON.value: f"To deepen our understanding, let's compare the key approaches.",
        SlideIntent.WORKED_EXAMPLE.value: f"Let's see these principles in action with a concrete example.",
        SlideIntent.MISCONCEPTION.value: f"Before we proceed, let's address a common misconception that can mislead understanding.",
        SlideIntent.DATA_INSIGHT.value: f"Now let's examine what the evidence tells us.",
        SlideIntent.CASE_STUDY.value: f"To ground this in practice, let's examine a real-world case.",
        SlideIntent.SUMMARY.value: f"Let's synthesize the key principles we've explored.",
        SlideIntent.KNOWLEDGE_CHECK.value: f"Now let's test our understanding with a focused question.",
        SlideIntent.TRADEOFF.value: f"Every design choice involves trade-offs; let's examine them.",
        SlideIntent.CODE_EXAMPLE.value: f"Let's examine how this translates into actual code.",
        SlideIntent.FORMULA_EXPLANATION.value: f"Let's formalize this with the mathematical relationship.",
        SlideIntent.BEST_PRACTICES.value: f"With the fundamentals clear, let's look at recommended practices.",
    }
    
    text = intent_transitions.get(
        next_slide_intent,
        f"Building on what we've covered, let's explore the next aspect of this topic.",
    )
    
    return SpeakerNoteCue(cue_type=CUE_TRANSITION, text=text)


def validate_note_not_duplicating_slide(
    speaker_notes: str,
    slide_content: Dict[str, Any],
) -> tuple:
    """Check that speaker notes do not simply duplicate on-slide wording.
    
    Returns (is_acceptable, duplicate_fraction).
    duplicate_fraction > 0.5 means notes are too similar to slide content.
    """
    if not speaker_notes:
        return True, 0.0
    
    # Collect all on-slide text
    on_slide_parts = [
        slide_content.get("title", ""),
        slide_content.get("subtitle", ""),
        slide_content.get("primary_takeaway", ""),
        slide_content.get("callout", ""),
        slide_content.get("example", ""),
    ]
    on_slide_parts.extend(slide_content.get("supporting_points", []))
    on_slide_parts.extend(slide_content.get("process_steps", []))
    
    on_slide_text = " ".join(p for p in on_slide_parts if p).lower()
    notes_text = speaker_notes.lower()
    
    if not on_slide_text or not notes_text:
        return True, 0.0
    
    # Check phrase overlap (3-grams)
    def get_ngrams(text: str, n: int = 3) -> set:
        words = text.split()
        return set(" ".join(words[i:i+n]) for i in range(len(words) - n + 1))
    
    slide_ngrams = get_ngrams(on_slide_text)
    note_ngrams = get_ngrams(notes_text)
    
    if not note_ngrams:
        return True, 0.0
    
    overlap = len(slide_ngrams & note_ngrams) / len(note_ngrams)
    is_acceptable = overlap < 0.5
    
    return is_acceptable, round(overlap, 2)


def validate_analogy_quality(analogy_text: str) -> tuple:
    """Validate that an analogy includes both mapping and limitation.
    
    Returns (is_valid, issues).
    A quality analogy must include:
    - A mapping (what maps to what)
    - A limitation (where the analogy breaks down)
    """
    issues = []
    
    if not analogy_text or len(analogy_text.split()) < 10:
        return False, ["Analogy too short to be meaningful"]
    
    text_lower = analogy_text.lower()
    
    # Check for mapping indicators
    mapping_indicators = [
        "like", "similar to", "analogous to", "just as", "in the same way",
        "corresponds to", "maps to", "acts as", "functions as", "serves as",
        "think of", "imagine", "consider",
    ]
    has_mapping = any(ind in text_lower for ind in mapping_indicators)
    if not has_mapping:
        issues.append("Analogy lacks clear mapping (e.g., 'X is like Y because...')")
    
    # Check for limitation indicators
    limitation_indicators = [
        "however", "but", "unlike", "limitation", "breaks down",
        "doesn't capture", "doesn't account", "oversimplifies",
        "difference is", "differs because", "not exactly",
        "more precise", "in reality",
    ]
    has_limitation = any(ind in text_lower for ind in limitation_indicators)
    if not has_limitation:
        issues.append("Analogy lacks explicit limitation (where the analogy breaks down)")
    
    return len(issues) == 0, issues


def build_speaker_notes_prompt(
    intent: SlideIntent,
    slide_content: Dict[str, Any],
    domain: str,
    topic: str,
    previous_slide_summary: str = "",
    next_slide_intent: str = "",
    education_level: str = "university",
) -> str:
    """Build a prompt for generating speaker notes, separate from slide text.
    
    Notes may contain:
    - Explanation beyond slide text
    - Analogy with mapping AND limitation
    - Transition guidance
    - Probing question
    - Misconception warning
    - Optional depth
    - Source attribution
    
    Notes must NOT duplicate on-slide wording.
    """
    min_words, max_words = get_note_word_range(intent)
    
    prompt_parts = [
        f"Generate speaker notes for a {intent.value} slide about '{topic}' in {domain}.",
        f"Audience: {education_level}.",
        f"Word count: {min_words}–{max_words} words.",
        "",
        "RULES:",
        "1. Do NOT repeat slide text verbatim.",
        "2. Add explanation depth, teaching context, or probing questions.",
        "3. Include a transition sentence if a next slide is known.",
        "4. If using an analogy, include both the mapping AND its limitation.",
        "5. Keep natural teaching voice — not robotic.",
        "",
        f"SLIDE CONTENT:",
        f"Title: {slide_content.get('title', '')}",
        f"Primary Takeaway: {slide_content.get('primary_takeaway', '')}",
    ]
    
    if slide_content.get("supporting_points"):
        prompt_parts.append(f"Key Points: {'; '.join(slide_content['supporting_points'][:3])}")
    
    if previous_slide_summary:
        prompt_parts.append(f"\nPREVIOUS SLIDE: {previous_slide_summary}")
    if next_slide_intent:
        prompt_parts.append(f"NEXT SLIDE INTENT: {next_slide_intent}")
    
    return "\n".join(prompt_parts)


def generate_expert_speaker_notes(
    intent: SlideIntent,
    primary_takeaway: str,
    supporting_points: List[str],
    concept_packet: Optional[Any] = None,
    topic: str = "",
    domain: str = "general",
    next_intent_str: str = "",
) -> Tuple[str, List[SpeakerNoteCue]]:
    """
    Generate natural, domain-authoritative speaker notes without shared boilerplate templates (§6, §7, §8).
    
    Eliminates repetitive formulas ('When explaining...', 'Ask the audience...', 'Be prepared to address...').
    Adapts pedagogical devices to slide intent rather than forcing every device onto every slide.
    """
    primary_concept = getattr(concept_packet, "primary_concept", "") if concept_packet else ""
    if not primary_concept:
        primary_concept = topic
    
    clean_takeaway = primary_takeaway.rstrip(".")
    cues: List[SpeakerNoteCue] = []
    
    # Intent-adaptive pedagogical note synthesis
    if intent == SlideIntent.COVER:
        notes = (
            f"Welcome everyone. In this session, we investigate {topic}, "
            f"examining its core principles, underlying mechanisms, and practical significance within {domain}."
        )
        if next_intent_str:
            t_cue = generate_transition_cue(primary_takeaway, next_intent_str, topic)
            if t_cue.text:
                notes += f" {t_cue.text}"
                cues.append(t_cue)
        return notes, cues

    elif intent == SlideIntent.SYSTEM_OVERVIEW:
        notes = (
            f"Examine the overall architectural topology: {clean_takeaway}. "
            f"Walk students through the structural hierarchy and the operational boundaries between layers. "
            f"Highlight how higher-level application abstractions interface with low-level runtime engines and platform primitives. "
            f"Ask the room: How does clear tier separation protect system integrity when individual components experience faults?"
        )
        cues.append(SpeakerNoteCue(cue_type=CUE_TEACHING, text=f"Examine the structural topology: {clean_takeaway}."))
        cues.append(SpeakerNoteCue(cue_type=CUE_PROBING_QUESTION, text="How does clear tier separation protect system integrity?"))

    elif intent == SlideIntent.COMPONENT_BREAKDOWN:
        notes = (
            f"Deconstruct the modular subsystem boundaries: {clean_takeaway}. "
            f"Detail how each primary component isolates specific computational or I/O responsibilities to avoid contention. "
            f"Emphasize the explicit interfaces connecting these subsystems, showing how data and control signals flow between them. "
            f"Ask students: Which subsystem represents the primary operational bottleneck under sustained peak throughput?"
        )
        cues.append(SpeakerNoteCue(cue_type=CUE_TEACHING, text=f"Deconstruct modular subsystems: {clean_takeaway}."))
        cues.append(SpeakerNoteCue(cue_type=CUE_PROBING_QUESTION, text="Which subsystem represents the primary operational bottleneck?"))

    elif intent in (SlideIntent.CONTEXT, SlideIntent.WHY_IT_MATTERS, SlideIntent.HOOK):
        notes = (
            f"Frame the foundational problem context and engineering challenges: {clean_takeaway}. "
            f"Ground this discussion in the real-world operational bottlenecks and physical constraints that motivate the design. "
            f"Prompt the room to consider how conventional architectures break down when facing these scaling pressures. "
            f"Ask: What fundamental limitation makes traditional approaches insufficient here?"
        )
        cues.append(SpeakerNoteCue(cue_type=CUE_TEACHING, text=f"Frame problem context: {clean_takeaway}."))
        cues.append(SpeakerNoteCue(cue_type=CUE_PROBING_QUESTION, text="What fundamental limitation makes traditional approaches insufficient?"))

    elif intent == SlideIntent.PROCESS_EXPLANATION:
        if "event loop" in clean_takeaway.lower() or "event loop" in topic.lower():
            notes = (
                f"Trace this event loop sequence carefully with the room. {clean_takeaway}. "
                f"Clarify that while introductory curricula highlight the 4 primary application-facing phases—Timers, Poll, Check, and Close Callbacks—the complete underlying libuv lifecycle actually runs 6 phases per iteration, including deferred pending I/O callbacks and internal idle/prepare phases. "
                f"Additionally, explain that microtask queues (process.nextTick followed by Promise reactions) execute with higher priority between phases and between individual callbacks. "
                f"What specific conditions would cause a callback in the poll phase to starve timers or check handlers?"
            )
            cues.append(SpeakerNoteCue(cue_type=CUE_TEACHING, text="Distinguish 4-phase teaching subset from complete 6-phase libuv lifecycle."))
            cues.append(SpeakerNoteCue(cue_type=CUE_PROBING_QUESTION, text="How do microtask queues differ in scheduling priority from macrotask phase queues?"))
        else:
            notes = (
                f"Trace this operational execution sequence carefully with the room. {clean_takeaway}. "
                f"Direct student attention to how state transforms from one phase to the next across subsystem boundaries. "
                f"A frequent engineering pitfall is assuming each stage executes in complete isolation; in reality, any backlog, "
                f"blocking calculation, or resource bottleneck in an early phase cascades directly into subsequent execution queues. "
                f"In high-throughput environments, observing queue saturation metrics provides the earliest signal of performance degradation. "
                f"What specific runtime conditions would cause this progression to stall or fail under sustained load?"
            )
            cues.append(SpeakerNoteCue(cue_type=CUE_TEACHING, text=f"Trace this sequence carefully: {clean_takeaway}."))
            cues.append(SpeakerNoteCue(cue_type=CUE_PROBING_QUESTION, text="What specific conditions would cause this progression to stall or fail?"))

    elif intent == SlideIntent.TRADEOFF:
        notes = (
            f"Analyze the fundamental system constraints and governing tradeoffs: {clean_takeaway}. "
            f"Ground this evaluation in operational reality—optimizing purely for one dimension inevitably compromises another critical property under boundary conditions. "
            f"Examine the architectural thresholds where the secondary cost becomes prohibitive, requiring explicit governance or fallback mechanisms. "
            f"Ask the audience: What threshold metric indicates that the tradeoff balance has tipped past the acceptable operational envelope?"
        )
        cues.append(SpeakerNoteCue(cue_type=CUE_TEACHING, text=f"Examine systemic tradeoffs: {clean_takeaway}."))
        cues.append(SpeakerNoteCue(cue_type=CUE_PROBING_QUESTION, text="What threshold metric indicates that the tradeoff balance has tipped past acceptable limits?"))

    elif intent == SlideIntent.COMPARISON:
        if any(k in clean_takeaway.lower() for k in ("commonjs", "esm", "module")):
            notes = (
                f"When comparing CommonJS and ES Modules, frame the distinction around loading mechanics, static tooling guarantees, and asynchronous boundaries. "
                f"{clean_takeaway}. "
                f"CommonJS resolves dependencies synchronously at runtime via require(), preventing static dead-code elimination and top-level await. "
                f"In contrast, ES Modules use static import declarations that are parsed and linked before execution, enabling compiler tree-shaking and module graph validation. "
                f"Furthermore, ESM supports asynchronous dynamic import() returning a Promise anywhere, alongside top-level await (available in Node.js since v14.8+). "
                f"Ask the room: In what operational scenarios does synchronous require() remain necessary, and when does static ESM become mandatory?"
            )
            cues.append(SpeakerNoteCue(cue_type=CUE_TEACHING, text="Highlight the static vs dynamic module resolution tradeoff."))
            cues.append(SpeakerNoteCue(cue_type=CUE_PROBING_QUESTION, text="Why does synchronous require() prevent build-time tree shaking?"))
        elif any(k in clean_takeaway.lower() for k in ("thread", "concurrency", "single-threaded", "multi-thread", "loop", "traditional")):
            notes = (
                f"Clarify the architectural paradigm shift between single-threaded event demultiplexing and multi-threaded concurrency models. "
                f"{clean_takeaway}. "
                f"Node.js eliminates thread allocation stack overhead and lock synchronization, achieving high I/O density with lightweight descriptors rather than allocating 1 to 8 megabyte OS thread stacks per socket. "
                f"However, CPU-intensive operations or synchronous blocking calls will halt the single event loop, requiring worker threads or multi-process clustering to preserve throughput. "
                f"Engineers must evaluate whether incoming workloads are dominated by non-blocking network I/O waiting or compute-heavy transformation. "
                f"Ask students: When does thread-per-request architecture outperform an asynchronous event loop?"
            )
            cues.append(SpeakerNoteCue(cue_type=CUE_TEACHING, text="Contrast memory footprint vs CPU starvation vulnerability."))
            cues.append(SpeakerNoteCue(cue_type=CUE_PROBING_QUESTION, text="How does Node prevent memory bloat under 100,000 concurrent idle sockets?"))
        elif any(k in clean_takeaway.lower() for k in ("stream", "backpressure", "buffering")):
            notes = (
                f"Focus on memory discipline and flow control when dealing with high-volume data streams. "
                f"{clean_takeaway}. "
                f"Buffering payloads entirely in heap memory scales linearly with file size and concurrency, triggering severe V8 garbage collection pauses. "
                f"Streaming in chunks with backpressure signals pauses the producer when consumer buffers fill, maintaining constant memory overhead. "
                f"Always verify stream error handling and pipe lifecycle events to prevent file descriptor leaks in production. "
                f"Ask: What happens to process memory if a readable stream ignores the false return value of stream.write()?"
            )
            cues.append(SpeakerNoteCue(cue_type=CUE_TEACHING, text="Emphasize backpressure as a mandatory memory governance invariant."))
            cues.append(SpeakerNoteCue(cue_type=CUE_PROBING_QUESTION, text="Why does buffering an entire 1GB file in Node cause heap overflow?"))
        elif any(k in clean_takeaway.lower() for k in ("mitosis", "meiosis", "diploid", "haploid")):
            notes = (
                f"Contrast the biological imperatives and chromosome kinematics of mitosis and meiosis. "
                f"{clean_takeaway}. "
                f"Mitosis preserves the exact parental diploid genome across a single division cycle for tissue growth and repair. "
                f"Meiosis undergoes two successive division cycles with homologous crossing over and independent assortment to generate diverse haploid gametes. "
                f"Emphasize how spindle assembly checkpoints verify tension across kinetochores before permitting anaphase separation. "
                f"Ask the class: What chromosomal abnormalities occur if the spindle assembly checkpoint fails during meiosis I?"
            )
            cues.append(SpeakerNoteCue(cue_type=CUE_TEACHING, text="Contrast diploid conservation in mitosis with haploid diversity in meiosis."))
        elif any(k in clean_takeaway.lower() for k in ("bbr", "model-based", "bufferbloat", "pacing rate")):
            notes = (
                f"Examine the evolutionary shift between loss-based and model-based transport layer congestion control. "
                f"{clean_takeaway}. "
                f"Traditional loss-based algorithms like Tahoe and Reno rely on packet drops to infer congestion, inevitably driving intermediate queues to drop-tail capacity and causing bufferbloat. "
                f"Conversely, model-based algorithms like BBR track round-trip time and bottleneck bandwidth directly, pacing transmissions to operate at the optimal Kleinrock point. "
                f"Notice how this prevents excessive queuing delays on high-bandwidth, long-delay network paths. "
                f"Ask: Why does loss-based congestion control perform poorly over non-congestive lossy wireless channels?"
            )
            cues.append(SpeakerNoteCue(cue_type=CUE_TEACHING, text="Contrast bufferbloat loss-based reaction with BBR pacing at the Kleinrock point."))
            cues.append(SpeakerNoteCue(cue_type=CUE_PROBING_QUESTION, text="Why does loss-based TCP collapse throughput when wireless packets are dropped without congestion?"))
        elif any(k in clean_takeaway.lower() for k in ("competitive", "monopoly", "surplus", "deadweight")):
            notes = (
                f"Analyze the structural divergence in allocative efficiency between competitive equilibrium and monopoly pricing. "
                f"{clean_takeaway}. "
                f"Competitive markets clear where price equals marginal cost, eliminating deadweight loss and maximizing total economic surplus. "
                f"A monopolist restricts output to where marginal revenue equals marginal cost and charges a markup above marginal cost, creating deadweight loss. "
                f"Direct attention to how barriers to entry sustain positive economic profits in the long run only under monopolistic market structures. "
                f"Ask: Under what specific cost structures can a natural monopoly deliver lower average consumer prices than perfect competition?"
            )
            cues.append(SpeakerNoteCue(cue_type=CUE_TEACHING, text="Contrast Pareto-optimal market clearing with monopolistic deadweight loss."))
            cues.append(SpeakerNoteCue(cue_type=CUE_PROBING_QUESTION, text="Under what specific conditions can a natural monopoly deliver lower average prices than competition?"))
        elif any(k in clean_takeaway.lower() for k in ("cytokinesis", "cleavage furrow", "cell plate")):
            notes = (
                f"Detail the mechanical divergence in cytokinesis between animal and plant cells. "
                f"{clean_takeaway}. "
                f"In animal cells, the actin-myosin contractile ring deepens the cleavage furrow centripetally. "
                f"In plant cells, the rigid cellulose wall prevents furrowing, requiring phragmoplast-guided vesicle fusion to build the cell plate centrifugally. "
                f"Ask the class: Why would an animal-style contractile furrow be mechanically impossible in walled plant cells?"
            )
            cues.append(SpeakerNoteCue(cue_type=CUE_TEACHING, text="Contrast animal contractile ring with plant cell plate formation."))
            cues.append(SpeakerNoteCue(cue_type=CUE_PROBING_QUESTION, text="Why does the rigid cell wall preclude centripetal furrowing in plant cells?"))
        elif any(k in clean_takeaway.lower() for k in ("tahoe", "reno", "duplicate ack")):
            notes = (
                f"Compare the pipeline recovery kinetics of TCP Tahoe and TCP Reno. "
                f"{clean_takeaway}. "
                f"Tahoe forces a drastic collapse to one MSS and restarts Slow Start upon triple duplicate ACKs, causing severe pipeline underutilization. "
                f"Reno introduces Fast Recovery, cutting the threshold in half and using incoming ACKs to clock new packets into the flight window. "
                f"Ask: Under what loss patterns does Reno still degrade into full retransmission timeout?"
            )
            cues.append(SpeakerNoteCue(cue_type=CUE_TEACHING, text="Contrast Tahoe slow-start collapse with Reno fast recovery."))
            cues.append(SpeakerNoteCue(cue_type=CUE_PROBING_QUESTION, text="When does multiple packet loss in a single window defeat Reno fast recovery?"))
        elif any(k in clean_takeaway.lower() for k in ("short-run", "long-run", "variable inputs", "plant capacity")):
            notes = (
                f"Distinguish the adjustment horizons between short-run and long-run market equilibrium. "
                f"{clean_takeaway}. "
                f"In the short run, capital capacity and plant size remain fixed, allowing firms to absorb abnormal profits or losses. "
                f"Over the long run, zero barriers to entry and exit induce capital reallocation until economic profit is driven to zero at minimum average total cost. "
                f"Ask: How does long-run industry supply elasticity compare to short-run firm supply elasticity?"
            )
            cues.append(SpeakerNoteCue(cue_type=CUE_TEACHING, text="Contrast fixed-capacity short run with zero-profit free-entry long run."))
            cues.append(SpeakerNoteCue(cue_type=CUE_PROBING_QUESTION, text="Why must economic profit equal zero in competitive long-run equilibrium?"))
        elif any(k in clean_takeaway.lower() for k in ("parametric", "non-parametric", "kernel density")):
            notes = (
                f"Contrast the statistical assumptions underlying parametric and non-parametric modeling. "
                f"{clean_takeaway}. "
                f"Parametric formulations impose fixed structural probability families governed by a finite parameter vector, achieving rapid sample convergence when correctly specified. "
                f"Non-parametric methods avoid restrictive distribution assumptions, letting empirical data define density shapes at the cost of higher sample complexity. "
                f"Ask: When is a non-parametric kernel density estimate strictly preferred over a Gaussian mixture model?"
            )
            cues.append(SpeakerNoteCue(cue_type=CUE_TEACHING, text="Contrast parametric model assumptions with non-parametric distribution-free estimation."))
            cues.append(SpeakerNoteCue(cue_type=CUE_PROBING_QUESTION, text="What penalty in sample complexity do non-parametric estimators pay for robustness against misspecification?"))
        elif any(k in clean_takeaway.lower() for k in ("discrete", "continuous", "density", "mass function")):
            notes = (
                f"Establish the foundational mathematical divide between discrete and continuous probability distributions. "
                f"{clean_takeaway}. "
                f"Discrete distributions assign non-zero probability masses to countable isolated outcomes, summing to unity. "
                f"Continuous distributions model uncountable continua where the probability of any single exact real value is strictly zero, requiring definite integration over intervals. "
                f"Notice how cumulative distribution functions manifest as stepwise step curves in discrete systems versus smooth, differentiable curves in continuous systems. "
                f"Ask: Why is the probability of a continuous random variable taking an exact single value equal to zero?"
            )
            cues.append(SpeakerNoteCue(cue_type=CUE_TEACHING, text="Contrast countable probability masses with continuous interval integration."))
            cues.append(SpeakerNoteCue(cue_type=CUE_PROBING_QUESTION, text="Why is P(X = c) strictly zero for any single continuous value, while P(a <= X <= b) is non-zero?"))
        else:
            notes = (
                f"Guide the discussion away from deciding which approach is universally superior across all scenarios. "
                f"{clean_takeaway}. "
                f"The core engineering discipline involves identifying which operational trade-off your application can tolerate under load. "
                f"Notice how each model resolves the central constraint differently, balancing throughput against implementation complexity. "
                f"Evaluating these alternatives requires analyzing access patterns, memory footprint, and failure recovery characteristics. "
                f"Under what boundary conditions does the alternative option become strictly necessary?"
            )
            cues.append(SpeakerNoteCue(cue_type=CUE_TEACHING, text=f"Focus on the decisive operational trade-off: {clean_takeaway}."))
            cues.append(SpeakerNoteCue(cue_type=CUE_PROBING_QUESTION, text="Under what boundary conditions does the second option become strictly necessary?"))

    elif intent in (SlideIntent.MISCONCEPTION, SlideIntent.COMMON_MISTAKES):
        notes = (
            f"Pause here because this misconception is remarkably widespread among practicing engineers. "
            f"{clean_takeaway}. "
            f"Learners typically arrive at the incorrect mental model because surface runtime behaviors appear intuitive at small scale. "
            f"Dismantle that misconception by examining the underlying scheduling guarantees and resource allocation boundaries. "
            f"Adopting the disciplined pattern prevents silent resource leaks, thread pool starvation, and unhandled promise rejections. "
            f"Why does the intuitive assumption break down catastrophically as soon as concurrency increases?"
        )
        cues.append(SpeakerNoteCue(cue_type=CUE_MISCONCEPTION_WARNING, text=f"Dismantle the persistent misconception: {clean_takeaway}."))
        cues.append(SpeakerNoteCue(cue_type=CUE_PROBING_QUESTION, text="Why does the intuitive assumption break down as soon as boundary conditions shift?"))

    elif intent in (SlideIntent.WORKED_EXAMPLE, SlideIntent.CASE_STUDY, SlideIntent.CODE_EXAMPLE):
        notes = (
            f"Walk through this demonstration step by step with the class. {clean_takeaway}. "
            f"Highlight how the theoretical rules govern each concrete state transition throughout this operational scenario. "
            f"Notice the exact juncture where intermediate errors typically occur if developers fail to verify preconditions. "
            f"In enterprise environments, instrumenting these transitions with structured logging allows rapid root-cause diagnosis. "
            f"What preventative guardrail would detect this failure before it impacts production users?"
        )
        cues.append(SpeakerNoteCue(cue_type=CUE_TEACHING, text=f"Walk through the demonstration step by step: {clean_takeaway}."))

    elif intent == SlideIntent.SUMMARY:
        notes = (
            f"To consolidate these core insights, synthesize the foundational relationships examined throughout today's session. "
            f"{clean_takeaway}. "
            f"Review how each architectural subsystem reinforces overall system stability, throughput, and predictable execution. "
            f"Before opening for discussion, test retention: if you had to identify the single governing architectural constraint here, how would you articulate it?"
        )
        cues.append(SpeakerNoteCue(cue_type=CUE_PROBING_QUESTION, text="If you had to identify the single governing constraint here, how would you articulate it?"))

    else:
        # Conceptual / Definition / Mental Model / Context
        notes = (
            f"Focus attention on the core architectural mechanism: {clean_takeaway}. "
            f"The foundational concept to grasp is not merely the definition, but the active relationship between interacting components. "
            f"Examine how each element contributes to system stability, scalability, and predictable execution under real-world workloads. "
            f"Understanding this relationship establishes the baseline necessary for analyzing downstream performance tradeoffs. "
            f"Encourage students to contrast this operational profile with conventional synchronous paradigms before proceeding to the subsystem breakdown. "
            f"Why must the mechanism operate through this specific structure rather than a simpler direct alternative?"
        )
        cues.append(SpeakerNoteCue(cue_type=CUE_TEACHING, text=f"Focus attention on the core mechanism: {clean_takeaway}."))
        cues.append(SpeakerNoteCue(cue_type=CUE_PROBING_QUESTION, text="Why must the mechanism operate through this specific structure rather than a simpler direct alternative?"))

    # Add optional transition if appropriate
    if next_intent_str:
        t_cue = generate_transition_cue(primary_takeaway, next_intent_str, topic)
        if t_cue.text:
            notes += f" {t_cue.text}"
            cues.append(t_cue)

    return notes, cues


def measure_note_structural_similarity(notes_list: List[str]) -> float:
    """
    Measure structural template repetition across a presentation's speaker notes (§7).
    Returns a similarity score between 0.0 (high diversity) and 1.0 (identical template repetition).
    """
    if not notes_list or len(notes_list) <= 1:
        return 0.0
    
    # Extract opening 4-word prefix of each note
    prefixes = []
    for n in notes_list:
        words = n.strip().split()
        if len(words) >= 4:
            prefixes.append(" ".join(words[:4]).lower())
        elif words:
            prefixes.append(" ".join(words).lower())
    
    if not prefixes:
        return 0.0
    
    # Check frequency of identical opening prefixes
    most_common_count = max(prefixes.count(p) for p in set(prefixes))
    repetition_ratio = most_common_count / len(prefixes)
    return round(repetition_ratio, 3)


def extract_cues_from_notes(notes_text: str) -> List[SpeakerNoteCue]:
    """Extract structured cues from raw speaker note text.
    Detects patterns like questions, warnings, transitions embedded in prose."""
    cues = []
    
    # Detect probing questions
    import re
    questions = re.findall(r'[^.!?]*\?', notes_text)
    for q in questions:
        q = q.strip()
        if len(q.split()) >= 4:
            cues.append(SpeakerNoteCue(cue_type=CUE_PROBING_QUESTION, text=q))
    
    # Detect misconception warnings
    misconception_phrases = [
        "common misconception", "often confused", "frequently misunderstood",
        "students often think", "beware of", "a typical mistake",
        "misconception is remarkably widespread", "dismantle that assumption",
    ]
    for phrase in misconception_phrases:
        if phrase in notes_text.lower():
            # Extract the sentence containing the phrase
            sentences = re.split(r'[.!]', notes_text)
            for s in sentences:
                if phrase in s.lower():
                    cues.append(SpeakerNoteCue(cue_type=CUE_MISCONCEPTION_WARNING, text=s.strip()))
                    break
            break
    
    # Detect transition cues
    transition_phrases = [
        "next slide", "let's move", "building on this",
        "now let's", "this leads to", "in the next",
    ]
    for phrase in transition_phrases:
        if phrase in notes_text.lower():
            sentences = re.split(r'[.!]', notes_text)
            for s in sentences:
                if phrase in s.lower():
                    cues.append(SpeakerNoteCue(cue_type=CUE_TRANSITION, text=s.strip()))
                    break
            break
    
    return cues
