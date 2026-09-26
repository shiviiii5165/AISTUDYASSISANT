"""
TeachGenie vNEXT — PresentationBrief Builder
==============================================
Transforms PresentationConfig (frontend API contract) into PresentationBrief
(internal intelligence representation) without requiring any frontend changes.

Flow (spec §3):
  PresentationConfig → PresentationBriefBuilder → PresentationBrief
"""
from app.core.logging import logger
import hashlib
import json
from typing import Optional, Dict, Any

from .schemas import (
    PresentationConfig,
    PresentationBrief,
    DomainClassification,
    TemplateSelectionSource,
)
from .domain_classifier import (
    classify_domain,
    classify_purpose,
    classify_mode,
    infer_technicality,
    infer_audience_expertise,
    infer_visual_preference,
    recommend_template,
    recommend_theme,
    recommend_story_grammar,
    estimate_duration,
    canonicalize_topic,
)


def build_presentation_brief(
    config: PresentationConfig,
    ontology_evidence: Optional[Dict[str, Any]] = None,
    domain_classification: Optional[DomainClassification] = None,
) -> PresentationBrief:
    """
    Build a PresentationBrief from a PresentationConfig.
    
    Applies all intelligence classification deterministically:
    - Domain classification (multi-signal or pre-refined model classification)
    - Purpose classification
    - Mode classification
    - Technicality inference
    - Template/theme recommendation with user override tracking
    - Story grammar selection with modifiers
    
    User explicit choices always win (spec §1).
    """
    topic = config.topic
    audience = config.audience
    custom_ctx = config.custom_instructions if hasattr(config, "custom_instructions") else ""
    depth = config.depth

    # ─── Domain Classification ────────────────────────────────
    if domain_classification is not None:
        domain_result = domain_classification
    else:
        domain_result = classify_domain(
            topic=topic,
            audience=audience,
            custom_context=custom_ctx,
            ontology_evidence=ontology_evidence,
        )

    # ─── Purpose Classification ───────────────────────────────
    purpose = classify_purpose(
        topic=topic,
        audience=audience,
        custom_context=custom_ctx,
        depth=depth,
    )

    # ─── Mode Classification ──────────────────────────────────
    mode = classify_mode(audience=audience, custom_context=custom_ctx)

    # ─── Technicality ─────────────────────────────────────────
    technicality = infer_technicality(
        domain=domain_result.domain,
        audience=audience,
        depth=depth,
    )

    # ─── Audience Expertise ───────────────────────────────────
    education_level = config.audience if config.audience else "university"
    expertise = infer_audience_expertise(audience, education_level)

    # ─── Visual Preference ────────────────────────────────────
    visual_pref = infer_visual_preference(domain_result.domain, technicality)

    # ─── Template Recommendation ──────────────────────────────
    recommended_tpl = recommend_template(domain_result.domain, purpose)

    # User override tracking (spec §1)
    user_design = config.design.value if hasattr(config.design, "value") else str(config.design)
    
    # Check if user explicitly selected a template or used default
    default_design = "academic"
    if user_design and user_design != default_design:
        selected_tpl = user_design
        tpl_source = TemplateSelectionSource.USER_OVERRIDE
    else:
        selected_tpl = recommended_tpl
        tpl_source = TemplateSelectionSource.AUTO_RECOMMENDED

    # ─── Theme Recommendation ─────────────────────────────────
    recommended_thm = recommend_theme(domain_result.domain, selected_tpl)

    user_theme = config.theme.strip() if config.theme else ""
    default_theme = ""
    if user_theme and user_theme != default_theme:
        selected_thm = user_theme
        thm_source = TemplateSelectionSource.USER_OVERRIDE
    else:
        selected_thm = recommended_thm
        thm_source = TemplateSelectionSource.AUTO_RECOMMENDED

    # ─── Story Grammar ────────────────────────────────────────
    primary_grammar, story_modifiers = recommend_story_grammar(
        domain=domain_result.domain,
        purpose=purpose,
        topic_intelligence=ontology_evidence,
    )

    # ─── Duration ─────────────────────────────────────────────
    duration = estimate_duration(config.slide_count)

    # ─── Source Hash ──────────────────────────────────────────
    source_hash = ""
    if config.source_id:
        source_hash = hashlib.sha256(
            f"{config.source_type}:{config.source_id}".encode()
        ).hexdigest()[:16]

    # ─── Canonical Topic ──────────────────────────────────────
    canonical = canonicalize_topic(topic)

    # ─── Build Brief ──────────────────────────────────────────
    brief = PresentationBrief(
        # Identity
        topic=topic,
        canonical_topic=canonical,
        # Domain
        domain=domain_result.domain,
        subdomain=domain_result.subdomain,
        domain_confidence=domain_result.confidence,
        classification_basis=domain_result.classification_basis,
        # Audience
        education_level=education_level,
        audience_expertise=expertise,
        # Purpose
        presentation_goal=purpose,
        presentation_mode=mode,
        # Timing
        duration_estimate=duration,
        # Complexity
        technicality=technicality,
        visual_preference=visual_pref,
        # Template/Theme
        selected_template=selected_tpl,
        recommended_template=recommended_tpl,
        template_selection_source=tpl_source,
        selected_theme=selected_thm,
        recommended_theme=recommended_thm,
        theme_selection_source=thm_source,
        # Story
        primary_story_grammar=primary_grammar,
        story_modifiers=story_modifiers,
        # Config
        slide_count=config.slide_count,
        language=config.language,
        knowledge_source=config.source_type or "general",
        source_hash=source_hash,
        custom_context=custom_ctx or None,
        # Feature toggles
        enable_diagrams=config.enable_diagrams,
        enable_images=config.enable_images,
        enable_speaker_notes=config.enable_speaker_notes,
        enable_sources=config.enable_sources,
        enable_examples=config.enable_examples,
        enable_quiz=config.enable_quiz,
    )

    logger.info(
        f"[BriefBuilder] Built PresentationBrief: "
        f"topic='{brief.canonical_topic}', domain={brief.domain}/{brief.subdomain}, "
        f"goal={brief.presentation_goal.value}, grammar={brief.primary_story_grammar.value}, "
        f"template={brief.selected_template}({brief.template_selection_source.value}), "
        f"theme={brief.selected_theme}({brief.theme_selection_source.value})"
    )
    return brief
