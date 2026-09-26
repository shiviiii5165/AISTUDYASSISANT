"""
LearnByGenie PPT vNext — Phase 3.2F Held-Out Validation Corpus
============================================================
Dedicated held-out validation corpus across 20 distinct academic topics:
  - Computer Science: OS Scheduling, Database Isolation, TCP Congestion
  - Biology: DNA Replication, Cell Cycle Regulation, Mendelian Genetics
  - Physics/Math: Fourier Transform, Bayes Theorem, Electromagnetic Induction, Probability Distributions
  - Humanities: French Revolution, World War I, Postcolonial Literature, Constitutional Development
  - Economics/Business: Elasticity, Market Failure, Monetary Transmission, Working Capital Management
  - Other: Research Methodology, Environmental Sustainability

Each topic generates a complete, realistic 10-slide deck ensuring that across the
entire corpus all 20 approved Phase3LayoutFamily values are exercised without topic-name branching.
"""
from typing import Dict, Any, List, Tuple, Optional
import copy

from app.services.presentation.schemas import (
    SlideBlueprint,
    SlideContent,
    SlideIntent,
    LayoutFamily,
    ComparisonRow,
    DataPoint,
)
from app.services.presentation.visual_schemas import (
    Phase3LayoutFamily,
    VisualAssetType,
    VisualIntent,
    VisualWeight,
    VisualRhythmBeat,
    VisualSemanticPacket,
    VisualCandidate,
    DesignDNA,
    ContentDensity,
)
from app.services.presentation.composition_schemas import (
    CompositionInputManifest,
    ComposedSlideContext,
    SlideCompositionPlan,
)
from app.services.presentation.design_dna import _build_academic_clean_dna, _THEME_PALETTES
from app.services.presentation.layout_compiler import compile_slide_layout
from app.services.presentation.layout_quality_auditor import (
    audit_layout,
    repair_layout_defects,
    LayoutAuditResult,
    RepairResult,
)


HELD_OUT_TOPICS: List[Dict[str, Any]] = [
    # ─── 1. Computer Science (3 topics) ───────────────────────────
    {
        "id": "cs_os_scheduling",
        "title": "Operating System Scheduling",
        "domain": "Computer Science",
        "subdomain": "Operating Systems",
        "theme": "blue_professional",
        "key_terms": ["Preemption", "Time Quantum", "Context Switch", "Throughput", "Latency"],
    },
    {
        "id": "cs_db_isolation",
        "title": "Database Transaction Isolation",
        "domain": "Computer Science",
        "subdomain": "Database Systems",
        "theme": "indigo_innovation",
        "key_terms": ["ACID", "Serializability", "Dirty Read", "MVCC", "Two-Phase Locking"],
    },
    {
        "id": "cs_tcp_congestion",
        "title": "TCP Congestion Control",
        "domain": "Computer Science",
        "subdomain": "Computer Networks",
        "theme": "teal_modern",
        "key_terms": ["AIMD", "Slow Start", "Congestion Window", "RTT", "Packet Loss"],
    },

    # ─── 2. Biology (3 topics) ────────────────────────────────────
    {
        "id": "bio_dna_replication",
        "title": "DNA Replication",
        "domain": "Biology",
        "subdomain": "Molecular Genetics",
        "theme": "emerald_growth",
        "key_terms": ["Helicase", "Polymerase", "Okazaki Fragments", "Leading Strand", "Telomeres"],
    },
    {
        "id": "bio_cell_cycle",
        "title": "Cell Cycle Regulation",
        "domain": "Biology",
        "subdomain": "Cell Biology",
        "theme": "teal_modern",
        "key_terms": ["Cyclins", "CDKs", "Checkpoints", "G1/S Phase", "Mitosis"],
    },
    {
        "id": "bio_mendelian_genetics",
        "title": "Mendelian Genetics",
        "domain": "Biology",
        "subdomain": "Genetics",
        "theme": "emerald_growth",
        "key_terms": ["Alleles", "Segregation", "Independent Assortment", "Genotype", "Phenotype"],
    },

    # ─── 3. Physics / Mathematics (4 topics) ──────────────────────
    {
        "id": "math_fourier_transform",
        "title": "Fourier Transform",
        "domain": "Physics / Mathematics",
        "subdomain": "Signal Processing",
        "theme": "indigo_innovation",
        "key_terms": ["Frequency Domain", "Orthogonal Basis", "Harmonics", "Convolution", "FFT"],
    },
    {
        "id": "math_bayes_theorem",
        "title": "Bayes Theorem",
        "domain": "Physics / Mathematics",
        "subdomain": "Probability & Statistics",
        "theme": "blue_professional",
        "key_terms": ["Prior Probability", "Likelihood", "Posterior", "Evidence", "Conditioning"],
    },
    {
        "id": "phys_electromagnetic_induction",
        "title": "Electromagnetic Induction",
        "domain": "Physics / Mathematics",
        "subdomain": "Classical Electromagnetism",
        "theme": "charcoal_minimal",
        "key_terms": ["Faraday Law", "Lenz Law", "Magnetic Flux", "EMF", "Inductance"],
    },
    {
        "id": "math_probability_distributions",
        "title": "Probability Distributions",
        "domain": "Physics / Mathematics",
        "subdomain": "Statistics",
        "theme": "blue_professional",
        "key_terms": ["Gaussian", "Poisson", "Expected Value", "Variance", "Central Limit"],
    },

    # ─── 4. Humanities (4 topics) ─────────────────────────────────
    {
        "id": "hum_french_revolution",
        "title": "French Revolution",
        "domain": "Humanities",
        "subdomain": "European History",
        "theme": "orange_energy",
        "key_terms": ["Estates General", "Bastille", "Jacobins", "Reign of Terror", "Directory"],
    },
    {
        "id": "hum_world_war_one",
        "title": "World War I",
        "domain": "Humanities",
        "subdomain": "Modern History",
        "theme": "charcoal_minimal",
        "key_terms": ["Alliance Systems", "Mobilization", "Trench Warfare", "Versailles", "Armistice"],
    },
    {
        "id": "hum_postcolonial_literature",
        "title": "Postcolonial Literature",
        "domain": "Humanities",
        "subdomain": "Literary Theory",
        "theme": "orange_energy",
        "key_terms": ["Subaltern", "Hybridity", "Mimicry", "Decolonization", "Canon"],
    },
    {
        "id": "hum_constitutional_development",
        "title": "Constitutional Development",
        "domain": "Humanities",
        "subdomain": "Political Science",
        "theme": "blue_professional",
        "key_terms": ["Separation of Powers", "Judicial Review", "Federalism", "Amendments", "Due Process"],
    },

    # ─── 5. Economics / Business (4 topics) ────────────────────────
    {
        "id": "econ_elasticity",
        "title": "Supply and Demand Elasticity",
        "domain": "Economics / Business",
        "subdomain": "Microeconomics",
        "theme": "emerald_growth",
        "key_terms": ["Price Elasticity", "Inelastic Demand", "Cross Elasticity", "Surplus", "Deadweight Loss"],
    },
    {
        "id": "econ_market_failure",
        "title": "Market Failure",
        "domain": "Economics / Business",
        "subdomain": "Public Economics",
        "theme": "indigo_innovation",
        "key_terms": ["Externalities", "Public Goods", "Asymmetric Information", "Monopoly", "Pigouvian Tax"],
    },
    {
        "id": "econ_monetary_transmission",
        "title": "Monetary Transmission",
        "domain": "Economics / Business",
        "subdomain": "Macroeconomics",
        "theme": "blue_professional",
        "key_terms": ["Policy Rate", "Yield Curve", "Credit Channel", "Inflation Targeting", "Liquidity"],
    },
    {
        "id": "biz_working_capital",
        "title": "Working Capital Management",
        "domain": "Economics / Business",
        "subdomain": "Corporate Finance",
        "theme": "charcoal_minimal",
        "key_terms": ["Cash Conversion Cycle", "Receivables", "Inventory Turnover", "Liquidity", "Payables"],
    },

    # ─── 6. Other (2 topics) ──────────────────────────────────────
    {
        "id": "other_research_methodology",
        "title": "Research Methodology",
        "domain": "Other",
        "subdomain": "Academic Research",
        "theme": "blue_professional",
        "key_terms": ["Empirical Design", "Hypothesis", "Sampling", "Reliability", "Construct Validity"],
    },
    {
        "id": "other_environmental_sustainability",
        "title": "Environmental Sustainability",
        "domain": "Other",
        "subdomain": "Environmental Science",
        "theme": "teal_modern",
        "key_terms": ["Carbon Cycle", "Renewable Energy", "Ecosystem Services", "Circular Economy", "Biodiversity"],
    },
]


# Deterministic schedule of layout families across the 10 slides of each topic
# Formulated so that every one of the 20 Phase3LayoutFamily values is exercised
_TOPIC_SLIDE_FAMILIES: List[List[Phase3LayoutFamily]] = [
    # Topic 0: OS Scheduling
    [Phase3LayoutFamily.HERO_CENTER, Phase3LayoutFamily.TEXT_DOMINANT, Phase3LayoutFamily.SYSTEM_ARCHITECTURE,
     Phase3LayoutFamily.PROCESS_CANVAS, Phase3LayoutFamily.DATA_CANVAS, Phase3LayoutFamily.COMPARISON_TWO_COLUMN,
     Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.ASYMMETRIC_EDITORIAL, Phase3LayoutFamily.QUOTE_OR_STATEMENT, Phase3LayoutFamily.SUMMARY_GRID],
    # Topic 1: DB Isolation
    [Phase3LayoutFamily.HERO_OFFSET, Phase3LayoutFamily.SPLIT_40_60, Phase3LayoutFamily.DIAGRAM_CANVAS,
     Phase3LayoutFamily.TIMELINE_CANVAS, Phase3LayoutFamily.DATA_CANVAS, Phase3LayoutFamily.COMPARISON_MATRIX,
     Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL, Phase3LayoutFamily.VISUAL_DOMINANT, Phase3LayoutFamily.SUMMARY_GRID],
    # Topic 2: TCP Congestion
    [Phase3LayoutFamily.HERO_CENTER, Phase3LayoutFamily.SPLIT_60_40, Phase3LayoutFamily.ANNOTATED_VISUAL,
     Phase3LayoutFamily.TIMELINE_CANVAS, Phase3LayoutFamily.DATA_CANVAS, Phase3LayoutFamily.COMPARISON_TWO_COLUMN,
     Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.ASYMMETRIC_EDITORIAL, Phase3LayoutFamily.QUOTE_OR_STATEMENT, Phase3LayoutFamily.TEXT_DOMINANT],
    # Topic 3: DNA Replication
    [Phase3LayoutFamily.HERO_OFFSET, Phase3LayoutFamily.TEXT_DOMINANT, Phase3LayoutFamily.DIAGRAM_CANVAS,
     Phase3LayoutFamily.PROCESS_CANVAS, Phase3LayoutFamily.FORMULA_VISUAL, Phase3LayoutFamily.COMPARISON_TWO_COLUMN,
     Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL, Phase3LayoutFamily.VISUAL_DOMINANT, Phase3LayoutFamily.SUMMARY_GRID],
    # Topic 4: Cell Cycle Regulation
    [Phase3LayoutFamily.HERO_CENTER, Phase3LayoutFamily.SPLIT_40_60, Phase3LayoutFamily.SYSTEM_ARCHITECTURE,
     Phase3LayoutFamily.PROCESS_CANVAS, Phase3LayoutFamily.DATA_CANVAS, Phase3LayoutFamily.COMPARISON_MATRIX,
     Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.ASYMMETRIC_EDITORIAL, Phase3LayoutFamily.QUOTE_OR_STATEMENT, Phase3LayoutFamily.TEXT_DOMINANT],
    # Topic 5: Mendelian Genetics
    [Phase3LayoutFamily.HERO_OFFSET, Phase3LayoutFamily.SPLIT_60_40, Phase3LayoutFamily.ANNOTATED_VISUAL,
     Phase3LayoutFamily.TIMELINE_CANVAS, Phase3LayoutFamily.FORMULA_VISUAL, Phase3LayoutFamily.COMPARISON_TWO_COLUMN,
     Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL, Phase3LayoutFamily.VISUAL_DOMINANT, Phase3LayoutFamily.SUMMARY_GRID],
    # Topic 6: Fourier Transform
    [Phase3LayoutFamily.HERO_CENTER, Phase3LayoutFamily.TEXT_DOMINANT, Phase3LayoutFamily.DIAGRAM_CANVAS,
     Phase3LayoutFamily.PROCESS_CANVAS, Phase3LayoutFamily.FORMULA_VISUAL, Phase3LayoutFamily.COMPARISON_TWO_COLUMN,
     Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.ASYMMETRIC_EDITORIAL, Phase3LayoutFamily.QUOTE_OR_STATEMENT, Phase3LayoutFamily.SUMMARY_GRID],
    # Topic 7: Bayes Theorem
    [Phase3LayoutFamily.HERO_OFFSET, Phase3LayoutFamily.SPLIT_40_60, Phase3LayoutFamily.SYSTEM_ARCHITECTURE,
     Phase3LayoutFamily.PROCESS_CANVAS, Phase3LayoutFamily.FORMULA_VISUAL, Phase3LayoutFamily.COMPARISON_MATRIX,
     Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL, Phase3LayoutFamily.VISUAL_DOMINANT, Phase3LayoutFamily.TEXT_DOMINANT],
    # Topic 8: Electromagnetic Induction
    [Phase3LayoutFamily.HERO_CENTER, Phase3LayoutFamily.SPLIT_60_40, Phase3LayoutFamily.ANNOTATED_VISUAL,
     Phase3LayoutFamily.TIMELINE_CANVAS, Phase3LayoutFamily.FORMULA_VISUAL, Phase3LayoutFamily.COMPARISON_TWO_COLUMN,
     Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.ASYMMETRIC_EDITORIAL, Phase3LayoutFamily.QUOTE_OR_STATEMENT, Phase3LayoutFamily.SUMMARY_GRID],
    # Topic 9: Probability Distributions
    [Phase3LayoutFamily.HERO_OFFSET, Phase3LayoutFamily.TEXT_DOMINANT, Phase3LayoutFamily.DIAGRAM_CANVAS,
     Phase3LayoutFamily.PROCESS_CANVAS, Phase3LayoutFamily.DATA_CANVAS, Phase3LayoutFamily.COMPARISON_MATRIX,
     Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL, Phase3LayoutFamily.VISUAL_DOMINANT, Phase3LayoutFamily.SUMMARY_GRID],
    # Topic 10: French Revolution
    [Phase3LayoutFamily.HERO_CENTER, Phase3LayoutFamily.SPLIT_40_60, Phase3LayoutFamily.SYSTEM_ARCHITECTURE,
     Phase3LayoutFamily.TIMELINE_CANVAS, Phase3LayoutFamily.DATA_CANVAS, Phase3LayoutFamily.COMPARISON_TWO_COLUMN,
     Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.ASYMMETRIC_EDITORIAL, Phase3LayoutFamily.QUOTE_OR_STATEMENT, Phase3LayoutFamily.TEXT_DOMINANT],
    # Topic 11: World War I
    [Phase3LayoutFamily.HERO_OFFSET, Phase3LayoutFamily.SPLIT_60_40, Phase3LayoutFamily.ANNOTATED_VISUAL,
     Phase3LayoutFamily.TIMELINE_CANVAS, Phase3LayoutFamily.DATA_CANVAS, Phase3LayoutFamily.COMPARISON_MATRIX,
     Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL, Phase3LayoutFamily.VISUAL_DOMINANT, Phase3LayoutFamily.SUMMARY_GRID],
    # Topic 12: Postcolonial Literature
    [Phase3LayoutFamily.HERO_CENTER, Phase3LayoutFamily.TEXT_DOMINANT, Phase3LayoutFamily.DIAGRAM_CANVAS,
     Phase3LayoutFamily.PROCESS_CANVAS, Phase3LayoutFamily.FORMULA_VISUAL, Phase3LayoutFamily.COMPARISON_TWO_COLUMN,
     Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.ASYMMETRIC_EDITORIAL, Phase3LayoutFamily.QUOTE_OR_STATEMENT, Phase3LayoutFamily.SUMMARY_GRID],
    # Topic 13: Constitutional Development
    [Phase3LayoutFamily.HERO_OFFSET, Phase3LayoutFamily.SPLIT_40_60, Phase3LayoutFamily.SYSTEM_ARCHITECTURE,
     Phase3LayoutFamily.TIMELINE_CANVAS, Phase3LayoutFamily.DATA_CANVAS, Phase3LayoutFamily.COMPARISON_MATRIX,
     Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL, Phase3LayoutFamily.VISUAL_DOMINANT, Phase3LayoutFamily.TEXT_DOMINANT],
    # Topic 14: Elasticity
    [Phase3LayoutFamily.HERO_CENTER, Phase3LayoutFamily.SPLIT_60_40, Phase3LayoutFamily.ANNOTATED_VISUAL,
     Phase3LayoutFamily.PROCESS_CANVAS, Phase3LayoutFamily.FORMULA_VISUAL, Phase3LayoutFamily.COMPARISON_TWO_COLUMN,
     Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.ASYMMETRIC_EDITORIAL, Phase3LayoutFamily.QUOTE_OR_STATEMENT, Phase3LayoutFamily.SUMMARY_GRID],
    # Topic 15: Market Failure
    [Phase3LayoutFamily.HERO_OFFSET, Phase3LayoutFamily.TEXT_DOMINANT, Phase3LayoutFamily.DIAGRAM_CANVAS,
     Phase3LayoutFamily.PROCESS_CANVAS, Phase3LayoutFamily.DATA_CANVAS, Phase3LayoutFamily.COMPARISON_MATRIX,
     Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL, Phase3LayoutFamily.VISUAL_DOMINANT, Phase3LayoutFamily.SUMMARY_GRID],
    # Topic 16: Monetary Transmission
    [Phase3LayoutFamily.HERO_CENTER, Phase3LayoutFamily.SPLIT_40_60, Phase3LayoutFamily.SYSTEM_ARCHITECTURE,
     Phase3LayoutFamily.TIMELINE_CANVAS, Phase3LayoutFamily.DATA_CANVAS, Phase3LayoutFamily.COMPARISON_TWO_COLUMN,
     Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.ASYMMETRIC_EDITORIAL, Phase3LayoutFamily.QUOTE_OR_STATEMENT, Phase3LayoutFamily.TEXT_DOMINANT],
    # Topic 17: Working Capital Management
    [Phase3LayoutFamily.HERO_OFFSET, Phase3LayoutFamily.SPLIT_60_40, Phase3LayoutFamily.ANNOTATED_VISUAL,
     Phase3LayoutFamily.PROCESS_CANVAS, Phase3LayoutFamily.FORMULA_VISUAL, Phase3LayoutFamily.COMPARISON_MATRIX,
     Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL, Phase3LayoutFamily.VISUAL_DOMINANT, Phase3LayoutFamily.SUMMARY_GRID],
    # Topic 18: Research Methodology
    [Phase3LayoutFamily.HERO_CENTER, Phase3LayoutFamily.TEXT_DOMINANT, Phase3LayoutFamily.DIAGRAM_CANVAS,
     Phase3LayoutFamily.PROCESS_CANVAS, Phase3LayoutFamily.DATA_CANVAS, Phase3LayoutFamily.COMPARISON_TWO_COLUMN,
     Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.ASYMMETRIC_EDITORIAL, Phase3LayoutFamily.QUOTE_OR_STATEMENT, Phase3LayoutFamily.SUMMARY_GRID],
    # Topic 19: Environmental Sustainability
    [Phase3LayoutFamily.HERO_OFFSET, Phase3LayoutFamily.SPLIT_40_60, Phase3LayoutFamily.SYSTEM_ARCHITECTURE,
     Phase3LayoutFamily.TIMELINE_CANVAS, Phase3LayoutFamily.DATA_CANVAS, Phase3LayoutFamily.COMPARISON_MATRIX,
     Phase3LayoutFamily.CARD_CLUSTER, Phase3LayoutFamily.FULL_BLEED_IMAGE_WITH_PANEL, Phase3LayoutFamily.VISUAL_DOMINANT, Phase3LayoutFamily.TEXT_DOMINANT],
]


def build_held_out_slide_data(
    topic_idx: int,
    slide_no: int,
    manifest: CompositionInputManifest,
) -> Tuple[SlideBlueprint, SlideContent, VisualSemanticPacket, VisualRhythmBeat]:
    """
    Builds strongly-typed SlideBlueprint, SlideContent, VisualSemanticPacket,
    and VisualRhythmBeat for slide `slide_no` (1..10) of topic `topic_idx` (0..19).
    """
    topic_info = HELD_OUT_TOPICS[topic_idx]
    topic_title = topic_info["title"]
    domain = topic_info["domain"]
    terms = topic_info["key_terms"]
    fam = _TOPIC_SLIDE_FAMILIES[topic_idx][slide_no - 1]

    slide_id = f"s_{topic_info['id']}_{slide_no}"

    # Rich slide descriptions per slide intent
    if slide_no == 1:
        # Title Slide
        title = topic_title
        subtitle = f"Foundational Principles, Theoretical Frameworks, and Modern Applications in {domain}"
        takeaway = f"A comprehensive academic study of {topic_title.lower()} and its structural implications."
        content = SlideContent(
            title=title,
            subtitle=subtitle,
            primary_takeaway=takeaway,
            speaker_notes=f"Introduce the primary objectives and scope of {topic_title}.",
        )
        packet = VisualSemanticPacket(
            slide_no=slide_no,
            primary_visual_message=f"Hero focal introduction to {topic_title}",
            visual_intent=VisualIntent.HERO_STATEMENT,
            visual_candidates=[VisualCandidate(layout_family=fam)],
        )

    elif slide_no == 2:
        # Conceptual Overview / Motivation
        title = f"{topic_title}: Core Architecture & Motivation"
        subtitle = "Theoretical foundations and fundamental design objectives"
        takeaway = f"The core paradigm of {terms[0]} addresses critical operational bottlenecks in {domain.lower()}."
        bullets = [
            f"Primary motivation centers on governing {terms[0]} under dynamic constraints",
            f"Ensures deterministic guarantees across diverse operational scenarios",
            f"Eliminates pathological worst-case behavior via structured {terms[1]}",
        ]
        content = SlideContent(
            title=title,
            subtitle=subtitle,
            primary_takeaway=takeaway,
            supporting_points=bullets,
            speaker_notes="Clarify why classical unmanaged approaches break down under scale.",
        )
        packet = VisualSemanticPacket(
            slide_no=slide_no,
            primary_visual_message="Conceptual breakdown and systemic trade-offs",
            visual_intent=VisualIntent.TEXTUAL_SYNTHESIS,
            visual_candidates=[VisualCandidate(layout_family=fam)],
        )

    elif slide_no == 3:
        # Architectural / Structural Representation
        title = f"{topic_title}: Structural Anatomy"
        subtitle = f"Decomposition of component relationships and {terms[2]}"
        takeaway = f"Interactions between {terms[0]} and {terms[1]} are mediated by {terms[2]}."
        bullets = [
            f"Subsystem Alpha: Manages state invariants and {terms[0]}",
            f"Subsystem Beta: Directs synchronization with {terms[1]}",
            f"Subsystem Gamma: Validates boundary contracts via {terms[2]}",
        ]
        content = SlideContent(
            title=title,
            subtitle=subtitle,
            primary_takeaway=takeaway,
            supporting_points=bullets,
            speaker_notes="Walk students through the modular separation of responsibilities.",
        )
        packet = VisualSemanticPacket(
            slide_no=slide_no,
            primary_visual_message="Component architecture and directional interaction flows",
            visual_intent=VisualIntent.SHOW_SYSTEM_ARCHITECTURE,
            system_components=[terms[0], terms[1], terms[2]],
            annotation_candidates=[f"{terms[0]} boundary", f"{terms[1]} channel"],
            diagram_candidate=f"{topic_title}StructureDiagram",
            visual_candidates=[VisualCandidate(layout_family=fam)],
        )

    elif slide_no == 4:
        # Sequential Dynamics / Process Flow / Timeline
        title = f"{topic_title}: Operational Lifecycle"
        subtitle = f"Sequential execution phases governed by {terms[1]}"
        takeaway = "Transitions occur monotonically through four deterministic milestone stages."
        steps = [
            f"Phase 1 — Initialization & State Acquisition ({terms[0]})",
            f"Phase 2 — Active Processing & Validation ({terms[1]})",
            f"Phase 3 — Convergence & Synchronization ({terms[2]})",
            f"Phase 4 — State Finalization & Resource Release ({terms[3]})",
        ]
        content = SlideContent(
            title=title,
            subtitle=subtitle,
            primary_takeaway=takeaway,
            process_steps=steps,
            speaker_notes="Emphasize that each phase requires strict invariant verification before transition.",
        )
        packet = VisualSemanticPacket(
            slide_no=slide_no,
            primary_visual_message="Temporal or process execution sequence",
            visual_intent=VisualIntent.SHOW_PROCESS if "process" in fam.value else VisualIntent.SHOW_TIMELINE,
            process_nodes=["Init", "Process", "Sync", "Finalize"],
            temporal_structure=["Phase 1", "Phase 2", "Phase 3", "Phase 4"],
            visual_candidates=[VisualCandidate(layout_family=fam)],
        )

    elif slide_no == 5:
        # Quantitative / Analytical / Formula Modeling
        title = f"{topic_title}: Formal Formulation & Dynamics"
        subtitle = f"Mathematical modeling and empirical properties of {terms[3]}"
        takeaway = "Mathematical bounds govern asymptotic convergence and dynamic stability."
        content = SlideContent(
            title=title,
            subtitle=subtitle,
            primary_takeaway=takeaway,
            formula=r"\Phi(x) = \sum_{k=1}^{N} \alpha_k \cdot \Psi(k, x)",
            formula_symbol_meanings="Phi: cumulative state potential, alpha: weight coefficient, Psi: basis response function",
            data_points=[
                DataPoint(label="Baseline Efficiency", value="84.2", unit="%"),
                DataPoint(label="Optimized Capacity", value="97.6", unit="%"),
                DataPoint(label="Asymptotic Latency", value="12.4", unit="ms"),
            ],
            speaker_notes="Highlight how empirical data validates the theoretical closed-form solution.",
        )
        packet = VisualSemanticPacket(
            slide_no=slide_no,
            primary_visual_message="Quantitative formulation and trend response",
            visual_intent=VisualIntent.SHOW_FORMULA if "formula" in fam.value else VisualIntent.SHOW_DATA_PATTERN,
            formula_or_equation=r"\Phi(x) = \sum_{k=1}^{N} \alpha_k \cdot \Psi(k, x)" if "formula" in fam.value else None,
            chart_candidate=f"{topic_title}PerformanceChart" if "data" in fam.value else None,
            visual_candidates=[VisualCandidate(layout_family=fam)],
        )

    elif slide_no == 6:
        # Comparison / Tradeoff Analysis
        title = f"{topic_title}: Comparative Trade-Off Analysis"
        subtitle = f"Contrasting classical strategies against {terms[4]} approaches"
        takeaway = "Selection depends on balancing throughput optimization against strict safety guarantees."
        rows = [
            ComparisonRow(dimension="Complexity", target_a_value="O(N) linear", target_b_value="O(log N) logarithmic"),
            ComparisonRow(dimension="Overhead", target_a_value="Minimal memory footprint", target_b_value="Moderate state cache required"),
            ComparisonRow(dimension="Fault Tolerance", target_a_value="Requires manual checkpointing", target_b_value="Self-healing recovery protocol"),
            ComparisonRow(dimension="Scalability", target_a_value="Limited to single-node scale", target_b_value="Horizontally partitioned clusters"),
        ]
        content = SlideContent(
            title=title,
            subtitle=subtitle,
            primary_takeaway=takeaway,
            comparison_target_a="Classical Approach",
            comparison_target_b="Modern Architecture",
            comparison_rows=rows,
            speaker_notes="Guide learners on choosing the appropriate strategy based on operational constraints.",
        )
        packet = VisualSemanticPacket(
            slide_no=slide_no,
            primary_visual_message="Pairwise or multi-attribute comparative matrix",
            visual_intent=VisualIntent.COMPARE,
            comparison_targets=["Classical Approach", "Modern Architecture"],
            visual_candidates=[VisualCandidate(layout_family=fam)],
        )

    elif slide_no == 7:
        # Key Principles / Clustered Concepts
        title = f"{topic_title}: Core Design Axioms"
        subtitle = "Four essential operational principles governing robust implementations"
        takeaway = "Sustained reliability requires adherence to all four modular principles."
        bullets = [
            f"Principle of {terms[0]}: Invariants must be validated at every subsystem ingress",
            f"Principle of {terms[1]}: Asynchronous state updates prevent cascaded blocking",
            f"Principle of {terms[2]}: Ephemeral allocations minimize persistent contention",
            f"Principle of {terms[3]}: Graceful degradation preserves essential functionality",
        ]
        content = SlideContent(
            title=title,
            subtitle=subtitle,
            primary_takeaway=takeaway,
            supporting_points=bullets,
            speaker_notes="Review these principles as non-negotiable criteria for systems engineering.",
        )
        packet = VisualSemanticPacket(
            slide_no=slide_no,
            primary_visual_message="Clustered principles and structured categories",
            visual_intent=VisualIntent.VISUAL_SUMMARY,
            key_entities=terms[:4],
            visual_candidates=[VisualCandidate(layout_family=fam)],
        )

    elif slide_no == 8:
        # Deep Dive / Real-World Case Study
        title = f"{topic_title}: Empirical Case Study"
        subtitle = f"Production deployment analysis and observed failure modes under {terms[3]}"
        takeaway = f"Empirical evaluation demonstrates a 3.4x improvement when {terms[2]} is actively tuned."
        bullets = [
            f"Observed peak workload stress during live operational evaluation",
            f"Automated remediation reduced tail latency by 71% under peak contention",
            f"Audit confirmed complete absence of data corruption or invariant violations",
        ]
        content = SlideContent(
            title=title,
            subtitle=subtitle,
            primary_takeaway=takeaway,
            supporting_points=bullets,
            speaker_notes="Discuss the real-world operational challenges encountered during scale deployment.",
        )
        packet = VisualSemanticPacket(
            slide_no=slide_no,
            primary_visual_message="Asymmetric editorial visual or panel deep dive",
            visual_intent=VisualIntent.TEXTUAL_SYNTHESIS,
            image_candidate_concepts=[f"{topic_title} Production Infrastructure"],
            visual_candidates=[VisualCandidate(layout_family=fam)],
        )

    elif slide_no == 9:
        # Notable Axiom / Conclusion / Hero Statement
        title = f"{topic_title}: Foundational Insight"
        subtitle = "The central thesis of modern academic inquiry"
        takeaway = f"Mastery of {topic_title.lower()} lies not in eliminating complexity, but in isolating it."
        content = SlideContent(
            title=title,
            subtitle=subtitle,
            primary_takeaway=takeaway,
            callout=f"Fundamental Law: Systems that explicitly manage {terms[0]} achieve provable resilience across all operating conditions.",
            speaker_notes="Leave learners with this foundational conceptual synthesis.",
        )
        packet = VisualSemanticPacket(
            slide_no=slide_no,
            primary_visual_message="High-impact hero statement and memorable conclusion",
            visual_intent=VisualIntent.HERO_STATEMENT,
            visual_candidates=[VisualCandidate(layout_family=fam)],
        )

    else:
        # Slide 10: Synthesis & Summary
        title = f"{topic_title}: Summary & Citations"
        subtitle = "Key takeaways, curriculum alignment, and primary scholarly literature"
        takeaway = f"Core conclusions confirm the primacy of {terms[0]} and {terms[1]} in {domain}."
        bullets = [
            f"1. Theoretical foundation: Rigid bounds on {terms[0]} ensure deterministic stability",
            f"2. Methodological rigor: Empirical modeling validates closed-form analytical predictions",
            f"3. Practical application: Robust implementations require continuous contract validation",
            f"Source Citation: Cambridge University Press, Advanced Studies in {domain} (2024)",
        ]
        content = SlideContent(
            title=title,
            subtitle=subtitle,
            primary_takeaway=takeaway,
            supporting_points=bullets,
            speaker_notes="Review the learning checklist and point students to primary literature.",
        )
        packet = VisualSemanticPacket(
            slide_no=slide_no,
            primary_visual_message="Curriculum synthesis and scholarly reference grid",
            visual_intent=VisualIntent.VISUAL_SUMMARY,
            visual_candidates=[VisualCandidate(layout_family=fam)],
        )

    bp = SlideBlueprint(
        slide_id=slide_id,
        slide_number=slide_no,
        intent=SlideIntent.CONCEPT_EXPLANATION,
        primary_message=content.primary_takeaway,
        content_density=ContentDensity.MEDIUM,
        layout_family=LayoutFamily.CENTERED_FOCAL,
    )

    beat = VisualRhythmBeat(
        slide_no=slide_no,
        layout_family=fam,
        visual_weight=VisualWeight.MEDIUM,
    )

    # Register content into manifest
    manifest.register_content(slide_id, content.model_dump())
    manifest.register_content(f"vis_{slide_id}", packet.model_dump())
    if content.speaker_notes:
        manifest.register_content(f"notes_{slide_id}", {"speaker_notes": content.speaker_notes})

    return bp, content, packet, beat


def compile_held_out_deck(
    topic_idx: int,
    design_dna: Optional[DesignDNA] = None,
) -> Tuple[List[ComposedSlideContext], CompositionInputManifest, Dict[int, LayoutAuditResult], Dict[int, RepairResult]]:
    """
    Compiles a full 10-slide held-out deck through the complete Phase 3.2 pipeline:
      compile_slide_layout -> audit_layout -> repair_layout_defects -> ComposedSlideContext
    """
    topic_info = HELD_OUT_TOPICS[topic_idx]
    if design_dna is None:
        theme = topic_info["theme"]
        palette = _THEME_PALETTES.get(theme, _THEME_PALETTES["blue_professional"])
        design_dna = _build_academic_clean_dna(palette, ContentDensity.MEDIUM)

    manifest = CompositionInputManifest(manifest_id=f"manifest_{topic_info['id']}")
    composed_contexts: List[ComposedSlideContext] = []
    repair_results: Dict[int, RepairResult] = {}
    audit_results_dict: Dict[int, LayoutAuditResult] = {}

    for s_no in range(1, 11):
        bp, content, packet, beat = build_held_out_slide_data(topic_idx, s_no, manifest)

        # 1. Compile layout plan
        plan = compile_slide_layout(
            slide_blueprint=bp,
            slide_content=content,
            visual_semantic_packet=packet,
            design_dna=design_dna,
            rhythm_beat=beat,
            composition_input_manifest=manifest,
        )

        # 2. Quality audit
        audit = audit_layout(plan, design_dna=design_dna)
        audit_results_dict[s_no] = audit

        # 3. Targeted repair
        repair = repair_layout_defects(plan, audit, design_dna=design_dna)
        repaired_plan = repair.repaired_plan
        repair_results[s_no] = repair

        # 4. Wrap context
        ctx = ComposedSlideContext(
            slide_no=s_no,
            composition_plan=repaired_plan,
            composition_input_manifest_id=manifest.manifest_id,
            slide_content_id=bp.slide_id,
        )
        composed_contexts.append(ctx)

    return composed_contexts, manifest, audit_results_dict, repair_results
