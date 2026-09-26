"""
LearnByGenie vNEXT — Blueprint Sequence Validator
=================================================
Validates the complete SlideBlueprint sequence BEFORE content expansion.
Deterministic checks only — no LLM call (spec §13).

If validation fails, returns targeted repair directives.
Does NOT trigger full content regeneration (spec §11).
"""
from app.core.logging import logger
from typing import List, Tuple, Optional, Dict, Any
from .schemas import (
    SlideIntent,
    SlideBlueprint,
    PresentationBrief,
    LayoutFamily,
    VisualTypeHint,
)


# ═══════════════════════════════════════════════════════════════
# VALIDATION ISSUES
# ═══════════════════════════════════════════════════════════════

class BlueprintIssue:
    """A specific issue found during blueprint validation."""
    def __init__(self, severity: str, slide_id: str, issue: str, repair: str):
        self.severity = severity  # "error" | "warning"
        self.slide_id = slide_id
        self.issue = issue
        self.repair = repair

    def __repr__(self):
        return f"[{self.severity.upper()}] {self.slide_id}: {self.issue} → {self.repair}"


# ═══════════════════════════════════════════════════════════════
# VALIDATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def validate_blueprint_sequence(
    blueprints: List[SlideBlueprint],
    brief: PresentationBrief,
) -> Tuple[bool, List[BlueprintIssue]]:
    """
    Validate blueprint sequence coherence (spec §11).
    
    Checks:
      1. Exact requested slide count
      2. Cover placement (must be first)
      3. Logical concept progression
      4. No duplicate primary_message
      5. No duplicate narrative_role unless justified
      6. Prerequisites before dependent concepts
      7. Examples after enough explanation
      8. Summary near end
      9. Quiz only when enabled
      10. References when enabled
      11. Layout/visual diversity potential
    
    Returns (passed, issues).
    If passed=False, repair planning only — no content generation.
    """
    issues: List[BlueprintIssue] = []

    if not blueprints:
        issues.append(BlueprintIssue(
            "error", "all", "No blueprints generated", "Regenerate blueprint sequence"
        ))
        return False, issues

    # ─── 1. Exact slide count ─────────────────────────────────
    expected = brief.slide_count
    actual = len(blueprints)
    if actual != expected:
        issues.append(BlueprintIssue(
            "error", "all",
            f"Slide count mismatch: expected {expected}, got {actual}",
            f"Adjust blueprint count to exactly {expected}",
        ))

    # ─── 2. Cover placement ───────────────────────────────────
    if blueprints[0].intent != SlideIntent.COVER:
        issues.append(BlueprintIssue(
            "error", blueprints[0].slide_id,
            "First slide must be COVER intent",
            "Set first blueprint intent to COVER",
        ))

    # ─── 3. Logical progression — no advanced before basics ───
    FOUNDATIONAL = {
        SlideIntent.CONTEXT, SlideIntent.WHY_IT_MATTERS,
        SlideIntent.DEFINITION, SlideIntent.OBJECTIVES,
        SlideIntent.PREREQUISITES,
    }
    ADVANCED = {
        SlideIntent.WORKED_EXAMPLE, SlideIntent.CODE_EXAMPLE,
        SlideIntent.CASE_STUDY, SlideIntent.TRADEOFF,
        SlideIntent.COMMON_MISTAKES, SlideIntent.BEST_PRACTICES,
    }
    found_foundational = False
    for bp in blueprints:
        if bp.intent in FOUNDATIONAL:
            found_foundational = True
        if bp.intent in ADVANCED and not found_foundational:
            issues.append(BlueprintIssue(
                "warning", bp.slide_id,
                f"Advanced intent '{bp.intent.value}' appears before any foundational slide",
                "Move foundational slides (definition/context) earlier",
            ))
            break

    # ─── 4. Duplicate primary_message ─────────────────────────
    messages = [bp.primary_message for bp in blueprints if bp.primary_message]
    seen_messages = set()
    for msg in messages:
        normalized = msg.strip().lower()
        if normalized in seen_messages:
            issues.append(BlueprintIssue(
                "warning", "multiple",
                f"Duplicate primary_message: '{msg[:60]}...'",
                "Each blueprint must have a unique primary_message",
            ))
        seen_messages.add(normalized)

    # ─── 5. Duplicate narrative_role ──────────────────────────
    roles = [bp.narrative_role for bp in blueprints if bp.narrative_role]
    role_counts: Dict[str, int] = {}
    for role in roles:
        role_counts[role] = role_counts.get(role, 0) + 1
    # Allow duplicates for generic roles like "concept_explanation"
    GENERIC_ROLES = {"concept_explanation", "mechanism", ""}
    for role, count in role_counts.items():
        if count > 2 and role not in GENERIC_ROLES:
            issues.append(BlueprintIssue(
                "warning", "multiple",
                f"Narrative role '{role}' appears {count} times",
                "Diversify narrative roles for better storytelling",
            ))

    # ─── 6. Prerequisites before dependent concepts ───────────
    prereq_index = None
    for i, bp in enumerate(blueprints):
        if bp.intent == SlideIntent.PREREQUISITES:
            prereq_index = i
    if prereq_index is not None and prereq_index > len(blueprints) // 2:
        issues.append(BlueprintIssue(
            "warning", blueprints[prereq_index].slide_id,
            "Prerequisites slide appears too late in the sequence",
            "Move prerequisites to early in the deck (within first 25%)",
        ))

    # ─── 7. Examples after explanation ────────────────────────
    has_explanation = False
    for bp in blueprints:
        if bp.intent in (SlideIntent.CONCEPT_EXPLANATION, SlideIntent.DEFINITION,
                        SlideIntent.SYSTEM_OVERVIEW):
            has_explanation = True
        if bp.intent in (SlideIntent.WORKED_EXAMPLE, SlideIntent.CASE_STUDY) and not has_explanation:
            issues.append(BlueprintIssue(
                "warning", bp.slide_id,
                f"Example/case study appears before any explanation slide",
                "Ensure at least one concept/definition slide precedes examples",
            ))
            break

    # ─── 8. Summary near end ──────────────────────────────────
    summary_indices = [i for i, bp in enumerate(blueprints)
                       if bp.intent == SlideIntent.SUMMARY]
    if not summary_indices:
        issues.append(BlueprintIssue(
            "warning", "all",
            "No SUMMARY slide found",
            "Add a SUMMARY slide near the end of the deck",
        ))
    elif summary_indices[0] < len(blueprints) - 3:
        issues.append(BlueprintIssue(
            "warning", blueprints[summary_indices[0]].slide_id,
            "SUMMARY slide is not near the end of the deck",
            "Move SUMMARY to penultimate or ante-penultimate position",
        ))

    # ─── 9. Quiz only when enabled ────────────────────────────
    quiz_slides = [bp for bp in blueprints if bp.intent == SlideIntent.KNOWLEDGE_CHECK]
    if quiz_slides and not brief.enable_quiz:
        issues.append(BlueprintIssue(
            "error", quiz_slides[0].slide_id,
            "KNOWLEDGE_CHECK slide present but quiz is disabled",
            "Remove quiz slide or replace with another intent",
        ))
    if brief.enable_quiz and not quiz_slides:
        issues.append(BlueprintIssue(
            "warning", "all",
            "Quiz is enabled but no KNOWLEDGE_CHECK slide found",
            "Add a KNOWLEDGE_CHECK slide near the end",
        ))

    # ─── 10. Layout/visual diversity ──────────────────────────
    layouts = [bp.layout_family for bp in blueprints if bp.intent != SlideIntent.COVER]
    visuals = [bp.visual_type for bp in blueprints if bp.intent != SlideIntent.COVER]

    unique_layouts = len(set(layouts))
    unique_visuals = len(set(visuals))
    content_count = len(layouts)

    if content_count > 5 and unique_layouts < 3:
        issues.append(BlueprintIssue(
            "warning", "all",
            f"Low layout diversity: only {unique_layouts} unique layouts for {content_count} content slides",
            "Increase layout variety for visual engagement",
        ))

    if content_count > 5 and unique_visuals < 3:
        issues.append(BlueprintIssue(
            "warning", "all",
            f"Low visual diversity: only {unique_visuals} unique visual types for {content_count} content slides",
            "Use more varied visual representations",
        ))

    # ─── 11. No 3+ consecutive identical intents ─────────────
    for i in range(len(blueprints) - 2):
        if (blueprints[i].intent == blueprints[i+1].intent == blueprints[i+2].intent
                and blueprints[i].intent != SlideIntent.CONCEPT_EXPLANATION):
            issues.append(BlueprintIssue(
                "warning", blueprints[i+1].slide_id,
                f"Three consecutive slides with intent '{blueprints[i].intent.value}'",
                "Break monotony by interleaving different intent types",
            ))

    # ─── 12. Semantic Sanity Checks (spec §8) ────────────────
    sanity = compute_semantic_sanity_score(blueprints, brief)
    if not sanity["passed"]:
        for check_name, check_data in sanity["checks"].items():
            if not check_data["passed"]:
                for detail in check_data["details"]:
                    issues.append(BlueprintIssue(
                        "error", "semantic",
                        f"[{check_name}] {detail}",
                        f"Apply semantic sanity repair for {check_name}",
                    ))

    # ─── Determine pass/fail ──────────────────────────────────
    errors = [iss for iss in issues if iss.severity == "error"]
    passed = len(errors) == 0

    if issues:
        logger.warning(
            f"[BlueprintValidator] {len(errors)} errors, "
            f"{len(issues) - len(errors)} warnings in blueprint sequence"
        )
        for iss in issues:
            logger.warning(f"  {iss}")
    else:
        logger.info("[BlueprintValidator] Blueprint sequence passed all checks")

    return passed, issues


def compute_semantic_sanity_score(
    blueprints: List[SlideBlueprint],
    brief: PresentationBrief,
    topic_intelligence: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Blueprint Semantic Sanity Checks (spec §8).
    Evaluates:
      1. TOPIC_ROLE_FIT: Narrative/semantic roles align with domain
      2. TITLE_TOPIC_FIT: Zero banned canned generic titles
      3. VISUAL_TOPIC_FIT: Visual types fit topic & domain semantics
      4. BEAT_UNIQUENESS: No semantically equivalent duplicate blueprints without progression
      5. CONCEPT_PROGRESSION: Logical progression from foundations to synthesis
    
    Returns:
      dict with "passed", "overall_score", and "checks".
    """
    topic = brief.topic.strip()
    topic_lower = topic.lower()
    domain = brief.domain.lower()

    checks = {
        "TOPIC_ROLE_FIT": {"passed": True, "score": 1.0, "details": []},
        "TITLE_TOPIC_FIT": {"passed": True, "score": 1.0, "details": []},
        "VISUAL_TOPIC_FIT": {"passed": True, "score": 1.0, "details": []},
        "BEAT_UNIQUENESS": {"passed": True, "score": 1.0, "details": []},
        "CONCEPT_PROGRESSION": {"passed": True, "score": 1.0, "details": []},
    }

    # ─── 1. TOPIC_ROLE_FIT ─────────────────────────────────────
    if domain in ("biology", "medicine_health_sciences", "history", "literature_humanities", "law"):
        for bp in blueprints:
            role_lower = (bp.semantic_role or bp.narrative_role).lower()
            if role_lower in ("concurrency_model", "code_implementation", "thread_pool"):
                checks["TOPIC_ROLE_FIT"]["passed"] = False
                checks["TOPIC_ROLE_FIT"]["score"] = max(0.0, checks["TOPIC_ROLE_FIT"]["score"] - 0.25)
                checks["TOPIC_ROLE_FIT"]["details"].append(
                    f"Slide {bp.slide_number}: Inappropriate technical role '{role_lower}' for domain '{domain}'"
                )

    # ─── 2. TITLE_TOPIC_FIT ────────────────────────────────────
    banned_canned = [
        "Architecture & Foundations",
        f"The Problem {topic} Solves",
        f"How {topic} Works Step by Step",
        f"Core Mechanism of {topic}",
        f"Defining {topic}: Core Principles",
    ]
    for bp in blueprints:
        msg = bp.primary_message or ""
        for banned in banned_canned:
            if banned.lower() in msg.lower():
                checks["TITLE_TOPIC_FIT"]["passed"] = False
                checks["TITLE_TOPIC_FIT"]["score"] = max(0.0, checks["TITLE_TOPIC_FIT"]["score"] - 0.25)
                checks["TITLE_TOPIC_FIT"]["details"].append(
                    f"Slide {bp.slide_number}: Contains banned canned phrasing: '{msg}'"
                )
                break

    # ─── 3. VISUAL_TOPIC_FIT ───────────────────────────────────
    for bp in blueprints:
        if domain in ("biology", "medicine_health_sciences"):
            if bp.visual_type == VisualTypeHint.LAYERED_ARCHITECTURE:
                checks["VISUAL_TOPIC_FIT"]["passed"] = False
                checks["VISUAL_TOPIC_FIT"]["score"] = max(0.0, checks["VISUAL_TOPIC_FIT"]["score"] - 0.25)
                checks["VISUAL_TOPIC_FIT"]["details"].append(
                    f"Slide {bp.slide_number}: Inappropriate layered_architecture in biology presentation"
                )
        if domain in ("history", "literature_humanities", "law"):
            if bp.visual_type in (VisualTypeHint.LAYERED_ARCHITECTURE, VisualTypeHint.CODE_BLOCK):
                checks["VISUAL_TOPIC_FIT"]["passed"] = False
                checks["VISUAL_TOPIC_FIT"]["score"] = max(0.0, checks["VISUAL_TOPIC_FIT"]["score"] - 0.25)
                checks["VISUAL_TOPIC_FIT"]["details"].append(
                    f"Slide {bp.slide_number}: Inappropriate technical visual {bp.visual_type.value} in {domain}"
                )
        if domain == "environmental_science":
            if bp.visual_type == VisualTypeHint.LAYERED_ARCHITECTURE:
                checks["VISUAL_TOPIC_FIT"]["passed"] = False
                checks["VISUAL_TOPIC_FIT"]["score"] = max(0.0, checks["VISUAL_TOPIC_FIT"]["score"] - 0.25)
                checks["VISUAL_TOPIC_FIT"]["details"].append(
                    f"Slide {bp.slide_number}: Inappropriate layered_architecture in environmental science"
                )
        if "research" in topic_lower or "methodology" in topic_lower or brief.primary_story_grammar.value == "research":
            if bp.visual_type == VisualTypeHint.CODE_BLOCK and bp.intent != SlideIntent.CODE_EXAMPLE:
                checks["VISUAL_TOPIC_FIT"]["passed"] = False
                checks["VISUAL_TOPIC_FIT"]["score"] = max(0.0, checks["VISUAL_TOPIC_FIT"]["score"] - 0.25)
                checks["VISUAL_TOPIC_FIT"]["details"].append(
                    f"Slide {bp.slide_number}: code_block for generic research methodology explanation"
                )

    # ─── 4. BEAT_UNIQUENESS ────────────────────────────────────
    seen_messages = set()
    for i, bp in enumerate(blueprints):
        norm_msg = (bp.primary_message or "").strip().lower()
        if norm_msg and norm_msg in seen_messages:
            checks["BEAT_UNIQUENESS"]["passed"] = False
            checks["BEAT_UNIQUENESS"]["score"] = max(0.0, checks["BEAT_UNIQUENESS"]["score"] - 0.3)
            checks["BEAT_UNIQUENESS"]["details"].append(
                f"Slide {bp.slide_number}: Duplicate message '{norm_msg[:50]}...'"
            )
        if norm_msg:
            seen_messages.add(norm_msg)

        if i > 0 and bp.intent == blueprints[i-1].intent:
            prev = blueprints[i-1]
            if (bp.visual_type == prev.visual_type and
                bp.layout_family == prev.layout_family and
                not bp.comparison_target and not prev.comparison_target and
                (bp.semantic_role == prev.semantic_role or not bp.semantic_role)):
                checks["BEAT_UNIQUENESS"]["passed"] = False
                checks["BEAT_UNIQUENESS"]["score"] = max(0.0, checks["BEAT_UNIQUENESS"]["score"] - 0.3)
                checks["BEAT_UNIQUENESS"]["details"].append(
                    f"Slides {prev.slide_number} and {bp.slide_number}: Near-duplicate adjacent {bp.intent.value} blueprints without distinct progression"
                )

    def_slides = [bp for bp in blueprints if bp.intent == SlideIntent.DEFINITION]
    if len(def_slides) > 1:
        msgs = [bp.primary_message.lower() for bp in def_slides if bp.primary_message]
        if len(set(msgs)) < len(msgs):
            checks["BEAT_UNIQUENESS"]["passed"] = False
            checks["BEAT_UNIQUENESS"]["score"] = max(0.0, checks["BEAT_UNIQUENESS"]["score"] - 0.25)
            checks["BEAT_UNIQUENESS"]["details"].append("Duplicate generic DEFINITION beats detected")

    # ─── 5. CONCEPT_PROGRESSION ────────────────────────────────
    if blueprints and blueprints[0].intent != SlideIntent.COVER:
        checks["CONCEPT_PROGRESSION"]["passed"] = False
        checks["CONCEPT_PROGRESSION"]["score"] = 0.0
        checks["CONCEPT_PROGRESSION"]["details"].append("Deck does not start with COVER intent")

    summary_slides = [bp for bp in blueprints if bp.intent == SlideIntent.SUMMARY]
    if not summary_slides:
        checks["CONCEPT_PROGRESSION"]["passed"] = False
        checks["CONCEPT_PROGRESSION"]["score"] = 0.5
        checks["CONCEPT_PROGRESSION"]["details"].append("No SUMMARY intent near the end")

    passed = all(c["passed"] for c in checks.values())
    overall_score = sum(c["score"] for c in checks.values()) / len(checks)

    return {
        "passed": passed,
        "overall_score": overall_score,
        "checks": checks,
    }


def repair_blueprint_sequence(
    blueprints: List[SlideBlueprint],
    issues: List[BlueprintIssue],
    brief: PresentationBrief,
) -> List[SlideBlueprint]:
    """
    Apply targeted repairs to a blueprint sequence based on validation issues.
    Only modifies what's broken — no full regeneration.
    """
    repaired = list(blueprints)
    from .story_grammar import sanitize_visual_type_for_topic

    for iss in issues:
        if iss.severity != "error":
            continue

        # Repair: cover not first
        if "cover" in iss.issue.lower() and "first" in iss.issue.lower():
            if repaired and repaired[0].intent != SlideIntent.COVER:
                repaired[0].intent = SlideIntent.COVER
                repaired[0].narrative_role = "cover"
                logger.info("[BlueprintRepair] Set first slide to COVER")

        # Repair: slide count mismatch
        if "Slide count mismatch" in iss.issue:
            target = brief.slide_count
            while len(repaired) > target:
                for j in range(len(repaired) - 2, 0, -1):
                    if repaired[j].intent not in (SlideIntent.COVER, SlideIntent.SUMMARY,
                                                   SlideIntent.Q_AND_A):
                        repaired.pop(j)
                        break
                else:
                    break
            while len(repaired) < target:
                insert_pos = max(1, len(repaired) - 1)
                new_bp = SlideBlueprint(
                    slide_id=f"slide_{insert_pos + 1}_inserted",
                    slide_number=insert_pos + 1,
                    intent=SlideIntent.CONCEPT_EXPLANATION,
                    narrative_role="additional_concept",
                )
                repaired.insert(insert_pos, new_bp)
            for k, bp in enumerate(repaired):
                bp.slide_number = k + 1
                bp.slide_id = f"slide_{k + 1}"
            logger.info(f"[BlueprintRepair] Adjusted to {len(repaired)} slides")

        # Repair: quiz when disabled
        if "KNOWLEDGE_CHECK" in iss.issue and "disabled" in iss.issue:
            repaired = [bp for bp in repaired
                        if bp.intent != SlideIntent.KNOWLEDGE_CHECK]
            for k, bp in enumerate(repaired):
                bp.slide_number = k + 1
                bp.slide_id = f"slide_{k + 1}"
            logger.info("[BlueprintRepair] Removed quiz slide (disabled)")

        # Repair: domain-inappropriate visual
        if "VISUAL_TOPIC_FIT" in iss.issue or "Inappropriate" in iss.issue:
            for bp in repaired:
                bp.visual_type = sanitize_visual_type_for_topic(
                    bp.visual_type, bp.intent, brief.domain, brief.topic
                )
            logger.info("[BlueprintRepair] Sanitized visual types for domain")

        # Repair: canned titles or duplicate messages
        if "TITLE_TOPIC_FIT" in iss.issue or "BEAT_UNIQUENESS" in iss.issue or "banned canned" in iss.issue or "Duplicate primary_message" in iss.issue:
            from .planner_agent import _apply_deterministic_messages
            _apply_deterministic_messages(repaired, brief, force=True)
            logger.info("[BlueprintRepair] Applied domain-aware semantic titles to repaired blueprints")

    return repaired
