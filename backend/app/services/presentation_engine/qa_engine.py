"""
TeachGenie — QA Engine
=======================
Slide and deck-level quality assessment.
Evaluates density, balance, and readability.
"""
from typing import List
from . import SlideContent, SlideQAResult, DensityLevel


def evaluate_slide_density(content: SlideContent, slide_index: int = 0) -> SlideQAResult:
    """Score a single slide's information density."""
    issues = []

    # Word count across all text fields
    all_text = " ".join([
        content.title or "",
        content.subtitle or "",
        " ".join(content.body_bullets),
        content.example or "",
        content.key_insight or "",
        content.body_text or "",
    ])
    word_count = len(all_text.split())
    bullet_count = len(content.body_bullets)

    # Density scoring
    if word_count > 200:
        density = DensityLevel.CRITICAL
        issues.append(f"Too many words ({word_count}). Split or compress content.")
    elif word_count > 130:
        density = DensityLevel.HIGH
        issues.append(f"High word count ({word_count}). Consider shortening.")
    elif word_count > 60:
        density = DensityLevel.MEDIUM
    else:
        density = DensityLevel.LOW

    # Bullet count check
    if bullet_count > 7:
        density = DensityLevel.CRITICAL
        issues.append(f"Too many bullets ({bullet_count}). Max recommended: 6.")
    elif bullet_count > 5:
        if density != DensityLevel.CRITICAL:
            density = DensityLevel.HIGH
        issues.append(f"Many bullets ({bullet_count}). Consider grouping.")

    # Long bullet check
    for i, b in enumerate(content.body_bullets):
        if len(b) > 120:
            issues.append(f"Bullet {i+1} is too long ({len(b)} chars). Shorten to ~80 chars.")

    # Title check using TextFitter
    from .tokens import Typography, CONTENT_WIDTH, ZONE_TITLE_HEIGHT
    from .text_fitter import estimate_text_height
    
    if content.title:
        # Check title height using actual layout constraints
        title_h = estimate_text_height(content.title, Typography.SLIDE_TITLE, CONTENT_WIDTH)
        if title_h.inches > ZONE_TITLE_HEIGHT.inches:
            issues.append(f"Title is too long and will wrap/shrink to fit. Consider shortening.")
            
        if len(content.title) > 80:
             issues.append("Title exceeds recommended 80 characters.")

    passed = density in (DensityLevel.LOW, DensityLevel.MEDIUM)

    return SlideQAResult(
        slide_index=slide_index,
        density=density,
        word_count=word_count,
        bullet_count=bullet_count,
        issues=issues,
        passed=passed,
    )


def auto_compress_slide(content: SlideContent) -> SlideContent:
    """
    Automatically compress over-dense slide content.
    Shortens bullets, trims example, moves excess to speaker notes.
    """
    qa = evaluate_slide_density(content)

    if qa.density not in (DensityLevel.HIGH, DensityLevel.CRITICAL):
        return content  # No change needed

    # 1. Trim bullets to max 5
    if len(content.body_bullets) > 5:
        # Move excess to speaker notes
        excess = content.body_bullets[5:]
        extra_notes = "\n\nAdditional points to mention:\n" + "\n".join(f"• {b}" for b in excess)
        content.body_bullets = content.body_bullets[:5]
        content.speaker_note = (content.speaker_note or "") + extra_notes

    # 2. Shorten long bullets
    shortened = []
    for b in content.body_bullets:
        if len(b) > 100:
            # Truncate at sentence boundary or word boundary
            truncated = b[:95]
            last_space = truncated.rfind(' ')
            if last_space > 60:
                truncated = truncated[:last_space]
            shortened.append(truncated)
        else:
            shortened.append(b)
    content.body_bullets = shortened

    # 3. Shorten title if needed
    if content.title and len(content.title) > 70:
        # Try to shorten at a natural break
        t = content.title[:65]
        last_space = t.rfind(' ')
        if last_space > 40:
            content.title = t[:last_space]

    return content


def evaluate_deck_quality(slides: List[SlideContent]) -> dict:
    """Evaluate overall deck quality."""
    results = [evaluate_slide_density(s, i) for i, s in enumerate(slides)]

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    critical = sum(1 for r in results if r.density == DensityLevel.CRITICAL)

    # Layout variety check
    purposes = [s.purpose for s in slides]
    unique_purposes = len(set(purposes))
    variety_score = min(100, (unique_purposes / max(total - 2, 1)) * 100)  # exclude cover/closing

    return {
        "total_slides": total,
        "passed": passed,
        "failed": total - passed,
        "critical": critical,
        "variety_score": round(variety_score),
        "slide_results": results,
    }
