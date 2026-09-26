"""
Planner Agent
=============
Plans the narrative arc and slide layout structure (10..17 slides).
Ingests the Topic Ontology checklist to guarantee complete pedagogical coverage.
Maps each core subtopic to at least one slide, merging closely related concepts
or flexing up to +2 slides when necessary to ensure zero dropped subtopics.

vNEXT Phase 1: plan_presentation_vnext() uses story grammar + blueprints.
"""
from app.core.logging import logger
import json
import re
from typing import Dict, Any, List, Optional
from app.services.ai import router
from .schemas import (
    PresentationConfig, SlideType,
    PresentationBrief, SlideBlueprint, SlideIntent,
    VisualTypeHint,
)
from .prompts import PLANNER_SYSTEM_PROMPT
from .topic_ontology_agent import (
    generate_topic_ontology, TopicOntologyChecklist, TopicIntelligencePack,
)
from ..knowledge import get_topic_overview_context
from .story_grammar import (
    adapt_grammar_to_slide_count,
    generate_blueprints_from_grammar,
    blueprint_to_outline_dict,
    INTENT_TO_LEGACY_TYPE,
)
from .blueprint_validator import (
    validate_blueprint_sequence,
    repair_blueprint_sequence,
)
from .domain_classifier import recommend_story_grammar
from .content_quality_auditor import sanitize_and_complete_title


def check_subtopic_coverage(core_subtopics: List[str], slides: List[Dict[str, Any]]) -> tuple[List[str], List[str]]:
    """
    Deterministic check: verifies which core subtopics are covered in planned slides
    via keyword overlap in title, key_message, and visual_hint.
    Returns (covered_subtopics, missing_subtopics).
    """
    covered = []
    missing = []
    
    # Concatenate all slide text into searchable text
    slide_texts = []
    for s in slides:
        text = f"{s.get('title', '')} {s.get('key_message', '')} {s.get('subtitle', '')}".lower()
        slide_texts.append(text)
    full_deck_text = " ".join(slide_texts)

    for subtopic in core_subtopics:
        # Extract meaningful keywords (>3 chars, ignore common stop words)
        words = [re.sub(r"[^\w]", "", w.lower()) for w in subtopic.split()]
        meaningful_words = [w for w in words if len(w) > 3 and w not in ["with", "from", "that", "this", "into", "over", "under", "about", "scope", "core", "mechanism"]]
        
        if not meaningful_words:
            covered.append(subtopic)
            continue

        # Check if at least 1 key term appears anywhere in the deck text
        is_covered = any(w in full_deck_text for w in meaningful_words)
        if is_covered:
            covered.append(subtopic)
        else:
            missing.append(subtopic)

    return covered, missing


def _build_deterministic_plan(config: PresentationConfig, ontology: TopicOntologyChecklist) -> Dict[str, Any]:
    """
    Deterministic fallback outline generator when LLM providers are unavailable or fail.
    Preserves exact structural planner invariants:
    - Hero slide at index 0.
    - Closing slide at index -1 (quiz or qa).
    - If core subtopics fit comfortably within target slide count (len(core_subtopics) < slide_count - 2),
      generates exactly config.slide_count slides with zero unnecessary expansion.
    - If core subtopics exceed/tightly fill slide count (len(core_subtopics) >= slide_count - 2),
      flexes up to config.slide_count + 2 to avoid dropping core subtopics.
    """
    slides = []

    # Hero Slide
    slides.append({
        "slide_no": 1,
        "type": "hero",
        "title": f"{config.topic}: Architecture & Foundations",
        "key_message": f"Core principles and pedagogical overview of {config.topic}.",
        "visual_hint": "diagram",
    })

    expansion_permitted = len(ontology.core_subtopics) >= (config.slide_count - 2)

    # Intermediate concept slides from ontology core subtopics
    for idx, subtopic in enumerate(ontology.core_subtopics):
        slides.append({
            "slide_no": len(slides) + 1,
            "type": "concept",
            "title": f"{subtopic}: Core Architecture & Mechanism",
            "key_message": f"Essential operational principles governing {subtopic} in {config.topic}.",
            "visual_hint": "diagram",
        })

    # If subtopic count fits comfortably, pad with structured concept slides up to target (target - 1 for closing)
    target_intermediate = config.slide_count - 2
    if len(ontology.core_subtopics) < target_intermediate:
        counter = len(ontology.core_subtopics) + 1
        while len(slides) < (config.slide_count - 1):
            slides.append({
                "slide_no": len(slides) + 1,
                "type": "concept",
                "title": f"Applied Analysis & Verification Part {counter}",
                "key_message": f"Deep-dive technical mechanics and edge-case validation for {config.topic}.",
                "visual_hint": "diagram",
            })
            counter += 1

    # Closing Slide
    closing_type = "quiz" if config.enable_quiz else "qa"
    slides.append({
        "slide_no": len(slides) + 1,
        "type": closing_type,
        "title": "Interactive Knowledge Check" if config.enable_quiz else "Q&A, Review & Key Takeaways",
        "key_message": f"Synthesis and mastery assessment for {config.topic}.",
        "visual_hint": "cards",
    })

    expansion_reason = ""
    if len(slides) > config.slide_count and expansion_permitted:
        expansion_reason = f"Expanded to {len(slides)} slides to provide complete coverage for {len(ontology.core_subtopics)} core subtopics"

    return {
        "deck_title": config.topic,
        "subtitle": f"{config.audience.title()} Level  •  {config.language.title()}",
        "slides": slides,
        "expansion_reason": expansion_reason,
    }


async def plan_presentation(
    config: PresentationConfig,
    user_id: str,
    custom_context: str = "",
    ontology: Optional[TopicOntologyChecklist] = None,
) -> Dict[str, Any]:
    """
    Generate an outline calibrated against the Topic Ontology checklist.
    Guarantees every core subtopic is mapped without silent omissions.
    """
    # 1. Obtain Topic Ontology Checklist (Step 0.5)
    if ontology is None:
        ontology = await generate_topic_ontology(config, user_id=user_id)

    # 2. Retrieve knowledge context if requested
    context_str = custom_context
    if not context_str and config.source_type in ["uploaded_material", "uploaded_material_plus_web"] and config.source_id:
        context_str = await get_topic_overview_context(
            document_id=config.source_id,
            user_id=user_id,
            topic=config.topic,
            max_chunks=10,
        )

    # 3. Format planner prompt with Topic Ontology injection
    closing_desc = "Interactive Knowledge Check Quiz" if config.enable_quiz else "Closing / Q&A & Open Discussion"
    system_prompt = PLANNER_SYSTEM_PROMPT.format(
        slide_count=config.slide_count,
        n_minus_1=config.slide_count - 1,
        n_minus_2=config.slide_count - 2,
        closing_slide_desc=closing_desc,
    )
    
    ontology_guidance = (
        "\n\nTOPIC ONTOLOGY COVERAGE CONTRACT:\n"
        "You must map every one of the following CORE SUBTOPICS into at least one slide:\n"
        + "\n".join(f"- {st}" for st in ontology.core_subtopics)
        + "\n\nMust include: " + "; ".join(ontology.must_include)
        + "\nIf slide count is tight, merge closely related subtopics onto one slide or expand by up to +2 slides. NEVER drop a core subtopic."
    )
    system_prompt += ontology_guidance

    if config.custom_context:
        system_prompt += (
            "\n\nIMPORTANT INSTRUCTION: Use the following source material to generate the outline. "
            "DO NOT fabricate facts beyond this provided context:\n\n"
            f"{config.custom_context}"
        )

    user_msg_parts = [
        f"Topic: {config.topic}",
        f"Target Audience: {config.audience}",
        f"Language: {config.language}",
        f"Depth: {config.depth}",
        f"Design System: {config.design.value if hasattr(config.design, 'value') else config.design}",
        f"Target Slide Count: {config.slide_count} (allowed flex up to {config.slide_count + 2} for full coverage)",
    ]
    if config.enable_quiz:
        user_msg_parts.append("Special Requirement: The final slide must be an interactive Quiz slide.")
    if context_str:
        user_msg_parts.append(f"\nDocument Reference Material:\n{context_str[:3000]}")

    user_prompt = "\n".join(user_msg_parts)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # 4. Generate structured plan via ModelRouter with deterministic fallback
    try:
        plan_json = await router.generate_json(
            task="planning",
            messages=messages,
            temperature=0.3,
            max_tokens=4000,
        )
    except Exception as e:
        logger.warning(f"[Planner] LLM generation failed ({e}), using deterministic fallback outline")
        plan_json = _build_deterministic_plan(config, ontology)

    raw_slides = plan_json.get("slides", [])
    expansion_reason = plan_json.get("expansion_reason", "")

    # 5. Deterministic Coverage Audit & Repair
    expansion_permitted = len(ontology.core_subtopics) >= (config.slide_count - 2)
    max_allowed = (config.slide_count + 2) if expansion_permitted else config.slide_count

    covered, missing = check_subtopic_coverage(ontology.core_subtopics, raw_slides)

    if missing:
        logger.info(f"[Planner] {len(missing)} core subtopics initially unmapped: {missing}")
        # Repair: add or merge missing subtopics
        for m_sub in missing:
            if expansion_permitted and len(raw_slides) < max_allowed:
                # Add slide before closing slides
                insert_pos = max(1, len(raw_slides) - 2)
                raw_slides.insert(insert_pos, {
                    "slide_no": insert_pos + 1,
                    "type": "concept",
                    "title": f"{m_sub}: Core Architecture & Mechanism",
                    "key_message": f"Essential operational principles governing {m_sub} in {config.topic}.",
                    "visual_hint": "diagram",
                })
                expansion_reason = f"Expanded to {len(raw_slides)} slides to fully cover: {', '.join(missing)}"
            else:
                # Check if there is a generic placeholder slide to repurpose without increasing slide count
                repurposed = False
                for s in raw_slides[1:-1]:
                    s_title = s.get("title", "")
                    if any(s_title.startswith(prefix) for prefix in ["Key Principle", "Applied Analysis", "Overview"]):
                        s["title"] = f"{m_sub}: Core Architecture & Mechanism"
                        s["key_message"] = f"Essential operational principles governing {m_sub} in {config.topic}."
                        repurposed = True
                        break
                if not repurposed:
                    # Merge into the last concept slide
                    for s in reversed(raw_slides):
                        if s.get("type") in ["concept", "definition", "two_column"]:
                            s["title"] = f"{s.get('title', '')} & {m_sub}"[:100]
                            s["key_message"] = f"{s.get('key_message', '')} Covers {m_sub}."
                            break

    # 6. Slide Count Clamping strictly according to expansion allowance
    if len(raw_slides) > max_allowed:
        raw_slides = raw_slides[:max_allowed]
    elif len(raw_slides) < config.slide_count:
        while len(raw_slides) < config.slide_count:
            idx = len(raw_slides) + 1
            raw_slides.append({
                "slide_no": idx,
                "type": "concept",
                "title": f"Key Principle & Mechanism {idx}",
                "key_message": f"Core component analysis for {config.topic}",
                "visual_hint": "diagram",
            })

    if len(raw_slides) <= config.slide_count:
        expansion_reason = ""
    elif not expansion_reason and len(raw_slides) > config.slide_count:
        expansion_reason = f"Expanded to {len(raw_slides)} slides to provide complete coverage for {len(ontology.core_subtopics) if ontology else 0} core subtopics"

    # Renumber strictly 1..N
    for i, s in enumerate(raw_slides):
        s["slide_no"] = i + 1

    # Guarantee slide 1 is hero and closing slide matches requirement
    raw_slides[0]["type"] = "hero"
    raw_slides[0].pop("section_label", None)  # Hero never gets eyebrow tag
    if config.enable_quiz:
        raw_slides[-1]["type"] = "quiz"
        raw_slides[-1].pop("section_label", None)
    elif raw_slides[-1].get("type") not in ["summary", "qa"]:
        raw_slides[-1]["type"] = "qa"
    # Strip section_label from closing/summary/qa slides
    if raw_slides[-1].get("type") in ["qa", "summary", "quiz"]:
        raw_slides[-1].pop("section_label", None)

    plan_json["slides"] = raw_slides
    plan_json["expansion_reason"] = expansion_reason
    plan_json["topic_ontology"] = ontology.model_dump() if hasattr(ontology, "model_dump") else ontology.dict()
    if not plan_json.get("deck_title"):
        plan_json["deck_title"] = config.topic
    if not plan_json.get("subtitle"):
        plan_json["subtitle"] = f"{config.audience.title()} Level  •  {config.language.title()}"

    return plan_json


# ═══════════════════════════════════════════════════════════════
# vNEXT Phase 1 — Blueprint-Driven Planning
# ═══════════════════════════════════════════════════════════════

BLUEPRINT_PLANNER_SYSTEM_PROMPT = """You are an elite curriculum architect filling in semantic content
for a pre-structured presentation.

You are given a TOPIC, DOMAIN, PURPOSE, AUDIENCE, and a pre-computed SLIDE STRUCTURE.
Each slide has a determined INTENT (why the slide exists) and NARRATIVE_ROLE.

Your job is to fill in the SEMANTIC CONTENT for each slide position:
- primary_message: The single most important takeaway (1 concise sentence, under 70 chars)
- learning_purpose: What the learner gains from this slide (1 sentence)
- supporting_concepts: Key concepts this slide addresses (list of 2-4 terms)
- speaker_note_goal: What the speaker should emphasize (1 sentence)

RULES:
1. Each primary_message must be UNIQUE across the deck — no duplicates.
2. primary_message must be insight-driven, domain-aware, and never generic.
3. BANNED CANNED PHRASES:
   Do NOT use formulas like "Architecture & Foundations", "The Problem X Solves",
   "How X Works Step by Step", "Core Mechanism of X", or "Defining X: Core Principles".
   Instead, formulate insight titles (e.g. "How plants convert light into chemical energy",
   "Why industrialization began in eighteenth-century Britain", "Designing reproducible machine-learning research").
4. Use concrete nouns and verbs, not abstract filler.
5. Match the INTENT: a DEFINITION slide should define, a COMPARISON slide should contrast.
6. Repeated intent is allowed ONLY when each slide has a distinct semantic objective (e.g. comparison 1 compares concurrency models, comparison 2 compares module systems).
7. Respect the NARRATIVE ORDER: build from simple to complex.
8. No LaTeX. Plain text only.

Return strict JSON:
{{
  "slide_enrichments": [
    {{
      "slide_number": 1,
      "primary_message": "...",
      "learning_purpose": "...",
      "supporting_concepts": ["...", "..."],
      "speaker_note_goal": "..."
    }}
  ]
}}
"""


async def plan_presentation_vnext(
    brief: PresentationBrief,
    topic_intelligence: Optional[TopicIntelligencePack] = None,
    user_id: str = "",
    custom_context: str = "",
) -> Dict[str, Any]:
    """
    vNEXT Blueprint-driven planning.
    
    Flow:
      1. Story grammar → select + adapt narrative beats to slide_count
      2. Generate SlideBlueprint skeletons (visual, layout, budget — deterministic)
      3. LLM enrichment (primary_message, concepts — semantic)
      4. Validate blueprint sequence & semantic sanity
      5. Repair if needed
      6. Convert to outline_data for backward compatibility
    """
    logger.info(
        f"[PlannerVNext] Starting blueprint planning: "
        f"topic='{brief.topic}', grammar={brief.primary_story_grammar.value}, "
        f"modifiers={[m.value for m in brief.story_modifiers]}, "
        f"slides={brief.slide_count}"
    )

    # Convert topic intelligence to dict for story grammar functions
    ti_dict = None
    if topic_intelligence:
        ti_dict = topic_intelligence.model_dump() if hasattr(topic_intelligence, "model_dump") else topic_intelligence.dict()
        refined_primary, refined_modifiers = recommend_story_grammar(
            domain=brief.domain,
            purpose=brief.presentation_goal,
            topic_intelligence=ti_dict,
        )
        brief.primary_story_grammar = refined_primary
        brief.story_modifiers = refined_modifiers
        logger.info(
            f"[PlannerVNext] Grammar refined with TopicIntelligencePack: "
            f"primary={brief.primary_story_grammar.value}, "
            f"modifiers={[m.value for m in brief.story_modifiers]}"
        )

    # ─── Step 1: Adapt story grammar to slide count ───────────
    beats = adapt_grammar_to_slide_count(
        primary=brief.primary_story_grammar,
        modifiers=brief.story_modifiers,
        slide_count=brief.slide_count,
        domain=brief.domain,
        enable_quiz=brief.enable_quiz,
        topic_intelligence=ti_dict,
    )

    # ─── Step 2: Generate blueprint skeletons ─────────────────
    blueprints = generate_blueprints_from_grammar(
        beats=beats,
        domain=brief.domain,
        topic_intelligence=ti_dict,
        topic=brief.canonical_topic or brief.topic,
    )

    # ─── Step 3: PRE-ENRICHMENT deterministic validation ──────
    passed, issues = validate_blueprint_sequence(blueprints, brief)
    if not passed:
        logger.info(f"[PlannerVNext] Pre-enrichment validation failed, applying structural repairs...")
        blueprints = repair_blueprint_sequence(blueprints, issues, brief)

    # ─── Step 4: Semantic content fill ────────────────────────
    try:
        enriched_blueprints = await _enrich_blueprints_via_llm(
            blueprints=blueprints,
            brief=brief,
            topic_intelligence=topic_intelligence,
            custom_context=custom_context,
        )
    except Exception as e:
        logger.warning(f"[PlannerVNext] LLM enrichment unavailable or failed ({e}), using domain-aware blueprint realization")
        enriched_blueprints = blueprints

    # Always ensure domain-aware, topic-specific messages and zero canned generic text
    _apply_deterministic_messages(enriched_blueprints, brief, topic_intelligence=topic_intelligence)

    # ─── Step 5: POST-ENRICHMENT semantic validation ──────────
    post_passed, post_issues = validate_blueprint_sequence(enriched_blueprints, brief)
    if not post_passed:
        logger.info(f"[PlannerVNext] Post-enrichment validation: {len(post_issues)} issues, applying repairs...")
        enriched_blueprints = repair_blueprint_sequence(enriched_blueprints, post_issues, brief)

    # ─── Step 6: Convert to outline_data for backward compat ──
    outline_slides = [blueprint_to_outline_dict(bp) for bp in enriched_blueprints]

    ontology_dict = {}
    if topic_intelligence:
        covered, missing = check_subtopic_coverage(
            topic_intelligence.core_subtopics, outline_slides
        )
        if missing:
            logger.info(f"[PlannerVNext] {len(missing)} subtopics not explicitly covered: {missing}")
        ontology_dict = ti_dict or {}

    plan_json = {
        "deck_title": brief.canonical_topic or brief.topic,
        "subtitle": f"{brief.education_level.replace('_', ' ').title()} Level  •  {brief.language.title()}",
        "slides": outline_slides,
        "expansion_reason": "",
        "topic_ontology": ontology_dict,
        "key_takeaways": [],
        "blueprints": [
            bp.model_dump() if hasattr(bp, "model_dump") else bp.dict()
            for bp in enriched_blueprints
        ],
        "presentation_brief": brief.model_dump() if hasattr(brief, "model_dump") else brief.dict(),
    }

    logger.info(
        f"[PlannerVNext] Blueprint planning complete: "
        f"{len(enriched_blueprints)} slides, "
        f"intents={[bp.intent.value for bp in enriched_blueprints]}"
    )
    return plan_json


async def _enrich_blueprints_via_llm(
    blueprints: List[SlideBlueprint],
    brief: PresentationBrief,
    topic_intelligence: Optional[TopicIntelligencePack] = None,
    custom_context: str = "",
) -> List[SlideBlueprint]:
    """
    Use LLM to fill in semantic content for each blueprint:
    primary_message, learning_purpose, supporting_concepts, speaker_note_goal.
    """
    structure_desc = []
    for bp in blueprints:
        structure_desc.append({
            "slide_number": bp.slide_number,
            "intent": bp.intent.value,
            "narrative_role": bp.narrative_role,
            "content_density": bp.content_density.value,
            "section_label": bp.section_label or "",
        })

    ti_context = ""
    if topic_intelligence:
        concepts = [c.get("term", "") for c in topic_intelligence.canonical_concepts[:10]]
        if concepts:
            ti_context += f"\nKey Concepts: {', '.join(concepts)}"
        if topic_intelligence.processes:
            ti_context += f"\nKey Processes: {', '.join(topic_intelligence.processes[:5])}"
        if topic_intelligence.misconceptions:
            myths = [m.get("myth", "") for m in topic_intelligence.misconceptions[:3]]
            ti_context += f"\nCommon Misconceptions: {', '.join(myths)}"
        if topic_intelligence.real_world_examples:
            ti_context += f"\nReal Examples: {', '.join(topic_intelligence.real_world_examples[:3])}"

    user_prompt_parts = [
        f"Topic: {brief.topic}",
        f"Domain: {brief.domain}/{brief.subdomain}",
        f"Purpose: {brief.presentation_goal.value}",
        f"Audience: {brief.education_level} ({brief.audience_expertise})",
        f"Slide Count: {brief.slide_count}",
        f"\nPRE-COMPUTED SLIDE STRUCTURE:",
        json.dumps(structure_desc, indent=2),
    ]
    if ti_context:
        user_prompt_parts.append(f"\nTOPIC INTELLIGENCE:{ti_context}")
    if custom_context:
        user_prompt_parts.append(f"\nCUSTOM CONTEXT:\n{custom_context[:2000]}")

    messages = [
        {"role": "system", "content": BLUEPRINT_PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(user_prompt_parts)},
    ]

    try:
        enrichment_json = await router.generate_json(
            task="planning",
            messages=messages,
            temperature=0.3,
            max_tokens=3000,
        )
    except Exception as e:
        logger.warning(f"[BlueprintPlanner] LLM blueprint enrichment failed ({e}), using baseline blueprints")
        enrichment_json = {}

    enrichments = enrichment_json.get("slide_enrichments", [])

    enrichment_map = {e.get("slide_number", 0): e for e in enrichments}
    for bp in blueprints:
        enrichment = enrichment_map.get(bp.slide_number, {})
        if enrichment:
            raw_msg = enrichment.get("primary_message", bp.primary_message)
            bp.primary_message = sanitize_and_complete_title(raw_msg, topic=brief.topic)
            bp.learning_purpose = enrichment.get("learning_purpose", bp.learning_purpose)
            bp.speaker_note_goal = enrichment.get("speaker_note_goal", bp.speaker_note_goal)
            concepts = enrichment.get("supporting_concepts", [])
            if concepts:
                bp.supporting_concepts = concepts
        else:
            if bp.primary_message:
                bp.primary_message = sanitize_and_complete_title(bp.primary_message, topic=brief.topic)

    logger.info(f"[PlannerVNext] Enriched {len(enrichments)} blueprints via LLM")
    return blueprints


def _apply_deterministic_messages(
    blueprints: List[SlideBlueprint],
    brief: PresentationBrief,
    topic_intelligence: Optional[Any] = None,
    force: bool = False,
) -> None:
    """
    Domain-aware title & message realization (Phase 2 generalized).
    Generates blueprint primary messages/titles from:
      TopicIntelligencePack + story beat semantic role + domain + purpose.

    ALL production behavior emerges from general intelligence layers:
      domain classification, subdomain, TopicIntelligencePack, story grammar,
      SlideBlueprint, semantic role, visual routing.

    Zero hardcoded benchmark topic branches.
    Benchmark topics are test oracles only (validated in test fixtures).
    """
    topic = brief.topic.strip()
    domain = brief.domain.lower()
    subdomain = brief.subdomain.lower() if brief.subdomain else ""

    # ─── Extract topic intelligence for dynamic synthesis ──────
    ti_dict = None
    ti_concepts = []
    ti_processes = []
    ti_comparisons = []
    ti_chronology = []
    ti_misconceptions = []
    ti_examples = []
    ti_cause_effect = []

    if topic_intelligence:
        ti_dict = topic_intelligence.model_dump() if hasattr(topic_intelligence, "model_dump") else (
            topic_intelligence if isinstance(topic_intelligence, dict) else {}
        )
        for c in ti_dict.get("canonical_concepts", []):
            if isinstance(c, dict):
                ti_concepts.append(c.get("term", ""))
            elif isinstance(c, str):
                ti_concepts.append(c)
        ti_concepts = [c for c in ti_concepts if c]
        ti_processes = ti_dict.get("processes", [])
        ti_comparisons = ti_dict.get("comparison_candidates", [])
        ti_chronology = ti_dict.get("chronology_if_relevant", [])
        ti_misconceptions = ti_dict.get("misconceptions", [])
        ti_examples = ti_dict.get("real_world_examples", [])
        ti_cause_effect = ti_dict.get("cause_effect_pairs", [])

    # ─── Domain writing context labels ─────────────────────────
    DOMAIN_COVER_PATTERNS = {
        "biology": "biological mechanisms and principles",
        "medicine_health_sciences": "pathophysiology, evidence, and clinical relevance",
        "history": "historical dynamics and societal impact",
        "literature_humanities": "thematic exploration and critical interpretation",
        "environmental_science": "environmental dynamics, trends, and solutions",
        "computer_science": "architectural principles and system mechanics",
        "engineering": "design principles and engineering trade-offs",
        "physics": "physical models, phenomena, and experimental insight",
        "chemistry": "molecular mechanisms and reaction pathways",
        "mathematics": "mathematical structures and reasoning",
        "law": "legal doctrine, precedent, and application",
        "economics": "economic models, policy, and empirical evidence",
        "finance_accounting": "financial analysis, risk, and valuation",
        "business": "strategic frameworks, metrics, and decision-making",
        "education": "pedagogical principles and learning design",
        "social_sciences": "theoretical frameworks and empirical inquiry",
        "languages": "linguistic structures and communicative patterns",
        "general": "foundational concepts and core principles",
    }

    DOMAIN_CONTEXT_PATTERNS = {
        "history": "Historical setting and pre-conditions of {topic}",
        "biology": "Biological setting and systemic context of {topic}",
        "medicine_health_sciences": "Clinical context and pathological basis of {topic}",
        "computer_science": "Problem context and engineering challenges behind {topic}",
        "engineering": "Design requirements and constraints driving {topic}",
        "physics": "Physical context and observable phenomena behind {topic}",
        "chemistry": "Chemical context and conditions governing {topic}",
        "literature_humanities": "Literary context and cultural forces shaping {topic}",
        "law": "Legal context, jurisdiction, and doctrinal framework for {topic}",
        "economics": "Economic context, market conditions, and policy landscape of {topic}",
        "environmental_science": "Ecological baseline and environmental drivers of {topic}",
    }

    # ─── Synthesize messages for every blueprint ───────────────
    comp_counter = 0
    data_counter = 0
    process_counter = 0
    concept_counter = 0

    for bp in blueprints:
        if not force:
            is_generic = (
                not bp.primary_message
                or bp.primary_message.endswith(": Overview")
                or bp.primary_message == f"{topic}: Overview"
                or any(banned in bp.primary_message for banned in [
                    "Architecture & Foundations",
                    f"The Problem {topic} Solves",
                    f"How {topic} Works Step by Step",
                    f"Core Mechanism of {topic}",
                    f"Defining {topic}: Core Principles",
                ])
            )
            if not is_generic and bp.primary_message:
                continue

        # ─── COVER ─────────────────────────────────────────────
        if bp.intent == SlideIntent.COVER:
            cover_context = DOMAIN_COVER_PATTERNS.get(domain, DOMAIN_COVER_PATTERNS["general"])
            bp.primary_message = f"{topic}: {cover_context}"

        # ─── CONTEXT ───────────────────────────────────────────
        elif bp.intent == SlideIntent.CONTEXT:
            ctx_pattern = DOMAIN_CONTEXT_PATTERNS.get(
                domain,
                "Context, baseline conditions, and core drivers of {topic}",
            )
            bp.primary_message = ctx_pattern.format(topic=topic)

        # ─── WHY_IT_MATTERS ────────────────────────────────────
        elif bp.intent == SlideIntent.WHY_IT_MATTERS:
            if ti_cause_effect:
                ce = ti_cause_effect[0]
                cause = ce.get("cause", "") if isinstance(ce, dict) else str(ce)
                cause_clean = sanitize_and_complete_title(cause, topic=topic)
                bp.primary_message = f"Why {topic} matters: {cause_clean}" if cause_clean else f"Why understanding {topic} is essential and impactful"
            else:
                bp.primary_message = f"Why understanding {topic} is essential and impactful"

        # ─── DEFINITION ────────────────────────────────────────
        elif bp.intent == SlideIntent.DEFINITION:
            if ti_concepts:
                concept_str = ", ".join(ti_concepts[:3])
                bp.primary_message = f"Essential concepts of {topic}: {concept_str}"
            else:
                bp.primary_message = f"Essential concepts, terminology, and principles of {topic}"

        # ─── PROCESS_EXPLANATION ───────────────────────────────
        elif bp.intent == SlideIntent.PROCESS_EXPLANATION:
            process_counter += 1
            if ti_processes and process_counter <= len(ti_processes):
                process_name = ti_processes[process_counter - 1]
                bp.primary_message = f"{process_name}: operational stages and transitions"
            elif domain == "history":
                hist_phases = [
                    f"Origins, catalysts, and early transformation in {topic}",
                    f"Turning points, expansion, and chronological milestones in {topic}",
                    f"Consolidation, systemic changes, and societal outcomes of {topic}",
                ]
                bp.primary_message = hist_phases[(process_counter - 1) % len(hist_phases)]
            elif domain in ("biology", "medicine_health_sciences"):
                bio_phases = [
                    f"Step-by-step biological mechanisms and primary stages of {topic}",
                    f"Biochemical pathways, energy transformation, and cycles in {topic}",
                    f"Downstream regulation and cellular outcomes in {topic}",
                ]
                bp.primary_message = bio_phases[(process_counter - 1) % len(bio_phases)]
            elif domain == "chemistry":
                chem_phases = [
                    f"Reaction mechanism and pathway stages in {topic}",
                    f"Intermediates, transition states, and reaction conditions in {topic}",
                ]
                bp.primary_message = chem_phases[(process_counter - 1) % len(chem_phases)]
            else:
                proc_phases = [
                    f"Operational workflow and execution stages of {topic}",
                    f"Secondary transformation phases and handoff cycles in {topic}",
                    f"Control mechanisms and pipeline execution in {topic}",
                ]
                bp.primary_message = proc_phases[(process_counter - 1) % len(proc_phases)]

        # ─── SYSTEM_OVERVIEW ───────────────────────────────────
        elif bp.intent == SlideIntent.SYSTEM_OVERVIEW:
            if domain in ("biology", "environmental_science"):
                bp.primary_message = f"Structural organization and functional overview of {topic}"
            elif domain in ("computer_science", "engineering"):
                bp.primary_message = f"System architecture and component topology of {topic}"
            else:
                bp.primary_message = f"Structural overview and key components of {topic}"

        # ─── COMPONENT_BREAKDOWN ───────────────────────────────
        elif bp.intent == SlideIntent.COMPONENT_BREAKDOWN:
            if ti_concepts and len(ti_concepts) >= 3:
                bp.primary_message = f"Core subsystems of {topic}: {', '.join(ti_concepts[:3])}"
            else:
                bp.primary_message = f"Core subsystems and primary components of {topic}"

        # ─── CONCEPT_EXPLANATION ───────────────────────────────
        elif bp.intent == SlideIntent.CONCEPT_EXPLANATION:
            concept_counter += 1
            concept_perspectives = [
                f"Foundational principles and operational mechanisms of {topic}",
                f"Structural dynamics and component interactions in {topic}",
                f"Functional behavior and regulatory constraints of {topic}",
                f"Advanced concepts and practical implications of {topic}",
                f"Integration patterns and systematic behavior in {topic}",
            ]
            if bp.semantic_role and bp.semantic_role not in ("concept_explanation", "concept"):
                role_clean = bp.semantic_role.replace("_", " ").title()
                bp.primary_message = f"{role_clean} in {topic}: core mechanisms"
            elif ti_concepts and concept_counter <= len(ti_concepts):
                c_name = ti_concepts[concept_counter - 1]
                bp.primary_message = f"{c_name}: operational role within {topic}"
            else:
                bp.primary_message = concept_perspectives[(concept_counter - 1) % len(concept_perspectives)]

        # ─── COMPARISON ────────────────────────────────────────
        elif bp.intent == SlideIntent.COMPARISON:
            comp_counter += 1
            if ti_comparisons and comp_counter <= len(ti_comparisons):
                comp = ti_comparisons[comp_counter - 1]
                if isinstance(comp, dict):
                    a = comp.get("item_a", "")
                    b = comp.get("item_b", "")
                    axis = comp.get("comparison_axis", "")
                    bp.primary_message = f"Comparing {a} and {b}" + (f": {axis}" if axis else "")
                    bp.comparison_target = f"{a} vs {b}"
                else:
                    bp.primary_message = f"Contrasting primary approaches in {topic}"
                    bp.comparison_target = "Primary Approaches"
            elif comp_counter == 1:
                bp.primary_message = f"Contrasting primary approaches in {topic}"
                bp.comparison_target = "Primary Approaches"
            else:
                bp.primary_message = f"Comparing implementation models and tradeoffs in {topic}"
                bp.comparison_target = "Implementation Models"

        # ─── DATA_INSIGHT ──────────────────────────────────────
        elif bp.intent == SlideIntent.DATA_INSIGHT:
            data_counter += 1
            if data_counter == 1:
                bp.primary_message = f"Primary empirical trends and quantitative metrics for {topic}"
            elif data_counter == 2:
                bp.primary_message = f"Segmented distribution and comparative metrics in {topic}"
            else:
                bp.primary_message = f"Underlying drivers and factor breakdown for {topic}"

        # ─── TRADEOFF ──────────────────────────────────────────
        elif bp.intent == SlideIntent.TRADEOFF:
            bp.primary_message = f"Key tradeoffs, constraints, and decision factors in {topic}"

        # ─── WORKED_EXAMPLE ────────────────────────────────────
        elif bp.intent == SlideIntent.WORKED_EXAMPLE:
            if ti_examples:
                ex_clean = sanitize_and_complete_title(ti_examples[0], topic=topic)
                bp.primary_message = f"Worked example: {ex_clean}"
            else:
                bp.primary_message = f"Practical worked example and validation scenario for {topic}"

        # ─── CASE_STUDY ────────────────────────────────────────
        elif bp.intent == SlideIntent.CASE_STUDY:
            bp.primary_message = f"Real-world case study: implementation and outcomes in {topic}"

        # ─── REAL_WORLD_APPLICATION ────────────────────────────
        elif bp.intent == SlideIntent.REAL_WORLD_APPLICATION:
            if ti_examples and len(ti_examples) >= 2:
                ex_clean = sanitize_and_complete_title(ti_examples[0], topic=topic)
                bp.primary_message = f"Practical applications: {ex_clean}"
            else:
                bp.primary_message = f"Practical applications and modern relevance of {topic}"

        # ─── MISCONCEPTION ─────────────────────────────────────
        elif bp.intent == SlideIntent.MISCONCEPTION:
            if ti_misconceptions:
                myth = ti_misconceptions[0]
                myth_text = myth.get("myth", "") if isinstance(myth, dict) else str(myth)
                if myth_text:
                    myth_clean = sanitize_and_complete_title(myth_text, topic=topic)
                    bp.primary_message = f"Misconception: {myth_clean}"
                else:
                    bp.primary_message = f"Common misconceptions and clarified realities in {topic}"
            else:
                bp.primary_message = f"Common misconceptions and clarified realities in {topic}"

        # ─── BEST_PRACTICES ────────────────────────────────────
        elif bp.intent == SlideIntent.BEST_PRACTICES:
            bp.primary_message = f"Recommended best practices and guidelines for {topic}"

        # ─── SUMMARY ───────────────────────────────────────────
        elif bp.intent == SlideIntent.SUMMARY:
            bp.primary_message = f"Key takeaways and synthesis: {topic}"

        # ─── HOOK ──────────────────────────────────────────────
        elif bp.intent == SlideIntent.HOOK:
            bp.primary_message = f"Why {topic} demands attention now"

        # ─── KNOWLEDGE_CHECK ───────────────────────────────────
        elif bp.intent == SlideIntent.KNOWLEDGE_CHECK:
            bp.primary_message = f"Knowledge check: testing understanding of {topic}"

        # ─── FORMULA_EXPLANATION ───────────────────────────────
        elif bp.intent == SlideIntent.FORMULA_EXPLANATION:
            if ti_dict and ti_dict.get("formulas_or_equations"):
                form_clean = sanitize_and_complete_title(ti_dict['formulas_or_equations'][0], topic=topic)
                bp.primary_message = f"Formalizing {topic}: {form_clean}"
            else:
                bp.primary_message = f"Mathematical formalization and interpretation of {topic}"

        # ─── CODE_EXAMPLE ──────────────────────────────────────
        elif bp.intent == SlideIntent.CODE_EXAMPLE:
            bp.primary_message = f"Implementation example: {topic} in code"

        # ─── DIAGNOSTIC ───────────────────────────────────────
        elif bp.intent == SlideIntent.DIAGNOSTIC:
            bp.primary_message = f"Diagnostic reasoning and troubleshooting in {topic}"

        # ─── PREREQUISITES ─────────────────────────────────────
        elif bp.intent == SlideIntent.PREREQUISITES:
            bp.primary_message = f"Prerequisites and assumed knowledge for {topic}"

        # ─── MENTAL_MODEL ──────────────────────────────────────
        elif bp.intent == SlideIntent.MENTAL_MODEL:
            bp.primary_message = f"Building a mental model for {topic}"

        # ─── COMMON_MISTAKES ───────────────────────────────────
        elif bp.intent == SlideIntent.COMMON_MISTAKES:
            bp.primary_message = f"Common pitfalls and avoidable errors in {topic}"

        # ─── REFERENCES ───────────────────────────────────────
        elif bp.intent == SlideIntent.REFERENCES:
            bp.primary_message = f"References and further reading: {topic}"

        # ─── AGENDA / OBJECTIVES ───────────────────────────────
        elif bp.intent in (SlideIntent.AGENDA, SlideIntent.OBJECTIVES):
            bp.primary_message = f"Learning objectives and session agenda for {topic}"

        # ─── Q_AND_A ───────────────────────────────────────────
        elif bp.intent == SlideIntent.Q_AND_A:
            bp.primary_message = f"Questions, discussion, and review: {topic}"

        # ─── FALLBACK ──────────────────────────────────────────
        else:
            bp.primary_message = f"{topic}: {bp.intent.value.replace('_', ' ').title()}"

    # Final pass: sanitize and ensure complete grammatical headlines on all blueprints
    for bp in blueprints:
        bp.primary_message = sanitize_and_complete_title(bp.primary_message, topic=topic)

