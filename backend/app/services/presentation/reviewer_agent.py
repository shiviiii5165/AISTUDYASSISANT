"""
Reviewer / Critic Agent (Step 4.5)
==================================
Acts as the final pedagogical and visual quality gate before PPTX rendering:
1. Fast Deterministic Pre-Checks (zero LLM cost):
   - Verifies core subtopics are covered with real substance in bullets/notes.
   - Checks layout variety (no 3+ consecutive identical templates).
   - Ensures no empty shapes or missing images exist.
2. Single Scoped LLM Deck Critic Call:
   - Evaluates the deck as an integrated whole against the TeachGenie standard.
   - Judges depth (Definition -> Mechanism -> Example -> Application).
3. Targeted Repair Pass:
   - Reuses qa_agent.py's repair path for any flagged slide.
   - Strictly capped at 1 iteration (speed and stability prioritized).
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


def run_deterministic_deck_checks(
    slides: List[Dict[str, Any]],
    ontology: Optional[TopicOntologyChecklist] = None,
) -> tuple[List[str], Dict[int, List[str]]]:
    """
    Zero-token structural & pedagogical pre-checks.
    Returns (deck_level_issues, slide_level_issues).
    """
    deck_issues = []
    slide_issues: Dict[int, List[str]] = {}

    def add_issue(s_idx: int, msg: str):
        if s_idx not in slide_issues:
            slide_issues[s_idx] = []
        slide_issues[s_idx].append(msg)

    # 1. Subtopic Traceability
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

    # 2. Layout Variety & Circle-Pill (Parallel Comparison) Usage Cap
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
            f"exceeds the 25% maximum cap. Re-assign excess to 'comparison_table', 'contrast_pair', or 'plain_concept'."
        )

    # Monotony check: no single specialized component exceeds 25% of the deck
    for pat, count in pattern_counts.items():
        if pat != "parallel_comparison":  # already checked above
            ratio = count / total_content_slides
            if ratio > 0.35:
                deck_issues.append(f"Component monotony: pattern '{pat}' occurs {count} times ({ratio:.1%}), exceeding threshold.")

    # Consecutive repetition check (no 3 consecutive identical slide types or patterns)
    for i in range(len(slides) - 2):
        t1, t2, t3 = slides[i].get("type"), slides[i+1].get("type"), slides[i+2].get("type")
        p1 = str(slides[i].get("content_pattern", "")).lower()
        p2 = str(slides[i+1].get("content_pattern", "")).lower()
        p3 = str(slides[i+2].get("content_pattern", "")).lower()

        if t1 and t1 == t2 == t3 and t1 not in ["hero", "qa", "concept"]:
            deck_issues.append(f"Layout repetition: 3 consecutive slides ({i+1}, {i+2}, {i+3}) use type '{t1}'.")

        if p1 and p1 == p2 == p3 and p1 not in ["", "plain_concept"]:
            deck_issues.append(f"Component repetition: 3 consecutive slides ({i+1}, {i+2}, {i+3}) repeat pattern '{p1}'.")

        # Flag 2 consecutive circle-pills
        if (p1 == "parallel_comparison" and p2 == "parallel_comparison"):
            deck_issues.append(f"Consecutive circle-pill comparison shapes on slides {i+1} and {i+2}.")

    # 3. Slide-Level Inspections
    for i, s in enumerate(slides):
        s_no = s.get("slide_no", i + 1)
        stype = s.get("type", "concept")
        vspec = s.get("visual_spec") or {}

        # Catches silent image failure: if marked IMAGE but image_bytes is None
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
                    add_issue(s_no, f"Step {st_idx+1} is severely underfit (only {title_len + detail_len} chars).")

        # Example check for concept slides
        if stype == "concept" and not s.get("example") and not s.get("body_bullets"):
            add_issue(s_no, "Concept slide has neither body bullets nor an illustrative example.")

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
            "has_example": bool(s.get("example")),
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
        critic_res = await router.generate_json(
            task="qa",
            messages=[
                {"role": "system", "content": REVIEWER_CRITIC_SYSTEM_PROMPT},
                {"role": "user", "content": f"Review this generated presentation outline against the pedagogical standard:\n{json.dumps(critic_prompt, indent=2)}"},
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

    # 3. Combine Pre-check flags and Critic flags (capped at max 2 repairs)
    repair_queue: Dict[int, tuple[List[str], str]] = {}

    # Add critic flagged slides (capped at max 2 targeted repairs)
    for f in flagged:
        if len(repair_queue) >= 2:
            break
        s_no = f.get("slide_no")
        if s_no:
            issue = f.get("issue", "Quality defect flagged by critic")
            directive = f.get("repair_directive", "")
            repair_queue[s_no] = ([issue], directive)

    # Add pre-check flagged slides if room
    for s_no, issues in slide_issues.items():
        if s_no not in repair_queue and len(repair_queue) < 2:
            repair_queue[s_no] = (issues, "Correct structural and layout bounds.")

    # 4. Execute Targeted Repairs (Strictly capped at 1 pass)
    if repair_queue:
        logger.info(f"[ReviewerAgent] Triggering targeted repairs for {len(repair_queue)} slide(s): {list(repair_queue.keys())}")
        repaired_slides = []
        for s in slides:
            s_no = s.get("slide_no")
            if s_no in repair_queue:
                issues, directive = repair_queue[s_no]
                try:
                    healed = await asyncio.wait_for(
                        repair_single_slide(s, issues, directive=directive),
                        timeout=12.0,
                    )
                    repaired_slides.append(healed)
                except (asyncio.TimeoutError, Exception) as e:
                    logger.warning(f"[ReviewerAgent] Repair for slide {s_no} failed ({e}) — keeping original.")
                    repaired_slides.append(s)
            else:
                repaired_slides.append(s)
        return repaired_slides

    return slides
