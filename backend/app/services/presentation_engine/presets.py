"""
LearnByGenie Presentation Design Engine — Presets
================================================
Presentation personality presets that control prompt engineering,
section templates, slide purpose allocation, and visual strategy.
"""
from typing import List, Dict
from . import PresetType, SlidePurpose


PRESET_CONFIGS: Dict[str, dict] = {

    "academic": {
        "label": "Academic / Lecture",
        "description": "University-grade lecture with clear learning progression, concepts, examples, and assessment readiness.",
        "icon": "",
        "default_slide_flow": [
            SlidePurpose.COVER,
            SlidePurpose.CONCEPT,         # Learning objectives
            SlidePurpose.CONCEPT,         # Core concept 1
            SlidePurpose.TWO_COLUMN,      # Deeper explanation
            SlidePurpose.IMAGE_INSIGHT,   # Visual demonstration
            SlidePurpose.CONCEPT,         # Core concept 2
            SlidePurpose.COMPARISON,      # Compare approaches
            SlidePurpose.CASE_STUDY,      # Real-world example
            SlidePurpose.PROCESS_FLOW,    # Methodology/workflow
            SlidePurpose.QUOTE_INSIGHT,   # Key insight
            SlidePurpose.SUMMARY,         # Key takeaways
            SlidePurpose.CLOSING,
        ],
        "prompt_personality": (
            "You are a world-class professor at a top university preparing a lecture. "
            "Your content should be pedagogically structured with clear learning objectives, "
            "concrete examples, and progressive depth. Use the Socratic method when appropriate. "
            "Include real academic references and verifiable facts."
        ),
        "title_style": "Descriptive and concept-oriented",
        "preferred_themes": ["blue_professional", "emerald_academic", "indigo_innovation"],
    },

    "pitch": {
        "label": "Business / Pitch",
        "description": "Startup pitch or business strategy deck with data-driven insights, KPIs, and compelling narrative.",
        "icon": "",
        "default_slide_flow": [
            SlidePurpose.COVER,
            SlidePurpose.CONCEPT,         # Problem statement
            SlidePurpose.IMAGE_INSIGHT,   # Market opportunity
            SlidePurpose.CONCEPT,         # Solution
            SlidePurpose.KPI_METRICS,     # Key metrics
            SlidePurpose.ARCHITECTURE,    # Product/system overview
            SlidePurpose.COMPARISON,      # Competitive landscape
            SlidePurpose.TIMELINE,        # Roadmap
            SlidePurpose.CASE_STUDY,      # Traction/case study
            SlidePurpose.QUOTE_INSIGHT,   # Vision statement
            SlidePurpose.SUMMARY,         # Ask / next steps
            SlidePurpose.CLOSING,
        ],
        "prompt_personality": (
            "You are a top-tier management consultant creating a compelling business presentation. "
            "Focus on data-driven insights, market analysis, competitive positioning, and actionable recommendations. "
            "Use concrete metrics and real company examples. Every slide should drive toward the strategic conclusion."
        ),
        "title_style": "Insight-oriented and action-driven",
        "preferred_themes": ["orange_energy", "blue_professional", "teal_corporate"],
    },

    "technical": {
        "label": "Technical / Architecture",
        "description": "System architecture, technical deep-dive, or engineering documentation with diagrams and process flows.",
        "icon": "",
        "default_slide_flow": [
            SlidePurpose.COVER,
            SlidePurpose.CONCEPT,         # Overview / context
            SlidePurpose.ARCHITECTURE,    # System architecture
            SlidePurpose.PROCESS_FLOW,    # Workflow / pipeline
            SlidePurpose.TWO_COLUMN,      # Technical detail
            SlidePurpose.CONCEPT,         # Core mechanism
            SlidePurpose.COMPARISON,      # Technology comparison
            SlidePurpose.IMAGE_INSIGHT,   # Visual explanation
            SlidePurpose.KPI_METRICS,     # Performance metrics
            SlidePurpose.CASE_STUDY,      # Implementation example
            SlidePurpose.SUMMARY,         # Key decisions
            SlidePurpose.CLOSING,
        ],
        "prompt_personality": (
            "You are a senior system architect explaining a technical system. "
            "Prioritize clarity, precision, and technical accuracy. Use proper technical terminology. "
            "Include architecture layers, data flows, and performance considerations. "
            "Diagrams should show clear component relationships."
        ),
        "title_style": "Technical and precise",
        "preferred_themes": ["blue_professional", "indigo_innovation", "minimal_charcoal"],
    },

    "research": {
        "label": "Research / Analysis",
        "description": "Research findings, data analysis, or academic paper presentation with evidence and methodology.",
        "icon": "",
        "default_slide_flow": [
            SlidePurpose.COVER,
            SlidePurpose.CONCEPT,         # Research question
            SlidePurpose.TWO_COLUMN,      # Background / lit review
            SlidePurpose.PROCESS_FLOW,    # Methodology
            SlidePurpose.KPI_METRICS,     # Key findings
            SlidePurpose.IMAGE_INSIGHT,   # Data visualization
            SlidePurpose.COMPARISON,      # Result comparison
            SlidePurpose.CONCEPT,         # Discussion
            SlidePurpose.QUOTE_INSIGHT,   # Implication
            SlidePurpose.SUMMARY,         # Conclusion
            SlidePurpose.CLOSING,
        ],
        "prompt_personality": (
            "You are a published researcher presenting findings to an academic audience. "
            "Structure content around hypothesis, methodology, evidence, and conclusions. "
            "Use precise language and cite specific findings with data."
        ),
        "title_style": "Evidence-oriented and descriptive",
        "preferred_themes": ["emerald_academic", "blue_professional", "minimal_charcoal"],
    },

    "teaching": {
        "label": "Teaching / Lesson",
        "description": "Classroom teaching with Bloom's taxonomy alignment, scaffolded learning, and interactive elements.",
        "icon": "",
        "default_slide_flow": [
            SlidePurpose.COVER,
            SlidePurpose.CONCEPT,         # Learning objectives (Bloom's)
            SlidePurpose.IMAGE_INSIGHT,   # Hook / engagement
            SlidePurpose.CONCEPT,         # Core concept (Remember/Understand)
            SlidePurpose.TWO_COLUMN,      # Explanation (Apply)
            SlidePurpose.PROCESS_FLOW,    # Step-by-step method
            SlidePurpose.CASE_STUDY,      # Worked example (Analyze)
            SlidePurpose.COMPARISON,      # Compare concepts (Evaluate)
            SlidePurpose.QUOTE_INSIGHT,   # Key principle
            SlidePurpose.SUMMARY,         # Assessment / review
            SlidePurpose.CLOSING,
        ],
        "prompt_personality": (
            "You are an award-winning teacher creating an engaging lesson. "
            "Use scaffolded learning: start simple, build complexity. "
            "Include vivid analogies, relatable examples, and check-for-understanding moments. "
            "Align with Bloom's taxonomy where possible."
        ),
        "title_style": "Question or concept-oriented, engaging",
        "preferred_themes": ["blue_professional", "emerald_academic", "orange_energy"],
    },
}


def get_preset(preset_type: str) -> dict:
    """Get preset config, falling back to academic."""
    return PRESET_CONFIGS.get(preset_type, PRESET_CONFIGS["academic"])


def get_slide_flow(preset_type: str, depth: str) -> List[SlidePurpose]:
    """Get the slide flow for a preset, adjusted for depth."""
    preset = get_preset(preset_type)
    flow = list(preset["default_slide_flow"])

    if depth == "quick":
        # Remove some middle slides to shorten
        # Keep: cover, first 2-3 content, summary, closing
        if len(flow) > 8:
            # Keep cover + 5 content + summary + closing
            core = flow[1:-2]   # middle content
            keep_count = min(5, len(core))
            # Pick evenly spaced slides for variety
            step = max(1, len(core) // keep_count)
            selected = [core[i * step] for i in range(keep_count) if i * step < len(core)]
            flow = [flow[0]] + selected + flow[-2:]

    return flow
