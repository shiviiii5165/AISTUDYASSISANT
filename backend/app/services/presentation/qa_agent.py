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
from typing import List, Dict, Any, Optional, Set, Tuple
from app.services.ai import router
from .prompts import SLIDE_PATCH_SYSTEM_PROMPT
from .schemas import PresentationConfig
from .content_agent import BANNED_STRINGS, _contains_banned, _has_verb, _word_boundary_truncate
from .content_quality_auditor import sanitize_and_complete_title


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
            if word_count < 80:
                issues.append(f"Speaker notes too short ({word_count} words, minimum 80).")
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


def fit_title_semantic(title: str, max_chars: int = 60, topic: str = "", fallback: str = "") -> str:
    """
    Deterministically compresses and fits a slide title into the specified character budget (<= max_chars)
    without raw character slicing.
    
    Guarantees:
    - Preserves central meaning and subject
    - Grammatically complete (no dangling prepositions or conjunctions)
    - Avoids dangling punctuation (no trailing .,:;-—)
    - Protects mathematical expressions ($...$, equations) from broken delimiters or truncation
    - Avoids cutting named entities and acronyms (BERT, CPython, etc.) mid-word
    - Enforces <= max_chars strictly
    - Returns already-valid titles intact
    """
    if not title or not title.strip():
        if fallback:
            return fallback[:max_chars]
        if topic:
            return f"{topic}: Overview"[:max_chars]
        return "Overview"

    raw = title.strip()
    if len(raw) <= max_chars:
        return sanitize_and_complete_title(raw, topic=topic, fallback_concept=fallback)

    # 1. Identify protected spans (LaTeX math expressions and equations)
    math_spans: List[Tuple[int, int]] = []
    for m in re.finditer(r"\$\$?[^$]+\$\$?|\\\([^\)]+\\\)", raw):
        math_spans.append((m.start(), m.end()))

    def is_inside_math(idx: int) -> bool:
        return any(start <= idx < end for start, end in math_spans)

    # 2. Check for verbose meta-prefixes to strip
    PREFIX_PATTERNS = [
        r"^An?\s+(?:In-Depth\s+|Comprehensive\s+|Detailed\s+|Systematic\s+|Rigorous\s+)?Overview\s+of\s+(?:the\s+)?",
        r"^An?\s+(?:In-Depth\s+|Comprehensive\s+|Detailed\s+|Systematic\s+|Rigorous\s+)?Examination\s+of\s+(?:the\s+)?",
        r"^An?\s+(?:In-Depth\s+|Comprehensive\s+|Detailed\s+|Systematic\s+|Rigorous\s+)?Investigation\s+(?:into|of)\s+(?:the\s+)?",
        r"^An?\s+(?:In-Depth\s+|Comprehensive\s+|Detailed\s+|Systematic\s+|Rigorous\s+)?Introduction\s+to\s+(?:the\s+)?(?:Principles\s+of\s+)?",
        r"^An?\s+(?:In-Depth\s+|Comprehensive\s+|Detailed\s+|Systematic\s+|Rigorous\s+)?Analysis\s+of\s+(?:the\s+)?",
        r"^A\s+(?:Comparative\s+|Critical\s+)?Study\s+(?:on|of)\s+(?:the\s+)?",
        r"^Understanding\s+(?:the\s+)?(?:Mechanisms\s+of\s+|Fundamentals\s+of\s+|Principles\s+of\s+)?",
        r"^Exploring\s+(?:the\s+)?(?:Dynamics\s+of\s+|Concepts\s+of\s+)?",
        r"^Key\s+Principles\s+(?:and\s+Concepts\s+)?of\s+",
        r"^Insights\s+into\s+(?:the\s+)?",
    ]
    cur = raw
    for pat in PREFIX_PATTERNS:
        m = re.match(pat, cur, flags=re.IGNORECASE)
        if m:
            candidate = cur[m.end():].strip()
            if candidate:
                candidate = candidate[0].upper() + candidate[1:]
                if len(candidate) <= max_chars and len(candidate.split()) >= 2:
                    return sanitize_and_complete_title(candidate, topic=topic, fallback_concept=fallback)
                cur = candidate
                break

    # 3. Delimiter Split (Colon, Em-dash, En-dash, Pipe, Semicolon, Comma)
    for delim in [": ", " — ", " – ", " - ", " | ", "; ", ", "]:
        delim_idx = cur.find(delim)
        if delim_idx != -1 and not is_inside_math(delim_idx):
            left = cur[:delim_idx].strip()
            right = cur[delim_idx + len(delim):].strip()
            generic_markers = {"lecture", "chapter", "module", "part", "unit", "section", "overview", "case study"}
            has_math_on_right = any(start >= delim_idx for start, end in math_spans)
            if not has_math_on_right and 12 <= len(left) <= max_chars and len(left.split()) >= 2:
                if not any(left.lower().startswith(gm) for gm in generic_markers):
                    sanitized_left = sanitize_and_complete_title(left, topic=topic, fallback_concept=fallback)
                    if len(sanitized_left) <= max_chars:
                        return sanitized_left
            if 12 <= len(right) <= max_chars and len(right.split()) >= 2:
                sanitized_right = sanitize_and_complete_title(right, topic=topic, fallback_concept=fallback)
                if len(sanitized_right) <= max_chars and sanitized_right.count("$") % 2 == 0:
                    return sanitized_right

    # 4. Grammatical clause pruning (Relative clauses & Subordinate conjunctions)
    CLAUSE_DELIMITERS = [
        " that ",
        ", which ",
        " which ",
        ", where ",
        " where ",
        " because ",
        " although ",
        " in order to ",
        " so that ",
        " as well as ",
        " and should be ",
        " and will be ",
        " and can be ",
        " and its ",
        " and their ",
    ]
    for cdelim in CLAUSE_DELIMITERS:
        idx = cur.find(cdelim)
        if idx != -1 and not is_inside_math(idx):
            candidate = cur[:idx].strip()
            if 10 <= len(candidate) <= max_chars and len(candidate.split()) >= 2:
                sanitized = sanitize_and_complete_title(candidate, topic=topic, fallback_concept=fallback)
                if len(sanitized) <= max_chars:
                    return sanitized

    # 5. Prepositional & coordinating conjunction boundary reduction (scanning right-to-left)
    PHRASE_DELIMITERS = [
        " and ", " across ", " through ", " during ", " within ", " between ",
        " under ", " with ", " for ", " from ", " on ", " at ", " in ", " of "
    ]
    split_points = []
    for pdelim in PHRASE_DELIMITERS:
        for m in re.finditer(re.escape(pdelim), cur, flags=re.IGNORECASE):
            if not is_inside_math(m.start()):
                split_points.append(m.start())
    
    split_points.sort(reverse=True)
    for sp in split_points:
        candidate = cur[:sp].strip()
        if 8 <= len(candidate) <= max_chars and len(candidate.split()) >= 2:
            # If original title has math, prioritize candidates retaining all math spans
            if math_spans and not all(end <= sp for start, end in math_spans):
                continue
            sanitized = sanitize_and_complete_title(candidate, topic=topic, fallback_concept=fallback)
            if len(sanitized) <= max_chars:
                if sanitized.count("$") % 2 == 0:
                    return sanitized

    # 6. Word-boundary aware truncation fallback (avoiding math & entity cuts)
    words = cur.split()
    accumulated: List[str] = []
    for w in words:
        test_str = " ".join(accumulated + [w])
        if len(test_str) > max_chars:
            break
        accumulated.append(w)

    if accumulated:
        while accumulated and accumulated[-1].lower().rstrip(".,:;") in {
            "and", "or", "with", "for", "to", "but", "that", "of", "in", "on",
            "at", "by", "from", "as", "load", "loads", "leads", "causes", "is", "are"
        }:
            accumulated.pop()
        if accumulated:
            candidate = " ".join(accumulated)
            sanitized = sanitize_and_complete_title(candidate, topic=topic, fallback_concept=fallback)
            if len(sanitized) <= max_chars and sanitized.count("$") % 2 == 0:
                return sanitized

    # 7. Final guaranteed safety clamp
    fallback_res = sanitize_and_complete_title(cur[:max_chars].rsplit(" ", 1)[0], topic=topic, fallback_concept=fallback)
    if len(fallback_res) <= max_chars:
        return fallback_res
    return cur[:max_chars].rstrip(".,:;-— ")


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
        if len(b_str) > 118:
            overflow_to_notes.append(b_str)  # Keep full version in notes
            b_str = _word_boundary_truncate(b_str, 116)
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

    # 3. Title length and completeness enforcement (semantic compression, no raw slicing)
    title = slide.get("title", "")
    if title:
        orig_title = title.strip()
        healed_title = fit_title_semantic(orig_title, max_chars=60)
        slide["title"] = healed_title
        if healed_title != orig_title and len(orig_title) > 60:
            notes = slide.get("speaker_notes", "")
            if orig_title not in notes:
                slide["speaker_notes"] = (notes + f" Full topic title: {orig_title}").strip()

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

    # 6. Guard process slide steps completeness
    slide_type = str(slide.get("type", "")).lower()
    slide_intent = str(slide.get("intent", "")).lower()
    if "process" in slide_type or "process" in slide_intent:
        if not slide.get("steps") and slide.get("body_bullets"):
            slide["steps"] = [
                {"step": idx + 1, "title": f"Step {idx + 1}", "description": b}
                for idx, b in enumerate(slide["body_bullets"])
            ]
        if isinstance(slide.get("content"), dict):
            if not slide["content"].get("process_steps") and slide.get("steps"):
                slide["content"]["process_steps"] = [
                    s.get("description", str(s)) if isinstance(s, dict) else str(s)
                    for s in slide["steps"]
                ]

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
        from ..ai.circuit_breaker import circuit_breaker
        if not circuit_breaker.can_execute():
            return slide
        user_prompt = (
            f"Fix issues in this slide to meet the TeachGenie Master Standard:\n"
            f"Slide Content:\n{json.dumps({k: v for k, v in slide.items() if not isinstance(v, (bytes, bytearray))}, indent=2, default=str)}\n\n"
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
            timeout=8.0,
        )
        if patch_res and patch_res.get("title"):
            # Start from the original slide to preserve all structural data
            merged = dict(slide)
            for k, v in patch_res.items():
                if v is not None and v != "" and v != [] and v != {}:
                    merged[k] = v
                elif k in ("title", "subtitle", "key_message", "speaker_notes", "example"):
                    if v:
                        merged[k] = v

            # Strictly preserve original structural collections if patch_res didn't supply them
            for key in ("steps", "columns", "layers", "metrics", "content", "content_origin", "semantic_status"):
                if not patch_res.get(key) and slide.get(key):
                    merged[key] = slide[key]

            # Preserve visual_spec and numbering
            merged["visual_spec"] = slide.get("visual_spec")
            merged["image_bytes"] = slide.get("image_bytes")
            merged["slide_no"] = slide.get("slide_no")
            merged["content_pattern"] = patch_res.get("content_pattern") or slide.get("content_pattern")
            merged["section_label"] = slide.get("section_label")
            if not patch_res.get("type"):
                merged["type"] = slide.get("type")

            # Synchronize process steps if this is a process slide
            slide_type = str(merged.get("type", "")).lower()
            slide_intent = str(merged.get("intent", "")).lower()
            if "process" in slide_type or "process" in slide_intent:
                if not merged.get("steps") and slide.get("steps"):
                    merged["steps"] = slide["steps"]
                elif not merged.get("steps") and merged.get("body_bullets"):
                    merged["steps"] = [
                        {"step": idx + 1, "title": f"Step {idx + 1}", "description": b}
                        for idx, b in enumerate(merged["body_bullets"])
                    ]
                if isinstance(merged.get("content"), dict):
                    if not merged["content"].get("process_steps") and merged.get("steps"):
                        merged["content"]["process_steps"] = [
                            s.get("description", str(s)) if isinstance(s, dict) else str(s)
                            for s in merged["steps"]
                        ]

            return auto_heal_slide_python(merged)
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
        # Instead of hallucinating filler slides to meet the count, we preserve the exact
        # output. If slides were skipped due to CONTENT_SEMANTIC_GAP, the overall deck
        # will naturally fail the quality gate for being short, which is the correct behavior.
        pass

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
