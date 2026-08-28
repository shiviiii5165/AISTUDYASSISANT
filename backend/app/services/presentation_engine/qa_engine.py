"""
TeachGenie — QA Engine
=======================
Slide and deck-level quality assessment.
Evaluates density, balance, contrast, and readability.
"""
from typing import List, Tuple
from pptx.dml.color import RGBColor
from . import SlideContent, SlideQAResult, DensityLevel, SlidePurpose, ThemeColors


# ═══════════════════════════════════════════════════════════════════════════
# CONTRAST UTILITIES (WCAG 2.1)
# ═══════════════════════════════════════════════════════════════════════════

def _relative_luminance(c: RGBColor) -> float:
    """Compute WCAG 2.1 relative luminance from an RGBColor."""
    def _linearize(v: int) -> float:
        s = v / 255.0
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b = _linearize(c[0]), _linearize(c[1]), _linearize(c[2])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: RGBColor, bg: RGBColor) -> float:
    """Return the WCAG contrast ratio between two colors (≥ 1.0)."""
    l1 = _relative_luminance(fg)
    l2 = _relative_luminance(bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# Minimum contrast ratios (WCAG AA)
MIN_CONTRAST_LARGE_TEXT = 3.0   # ≥ 18pt or 14pt bold
MIN_CONTRAST_NORMAL_TEXT = 4.5


def check_slide_contrast(
    content: SlideContent,
    theme: ThemeColors,
) -> List[str]:
    """
    Check known text/background color pairings for a slide against the theme.
    Returns a list of contrast issue descriptions (empty = all good).
    """
    issues: List[str] = []

    # Build the pairs we know each slide type uses
    pairs: List[Tuple[str, RGBColor, RGBColor, bool]] = []  # (label, fg, bg, is_large)

    if content.purpose in (SlidePurpose.COVER, SlidePurpose.CLOSING):
        # These use dark_bg as background
        bg = theme.dark_bg
        pairs.append(("title text on dark bg", theme.text_on_dark, bg, True))
        pairs.append(("muted text on dark bg", theme.text_muted, bg, False))
        pairs.append(("body text on dark surface", theme.text_on_dark, theme.dark_surface, False))
    else:
        # Normal content slides use theme.background
        bg = theme.background
        pairs.append(("body text on background", theme.text, bg, False))
        pairs.append(("muted text on background", theme.text_muted, bg, False))
        pairs.append(("title on background", theme.text, bg, True))

    for label, fg, slide_bg, is_large in pairs:
        ratio = contrast_ratio(fg, slide_bg)
        threshold = MIN_CONTRAST_LARGE_TEXT if is_large else MIN_CONTRAST_NORMAL_TEXT
        if ratio < threshold:
            issues.append(
                f"Low contrast: {label} — ratio {ratio:.2f}:1 "
                f"(minimum {threshold:.1f}:1 required)"
            )

    return issues


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


def evaluate_deck_quality(
    slides: List[SlideContent],
    theme: ThemeColors = None,
) -> dict:
    """Evaluate overall deck quality (density + contrast)."""
    results = [evaluate_slide_density(s, i) for i, s in enumerate(slides)]

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    critical = sum(1 for r in results if r.density == DensityLevel.CRITICAL)

    # Contrast checks (when theme is available)
    contrast_issues: List[str] = []
    if theme:
        for i, s in enumerate(slides):
            slide_issues = check_slide_contrast(s, theme)
            for issue in slide_issues:
                contrast_issues.append(f"Slide {i+1} ({s.purpose.value}): {issue}")
                critical += 1

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
        "contrast_issues": contrast_issues,
    }

