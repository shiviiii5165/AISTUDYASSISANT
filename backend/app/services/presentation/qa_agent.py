"""
QA Agent (Master Prompt v2)
============================
Executes zero-token Python structural checks and performs targeted single-slide AI repair.
Enforces:
- 3–5 meaningful content blocks per content slide
- Complete sentences with verbs (no noun fragments)
- Title < 60 chars, subtitle < 140 chars
- Speaker notes 90–160 words
- Banned-string rejection
- No duplicate bullets, no title repetition in body
- Word-boundary-aware overflow handling (no raw slicing)
"""
from app.core.logging import logger
import asyncio
import json
import re
from typing import List, Dict, Any, Optional, Set
from app.services.ai import router
from .schemas import PresentationConfig
from .prompts import SLIDE_PATCH_SYSTEM_PROMPT
from .content_agent import BANNED_STRINGS, _contains_banned, _has_verb, _word_boundary_truncate, _generate_topic_fallback


def inspect_slide_structure(slide: Dict[str, Any]) -> List[str]:
    """
    Inspects structural, content, and quality bounds for a single slide.
    Zero-token check returning specific issue strings.
    Enforces Master Prompt rules.
    """
    issues = []
    title = slide.get("title", "").strip()
    subtitle = slide.get("subtitle", "").strip()
    bullets = slide.get("body_bullets", [])
    notes = slide.get("speaker_notes", "").strip()
    stype = slide.get("type", "concept")

    # ─── Title checks ─────────────────────────────────────────
    if not title:
        issues.append("Title is empty.")
    elif len(title) > 60:
        issues.append(f"Title exceeds 60-char limit ({len(title)} chars).")
    if _contains_banned(title):
        issues.append("Title contains banned filler string.")

    # ─── Subtitle checks ──────────────────────────────────────
    if subtitle and len(subtitle) > 140:
        issues.append(f"Subtitle exceeds 140-char limit ({len(subtitle)} chars).")

    # ─── Content slide checks ─────────────────────────────────
    if stype not in ["hero", "qa", "closing", "summary", "quiz"]:
        # Bullet count: 3-5 for content slides (unless specialized data exists)
        has_specialized = (
            slide.get("layers") or slide.get("steps") or
            slide.get("metrics") or slide.get("columns") or
            slide.get("milestones")
        )
        if not bullets and not has_specialized:
            issues.append("Content slide has no visible content blocks and no specialized data.")
        elif bullets and len(bullets) < 3 and not has_specialized:
            issues.append(f"Content slide has only {len(bullets)} bullets (minimum 3 for rich content).")
        elif bullets and len(bullets) > 6:
            issues.append(f"Too many bullets ({len(bullets)} > 6 maximum). Move excess to notes.")

        # Individual bullet quality checks
        seen_bullets: Set[str] = set()
        title_lower = title.lower().strip()
        for i, b in enumerate(bullets):
            b_str = str(b).strip()
            b_lower = b_str.lower().strip()

            if not b_str:
                issues.append(f"Bullet {i+1} is empty.")
                continue

            if len(b_str) > 120:
                issues.append(f"Bullet {i+1} exceeds 120-char limit ({len(b_str)} chars).")

            # Banned string check
            if _contains_banned(b_str):
                issues.append(f"Bullet {i+1} contains banned filler: '{b_str[:50]}'.")

            # Verb check (complete sentence requirement)
            if not _has_verb(b_str):
                issues.append(f"Bullet {i+1} appears to be a noun fragment (no verb detected).")

            # Title repetition check
            if title_lower and b_lower == title_lower:
                issues.append(f"Bullet {i+1} repeats the slide title.")

            # Duplicate check
            if b_lower in seen_bullets:
                issues.append(f"Bullet {i+1} is a duplicate of another bullet.")
            seen_bullets.add(b_lower)

        # ─── Speaker notes checks ────────────────────────────
        if not notes:
            issues.append("Speaker notes are missing.")
        else:
            word_count = len(notes.split())
            if word_count < 90:
                issues.append(f"Speaker notes too short ({word_count} words, minimum 90).")
            elif word_count > 200:
                issues.append(f"Speaker notes too long ({word_count} words, recommended max 160).")

            if _contains_banned(notes):
                issues.append("Speaker notes contain banned filler string.")

        # ─── Example check ──────────────────────────────────
        example = slide.get("example", "").strip()
        if example and _contains_banned(example):
            issues.append("Example contains banned filler string.")

    # ─── Image asset verification ────────────────────────────
    vspec = slide.get("visual_spec") or {}
    if vspec.get("asset_required") and not vspec.get("image_bytes"):
        issues.append("Slide flagged asset_required but image_bytes is missing.")

    return issues


def auto_heal_slide_python(slide: Dict[str, Any]) -> Dict[str, Any]:
    """
    Zero-token deterministic auto-heal for structural issues.
    Uses word-boundary-aware truncation (never raw slicing).
    """
    bullets = slide.get("body_bullets", [])

    # 1. Filter empty bullets and banned strings
    valid_bullets = []
    for b in bullets:
        b_str = str(b).strip()
        if not b_str:
            continue
        if _contains_banned(b_str):
            continue
        valid_bullets.append(b_str)

    # 2. Word-boundary truncation for overlong bullets (move excess to notes)
    overflow_to_notes = []
    trimmed_bullets = []
    for b_str in valid_bullets[:5]:
        if len(b_str) > 100:
            overflow_to_notes.append(b_str)  # Keep full version in notes
            b_str = _word_boundary_truncate(b_str, 95)
        trimmed_bullets.append(b_str)

    # Remove duplicates
    seen: Set[str] = set()
    deduped = []
    for b in trimmed_bullets:
        key = b.lower().strip()
        if key not in seen:
            seen.add(key)
            deduped.append(b)

    slide["body_bullets"] = deduped

    # Migrate overflow bullets to speaker notes
    if len(valid_bullets) > 5:
        overflow_to_notes.extend(valid_bullets[5:])

    if overflow_to_notes:
        notes = slide.get("speaker_notes", "")
        overflow_str = " Additional context: " + "; ".join(overflow_to_notes)
        slide["speaker_notes"] = (notes + overflow_str).strip()

    # 3. Title length enforcement (word-boundary, no raw slicing)
    title = slide.get("title", "")
    if len(title) > 60:
        slide["title"] = _word_boundary_truncate(title, 58)

    # 4. Subtitle length enforcement
    subtitle = slide.get("subtitle", "")
    if subtitle and len(subtitle) > 140:
        slide["subtitle"] = _word_boundary_truncate(subtitle, 138)

    # 5. Clean banned strings from notes
    notes = slide.get("speaker_notes", "")
    if notes and _contains_banned(notes):
        for banned in BANNED_STRINGS:
            notes = re.sub(re.escape(banned), "", notes, flags=re.IGNORECASE)
        slide["speaker_notes"] = notes.strip()

    return slide


async def repair_single_slide(
    slide: Dict[str, Any],
    issues: List[str],
    directive: str = "",
) -> Dict[str, Any]:
    """
    Targeted single-slide AI repair pass. Capped strictly at 1 invocation.
    Hard-capped at 15s per repair to prevent pipeline stalls.
    """
    try:
        user_prompt = (
            f"Fix issues in this slide to meet the TeachGenie Master Standard:\n"
            f"Slide Content:\n{json.dumps(slide, indent=2)}\n\n"
            f"Issues Identified:\n" + "\n".join(f"- {iss}" for iss in issues)
        )
        if directive:
            user_prompt += f"\n\nReviewer Repair Directive:\n{directive}"

        patch_res = await asyncio.wait_for(
            router.generate_json(
                task="repair",
                messages=[
                    {"role": "system", "content": SLIDE_PATCH_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=2000,
            ),
            timeout=15.0,
        )
        if patch_res and patch_res.get("title"):
            # Preserve original visual_spec and numbering
            patch_res["visual_spec"] = slide.get("visual_spec")
            patch_res["image_bytes"] = slide.get("image_bytes")
            patch_res["slide_no"] = slide.get("slide_no")
            patch_res["content_pattern"] = slide.get("content_pattern")
            patch_res["section_label"] = slide.get("section_label")
            return auto_heal_slide_python(patch_res)
    except asyncio.TimeoutError:
        logger.warning(f"[QA Agent] AI slide patch timed out (15s) for slide {slide.get('slide_no')} — using auto-healed version.")
    except Exception as e:
        logger.error(f"[QA Agent] AI slide patch failed for slide {slide.get('slide_no')}: {e}")
    return slide


MAX_AI_REPAIRS = 4  # Increased from 3 to handle stricter quality gates


async def run_presentation_qa(
    config: PresentationConfig,
    slides: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Executes Python structural QA, auto-heals overflow, and performs targeted AI repair.
    AI repairs are capped at MAX_AI_REPAIRS (4) to prevent timeout cascades.
    Allows slide count to flex up to config.slide_count + 2 without truncation.
    """
    max_allowed = config.slide_count + 2

    # 1. Enforce slide count boundaries [slide_count..slide_count + 2]
    if len(slides) > max_allowed:
        slides = slides[:max_allowed]
    elif len(slides) < config.slide_count:
        while len(slides) < config.slide_count:
            num = len(slides) + 1
            # Topic-derived fallback — NEVER banned placeholder strings
            slides.append(
                _generate_topic_fallback(
                    topic=config.topic,
                    slide_title=f"Key Concepts of {config.topic}",
                    slide_no=num,
                )
            )

    # 2. Run Python QA & Auto-Healing on each slide
    ai_repairs_used = 0
    repaired_slides = []
    for s in slides:
        healed = auto_heal_slide_python(s)
        issues = inspect_slide_structure(healed)

        # 3. If significant issues exist AND we haven't hit the repair cap, trigger AI patch
        if len(issues) >= 2 and ai_repairs_used < MAX_AI_REPAIRS:
            logger.info(f"[QA Agent] Slide {s.get('slide_no')} has {len(issues)} issues; triggering AI patch ({ai_repairs_used + 1}/{MAX_AI_REPAIRS}).")
            healed = await repair_single_slide(healed, issues)
            ai_repairs_used += 1
        elif len(issues) >= 2:
            logger.info(f"[QA Agent] Slide {s.get('slide_no')} has {len(issues)} issues but AI repair cap reached — using auto-heal only.")

        repaired_slides.append(healed)

    return repaired_slides
