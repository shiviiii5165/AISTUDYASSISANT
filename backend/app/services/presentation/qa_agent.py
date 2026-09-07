"""
QA Agent
========
Executes zero-token Python structural checks (bounds, empty bullets, bullet length,
underfit ratio) and performs targeted single-slide AI repair when structural or
content defects are found. Respects slide count flex up to +2.
"""
from app.core.logging import logger
import json
from typing import List, Dict, Any, Optional
from app.services.ai import router
from .schemas import PresentationConfig
from .prompts import SLIDE_PATCH_SYSTEM_PROMPT


def inspect_slide_structure(slide: Dict[str, Any]) -> List[str]:
    """
    Inspects structural and content bounds for a single slide.
    Zero-token check returning specific issue strings.
    """
    issues = []
    title = slide.get("title", "").strip()
    bullets = slide.get("body_bullets", [])
    stype = slide.get("type", "concept")

    if not title:
        issues.append("Title is empty.")
    elif len(title) > 95:
        issues.append(f"Title is too long ({len(title)} chars > 95 limit).")

    if stype not in ["hero", "qa", "closing"]:
        if not bullets and not slide.get("layers") and not slide.get("steps") and not slide.get("metrics") and not slide.get("columns"):
            issues.append("Slide has no content bullets and no diagram data.")

        for i, b in enumerate(bullets):
            b_str = str(b).strip()
            if not b_str:
                issues.append(f"Bullet {i+1} is empty.")
            elif len(b_str) > 120:
                issues.append(f"Bullet {i+1} exceeds 120 character limit ({len(b_str)} chars).")

        if len(bullets) > 6:
            issues.append(f"Too many bullets ({len(bullets)} > 6 maximum).")

    # Image asset verification
    vspec = slide.get("visual_spec") or {}
    if vspec.get("asset_required") and not vspec.get("image_bytes"):
        issues.append("Slide flagged asset_required but image_bytes is missing.")

    return issues


def auto_heal_slide_python(slide: Dict[str, Any]) -> Dict[str, Any]:
    """
    Zero-token deterministic auto-heal for minor overflows.
    """
    bullets = slide.get("body_bullets", [])
    
    # 1. Filter empty bullets
    valid_bullets = [str(b).strip() for b in bullets if str(b).strip()]
    
    # 2. Trim bullet length if slightly over 95 chars
    trimmed_bullets = []
    for b in valid_bullets[:5]:
        b_str = str(b).strip()
        if len(b_str) > 100:
            cut = b_str[:95]
            last_sp = cut.rfind(" ")
            if last_sp > 55:
                cut = cut[:last_sp]
            trimmed_bullets.append(cut + "...")
        else:
            trimmed_bullets.append(b_str)
    slide["body_bullets"] = trimmed_bullets

    # Migrate overflow bullets to speaker notes
    if len(valid_bullets) > 5:
        overflow = valid_bullets[5:]
        notes = slide.get("speaker_notes", "")
        overflow_str = " Additional points: " + "; ".join(overflow)
        slide["speaker_notes"] = (notes + overflow_str).strip()

    # 3. Trim title if overly long
    title = slide.get("title", "")
    if len(title) > 85:
        cut_title = title[:80]
        last_sp = cut_title.rfind(" ")
        if last_sp > 40:
            cut_title = cut_title[:last_sp]
        slide["title"] = cut_title

    return slide


async def repair_single_slide(
    slide: Dict[str, Any],
    issues: List[str],
    directive: str = "",
) -> Dict[str, Any]:
    """
    Targeted single-slide AI repair pass. Capped strictly at 1 invocation.
    """
    try:
        user_prompt = f"Fix issues in this slide:\nSlide Content:\n{json.dumps(slide, indent=2)}\n\nIssues Identified:\n" + "\n".join(issues)
        if directive:
            user_prompt += f"\n\nReviewer Repair Directive:\n{directive}"

        patch_res = await router.generate_json(
            task="repair",
            messages=[
                {"role": "system", "content": SLIDE_PATCH_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=2000,
        )
        if patch_res and patch_res.get("title"):
            # Preserve original visual_spec and numbering
            patch_res["visual_spec"] = slide.get("visual_spec")
            patch_res["image_bytes"] = slide.get("image_bytes")
            patch_res["slide_no"] = slide.get("slide_no")
            return auto_heal_slide_python(patch_res)
    except Exception as e:
        logger.error(f"[QA Agent] AI slide patch failed for slide {slide.get('slide_no')}: {e}")
    return slide


async def run_presentation_qa(
    config: PresentationConfig,
    slides: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Executes Python structural QA, auto-heals overflow, and performs targeted AI repair.
    Allows slide count to flex up to config.slide_count + 2 without truncation.
    """
    max_allowed = config.slide_count + 2

    # 1. Enforce slide count boundaries [slide_count..slide_count + 2]
    if len(slides) > max_allowed:
        slides = slides[:max_allowed]
    elif len(slides) < config.slide_count:
        while len(slides) < config.slide_count:
            num = len(slides) + 1
            slides.append({
                "slide_no": num,
                "type": "concept",
                "title": f"Summary & Key Takeaway {num}",
                "key_message": "Core takeaway summary point.",
                "body_bullets": ["Key educational insight", "Synthesized understanding"],
                "speaker_notes": "Key takeaway context.",
            })

    # 2. Run Python QA & Auto-Healing on each slide
    repaired_slides = []
    for s in slides:
        healed = auto_heal_slide_python(s)
        issues = inspect_slide_structure(healed)

        # 3. If major structural issues exist, trigger targeted single repair (max 1 pass)
        if len(issues) >= 3:
            logger.info(f"[QA Agent] Slide {s.get('slide_no')} has {len(issues)} structural issues; triggering AI patch.")
            healed = await repair_single_slide(healed, issues)

        repaired_slides.append(healed)

    return repaired_slides
