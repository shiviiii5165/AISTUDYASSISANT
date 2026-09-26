"""
Reviewer / Critic Agent (Step 4.5) — Master Prompt v2
======================================================
Acts as the final pedagogical and visual quality gate before PPTX rendering:
1. Fast Deterministic Pre-Checks (zero LLM cost):
   - Banned-string scanning across all text fields
   - Bullet quality checks (verb presence, no title repetition, no duplicates)
   - Subtopic traceability via keyword matching
   - Layout variety and pattern monotony detection
   - Full-slide content richness (underfit detection)
   - Speaker notes word-count validation
2. Single Scoped LLM Deck Critic Call
3. Targeted Repair Pass (max 1 iteration)
"""
from app.core.logging import logger
import asyncio
import json
import re
from typing import List, Dict, Any, Optional
from app.services.ai import router
from .schemas import PresentationConfig, VisualKind
from .prompts import REVIEWER_CRITIC_SYSTEM_PROMPT
from .topic_ontology_agent import TopicOntologyChecklist
from .qa_agent import repair_single_slide
from .content_agent import BANNED_STRINGS, _contains_banned, _has_verb


def run_deterministic_deck_checks(
    slides: List[Dict[str, Any]],
    ontology: Optional[TopicOntologyChecklist] = None,
) -> tuple[List[str], Dict[int, List[str]]]:
    """
    Zero-token structural, content quality, and pedagogical pre-checks.
    Returns (deck_level_issues, slide_level_issues).
    """
    deck_issues = []
    slide_issues: Dict[int, List[str]] = {}

    def add_issue(s_idx: int, msg: str):
        if s_idx not in slide_issues:
            slide_issues[s_idx] = []
        slide_issues[s_idx].append(msg)

    # ═══════════════════════════════════════════════════════════
    # 1. Subtopic Traceability
    # ═══════════════════════════════════════════════════════════
    if ontology and ontology.core_subtopics:
        deck_text_corpus = ""
        for i, s in enumerate(slides):
            text = f"{s.get('title', '')} {' '.join(str(b) for b in s.get('body_bullets', []))} {s.get('speaker_notes', '')}".lower()
            deck_text_corpus += " " + text

        for st in ontology.core_subtopics:
            words = [re.sub(r"[^\w]", "", w.lower()) for w in st.split()]
            meaningful = [w for w in words if len(w) > 3 and w not in ["with", "from", "that", "this", "into", "over", "scope", "core", "mechanism"]]
            if meaningful and not any(w in deck_text_corpus for w in meaningful):
                deck_issues.append(f"Subtopic '{st}' is missing from deck bullets and notes.")

    # ═══════════════════════════════════════════════════════════
    # 2. Banned-String Scanning (Deck-Wide)
    # ═══════════════════════════════════════════════════════════
    for i, s in enumerate(slides):
        s_no = s.get("slide_no", i + 1)

        # Check title
        if _contains_banned(s.get("title", "")):
            add_issue(s_no, f"Title contains banned filler string.")

        # Check bullets
        for b_idx, b in enumerate(s.get("body_bullets", [])):
            if _contains_banned(str(b)):
                add_issue(s_no, f"Bullet {b_idx+1} contains banned filler: '{str(b)[:40]}'.")

        # Check example
        if _contains_banned(s.get("example", "")):
            add_issue(s_no, f"Example text contains banned filler string.")

        # Check speaker notes
        if _contains_banned(s.get("speaker_notes", "")):
            add_issue(s_no, f"Speaker notes contain banned filler string.")

    # ═══════════════════════════════════════════════════════════
    # 3. Bullet Quality Checks (Deck-Wide)
    # ═══════════════════════════════════════════════════════════
    for i, s in enumerate(slides):
        s_no = s.get("slide_no", i + 1)
        stype = s.get("type", "concept")
        title_lower = s.get("title", "").lower().strip()
        bullets = s.get("body_bullets", [])

        if stype in ["hero", "qa", "closing", "quiz"]:
            continue

        # Verb presence check
        for b_idx, b in enumerate(bullets):
            b_str = str(b).strip()
            if b_str and not _has_verb(b_str):
                add_issue(s_no, f"Bullet {b_idx+1} appears to lack a verb (noun fragment).")

        # Title repetition check
        for b_idx, b in enumerate(bullets):
            if title_lower and str(b).lower().strip() == title_lower:
                add_issue(s_no, f"Bullet {b_idx+1} repeats the slide title verbatim.")

        # Duplicate detection
        seen = set()
        for b_idx, b in enumerate(bullets):
            key = str(b).lower().strip()
            if key in seen:
                add_issue(s_no, f"Bullet {b_idx+1} is a duplicate.")
            seen.add(key)

    # ═══════════════════════════════════════════════════════════
    # 4. Full-Slide Content Richness (Underfit Detection)
    # ═══════════════════════════════════════════════════════════
    for i, s in enumerate(slides):
        s_no = s.get("slide_no", i + 1)
        stype = s.get("type", "concept")
        bullets = s.get("body_bullets", [])
        has_specialized = bool(s.get("layers") or s.get("steps") or s.get("metrics") or s.get("columns") or s.get("milestones"))

        if stype in ["hero", "qa", "closing", "quiz", "summary"]:
            continue

        if len(bullets) < 3 and not has_specialized:
            add_issue(s_no, f"Content slide is underfit — only {len(bullets)} content blocks (need 3-5 for rich layout).")

    # ═══════════════════════════════════════════════════════════
    # 5. Speaker Notes Validation
    # ═══════════════════════════════════════════════════════════
    for i, s in enumerate(slides):
        s_no = s.get("slide_no", i + 1)
        stype = s.get("type", "concept")
        notes = s.get("speaker_notes", "").strip()

        if stype in ["hero", "qa", "closing", "quiz"]:
            continue

        if not notes:
            add_issue(s_no, "Speaker notes are missing entirely.")
        else:
            wc = len(notes.split())
            if wc < 90:
                add_issue(s_no, f"Speaker notes are too short ({wc} words, need 90-160).")

    # ═══════════════════════════════════════════════════════════
    # 6. Layout Variety & Pattern Monotony
    # ═══════════════════════════════════════════════════════════
    pill_count = 0
    pattern_counts: Dict[str, int] = {}
    total_content_slides = max(1, len(slides))

    for s in slides:
        cpat = str(s.get("content_pattern", "")).lower()
        stype = str(s.get("type", "")).lower()
        is_pill = (cpat == "parallel_comparison" or (stype == "comparison" and cpat != "comparison_table"))
        if is_pill:
            pill_count += 1
        if cpat and cpat not in ["plain_concept", "hero", "qa"]:
            pattern_counts[cpat] = pattern_counts.get(cpat, 0) + 1

    pill_ratio = pill_count / total_content_slides
    if pill_ratio > 0.25:
        deck_issues.append(
            f"Circle-pill comparison overuse: {pill_count}/{total_content_slides} ({pill_ratio:.1%}) "
            f"exceeds 25% cap. Re-assign excess to 'comparison_table', 'contrast_pair', or 'plain_concept'."
        )

    # Monotony check
    for pat, count in pattern_counts.items():
        if pat != "parallel_comparison":
            ratio = count / total_content_slides
            if ratio > 0.35:
                deck_issues.append(f"Pattern monotony: '{pat}' occurs {count} times ({ratio:.1%}), exceeding threshold.")

    # Consecutive repetition check (no 3 consecutive identical types or patterns)
    for i in range(len(slides) - 2):
        t1, t2, t3 = slides[i].get("type"), slides[i+1].get("type"), slides[i+2].get("type")
        p1 = str(slides[i].get("content_pattern", "")).lower()
        p2 = str(slides[i+1].get("content_pattern", "")).lower()
        p3 = str(slides[i+2].get("content_pattern", "")).lower()

        if t1 and t1 == t2 == t3 and t1 not in ["hero", "qa", "concept"]:
            deck_issues.append(f"Layout repetition: 3 consecutive slides ({i+1}, {i+2}, {i+3}) use type '{t1}'.")

        if p1 and p1 == p2 == p3 and p1 not in ["", "plain_concept"]:
            deck_issues.append(f"Pattern repetition: 3 consecutive slides ({i+1}, {i+2}, {i+3}) repeat pattern '{p1}'.")

        if p1 == "parallel_comparison" and p2 == "parallel_comparison":
            deck_issues.append(f"Consecutive circle-pill comparisons on slides {i+1} and {i+2}.")

    # ═══════════════════════════════════════════════════════════
    # 7. Slide-Level Visual & Data Inspections
    # ═══════════════════════════════════════════════════════════
    for i, s in enumerate(slides):
        s_no = s.get("slide_no", i + 1)
        stype = s.get("type", "concept")
        vspec = s.get("visual_spec") or {}

        # Silent image failure detection
        if vspec.get("kind") == VisualKind.IMAGE.value or vspec.get("asset_required"):
            if not vspec.get("image_bytes") and not s.get("image_bytes"):
                add_issue(s_no, "Assigned image query but image bytes were omitted.")

        # Underfit check on steps / phase layouts
        if stype in ["process_flow", "flow"]:
            steps = s.get("steps", [])
            for st_idx, step in enumerate(steps):
                title_len = len(step.get("title", ""))
                detail_len = len(step.get("detail", ""))
                if title_len + detail_len < 10:
                    add_issue(s_no, f"Step {st_idx+1} is severely underfit ({title_len + detail_len} chars).")

    return deck_issues, slide_issues


async def run_reviewer_critic(
    config: PresentationConfig,
    slides: List[Dict[str, Any]],
    ontology: Optional[TopicOntologyChecklist] = None,
) -> List[Dict[str, Any]]:
    """
    Step 4.5: Runs deterministic pre-checks + 1 scoped LLM critic call,
    triggering single-slide repair for flagged defects (max 1 pass).
    """
    logger.info(f"[ReviewerAgent] Running pre-checks and pedagogical critic for '{config.topic}'...")

    # 1. Deterministic Pre-Checks
    deck_issues, slide_issues = run_deterministic_deck_checks(slides, ontology)
    if deck_issues:
        logger.info(f"[ReviewerAgent] Deterministic pre-checks flagged: {deck_issues[:3]}")
    if slide_issues:
        logger.info(f"[ReviewerAgent] Slide-level issues found on {len(slide_issues)} slide(s).")

    # 2. Single Condensed LLM Critic Call for the Entire Deck
    condensed_deck = []
    for s in slides:
        bullets_brief = " | ".join(str(b)[:60] for b in s.get("body_bullets", [])[:3])
        condensed_deck.append({
            "slide_no": s.get("slide_no"),
            "type": s.get("type"),
            "title": s.get("title"),
            "key_message": s.get("key_message"),
            "bullets_preview": bullets_brief,
            "bullet_count": len(s.get("body_bullets", [])),
            "has_example": bool(s.get("example")),
            "has_notes": bool(s.get("speaker_notes", "").strip()),
            "has_visual": bool((s.get("visual_spec") or {}).get("image_bytes") or s.get("steps") or s.get("layers")),
        })

    critic_prompt = {
        "topic": config.topic,
        "audience": config.audience,
        "core_subtopics_required": ontology.core_subtopics if ontology else [],
        "slides_summary": condensed_deck,
        "pre_check_notes": deck_issues[:4],
    }

    try:
        from app.services.ai.circuit_breaker import circuit_breaker
        if not circuit_breaker.can_execute():
            critic_res = {"overall_rating": 4, "needs_revision": False, "flagged_slides": []}
        else:
            critic_res = await router.generate_json(
                task="qa",
                messages=[
                    {"role": "system", "content": REVIEWER_CRITIC_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Review this generated presentation against the LearnByGenie Master Standard:\n{json.dumps(critic_prompt, indent=2)}"},
                ],
                temperature=0.2,
                max_tokens=2048,
            )
    except Exception as e:
        logger.warning(f"[ReviewerAgent] Critic LLM call failed (proceeding with pre-check repairs): {e}")
        critic_res = {"overall_rating": 4, "needs_revision": False, "flagged_slides": []}

    rating = critic_res.get("overall_rating", 4)
    verdict = critic_res.get("pedagogical_verdict", "Acceptable")
    flagged = critic_res.get("flagged_slides", [])

    logger.info(f"[ReviewerAgent] Deck rating: {rating}/5 | Verdict: {verdict}")

    # 3. Combine Pre-check flags and Critic flags (capped at max 3 repairs)
    repair_queue: Dict[int, tuple[List[str], str]] = {}

    # Add critic flagged slides
    for f in flagged:
        if len(repair_queue) >= 3:
            break
        s_no = f.get("slide_no")
        if s_no:
            issue = f.get("issue", "Quality defect flagged by critic")
            directive = f.get("repair_directive", "")
            repair_queue[s_no] = ([issue], directive)

    # Add pre-check flagged slides if room
    for s_no, issues in slide_issues.items():
        if s_no not in repair_queue and len(repair_queue) < 3:
            repair_queue[s_no] = (issues, "Correct structural, content quality, and layout issues per Master Prompt standard.")

    # 4. Execute Targeted Repairs (Strictly capped at 1 pass)
    if repair_queue:
        from ..ai.circuit_breaker import circuit_breaker
        if not circuit_breaker.can_execute():
            logger.info("[ReviewerAgent] Circuit breaker open; bypassing LLM targeted repair pass.")
            return slides
        logger.info(f"[ReviewerAgent] Triggering targeted repairs for {len(repair_queue)} slide(s): {list(repair_queue.keys())}")
        repaired_slides = []
        for s in slides:
            s_no = s.get("slide_no")
            if s_no in repair_queue:
                issues, directive = repair_queue[s_no]
                try:
                    healed = await asyncio.wait_for(
                        repair_single_slide(s, issues, directive=directive),
                        timeout=15.0,
                    )
                    repaired_slides.append(healed)
                except (asyncio.TimeoutError, Exception) as e:
                    logger.warning(f"[ReviewerAgent] Repair for slide {s_no} failed ({e}) — keeping original.")
                    repaired_slides.append(s)
            else:
                repaired_slides.append(s)
        return repaired_slides

    return slides
