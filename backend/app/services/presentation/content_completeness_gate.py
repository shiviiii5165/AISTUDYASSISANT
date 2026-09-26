"""
TeachGenie Presentation Engine — Content Completeness Gate
===========================================================
Pre-export semantic and structural completeness validation.
Validates slides against learning objectives and structural contracts
before serialization into PPTX shapes.
"""
import re
import logging
from typing import Dict, Any, List, Optional, Tuple, Set

logger = logging.getLogger("teachgenie.presentation.content_completeness_gate")

DANGLING_END_WORDS = {
    "and", "or", "but", "nor", "so", "yet", "for", "with", "to", "of",
    "in", "on", "at", "by", "from", "as", "into", "through", "between",
    "under", "over", "about", "that", "which", "who", "whom", "whose",
    "is", "are", "was", "were", "has", "have",
    "a", "an", "the"
}

DANGLING_END_PAIRS = {
    "that causes", "which causes", "that results", "which results", "leads to",
    "into a", "into the", "in a", "in the", "to a", "to the", "of a", "of the",
    "for a", "for the", "with a", "with the", "by a", "by the", "from a", "from the"
}

GENERIC_COMPARAND_NAMES = {
    "option 1", "option 2", "option a", "option b",
    "approach a", "approach b", "concept a", "concept b",
    "alternative concept", "alternative approach"
}


GENERIC_FILLER_PATTERNS = [
    r"^overview of \w+",
    r"^key principles?$",
    r"^important aspects?$",
    r"^general details?$",
    r"^important factors?( to consider)?$",
    r"^introduction to \w+",
    r"^main points?$",
    r"^concept \w+$",
    r"^subsystem layer$",
    r"^operational subsystem$",
    r"^core operational aspect$",
    r"^foundational principle$",
    r"^summary of findings$",
    r"^component \d+$",
]


def is_generic_filler(text: str) -> bool:
    """Return True if text is a generic, low-information template placeholder."""
    if not text or not text.strip():
        return True
    t_clean = text.strip().lower().rstrip(".:;,!?")
    if t_clean in GENERIC_COMPARAND_NAMES:
        return True
    if len(t_clean.split()) < 3 and not (":" in text and len(text.split()) >= 4):
        return True
    for pat in GENERIC_FILLER_PATTERNS:
        if re.search(pat, t_clean):
            return True
    return False


def is_semantically_complete_point(text: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a bullet point or text item is semantically complete.
    A complete point has sufficient length (>= 5 words), subject + predicate / active verb,
    does not end in dangling words, and is not generic filler.
    """
    if not text or not text.strip():
        return False, "Empty point"
    cleaned = text.strip()
    words = cleaned.split()
    if len(words) < 5:
        return False, f"Point too short ({len(words)} words; expected at least 5)"
    if is_generic_filler(cleaned):
        return False, f"Generic filler placeholder: '{cleaned}'"
    dangling_err = check_sentence_completeness(cleaned)
    if dangling_err:
        return False, dangling_err
    return True, None


def check_sentence_completeness(text: str) -> Optional[str]:
    """Return error message if text terminates in an incomplete or dangling word/phrase."""
    if not text or not text.strip():
        return None
    cleaned = text.strip().rstrip(".,:;!?\"'()[]{}")
    words = cleaned.split()
    if not words:
        return None
    if len(words) >= 2:
        last_two = f"{words[-2].lower()} {words[-1].lower()}"
        if last_two in DANGLING_END_PAIRS:
            return f"Terminates in dangling phrase '{last_two}'"
    last_word = words[-1].lower()
    if last_word in DANGLING_END_WORDS:
        return f"Terminates in dangling conjunction/preposition '{last_word}'"
    return None


def validate_comparison_slide(slide_dict: Dict[str, Any]) -> List[str]:
    """Validate comparison slide completeness."""
    errors = []
    columns = slide_dict.get("columns", [])
    content_obj = slide_dict.get("content", {})
    comp_rows = content_obj.get("comparison_rows", []) if isinstance(content_obj, dict) else []

    if not columns and not comp_rows:
        errors.append("CONTENT_INSUFFICIENT: Comparison slide has no comparison columns or rows")
        return errors

    headings = []
    if columns:
        for c in columns:
            h = (c.get("heading") or c.get("header") or c.get("title") or "").strip()
            headings.append(h)
    elif comp_rows:
        headings = [
            (content_obj.get("comparison_target_a") or "").strip(),
            (content_obj.get("comparison_target_b") or "").strip(),
        ]

    # Check named comparands
    if len(headings) < 2 or not headings[0] or not headings[1]:
        errors.append("CONTENT_INSUFFICIENT: Both comparison targets must be named with non-empty headings")
    elif any(h.lower() in GENERIC_COMPARAND_NAMES for h in headings[:2]):
        errors.append(f"CONTENT_INSUFFICIENT: Comparison targets contain generic placeholder names: {headings[:2]}")

    # Check comparison rows/data points
    row_count = len(comp_rows)
    if not row_count and columns:
        pts_per_col = [len(c.get("points") or c.get("items") or c.get("bullets") or []) for c in columns[:2]]
        row_count = min(pts_per_col) if pts_per_col else 0

    if row_count == 0:
        errors.append("CONTENT_INSUFFICIENT: missing valid corresponding comparison dimensions (zero comparison data rows exist)")
    elif row_count < 2:
        errors.append(f"CONTENT_INSUFFICIENT: Insufficient comparison dimensions: expected at least 2 corresponding rows, found {row_count}")

    return errors


def validate_process_slide(slide_dict: Dict[str, Any]) -> List[str]:
    """Validate process slide stage count consistency and content completeness."""
    errors = []
    steps = slide_dict.get("steps", [])
    content_obj = slide_dict.get("content", {})
    process_steps = content_obj.get("process_steps", []) if isinstance(content_obj, dict) else []
    step_count = len(steps) or len(process_steps)

    if step_count == 0:
        errors.append("CONTENT_INSUFFICIENT: Process slide has zero process steps")
        return errors

    # Check agreement between takeaway claim and rendered stages
    takeaway = (slide_dict.get("key_message") or "").lower()
    
    # Check for number mentions in takeaway
    num_match = re.search(r"\b(\d+)[‑\s]*(?:stage|phase|step)s?\b", takeaway)
    word_nums = {
        "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
        "seven": 7, "eight": 8, "nine": 9, "ten": 10
    }
    word_match = re.search(r"\b(two|three|four|five|six|seven|eight|nine|ten)[‑\s]*(?:stage|phase|step)s?\b", takeaway)

    claimed_count = None
    if num_match:
        claimed_count = int(num_match.group(1))
    elif word_match:
        claimed_count = word_nums[word_match.group(1)]

    if claimed_count is not None and claimed_count != step_count:
        errors.append(
            f"Process stage count mismatch: primary takeaway claims {claimed_count} stages, "
            f"but slide renders {step_count} stages"
        )

    return errors


def validate_architecture_slide(slide_dict: Dict[str, Any]) -> List[str]:
    """
    Validate architecture slide required components and relationship bindings for ANY topic.
    Does NOT require Node.js-specific keywords on unrelated architecture slides.
    """
    errors = []
    bullets = slide_dict.get("body_bullets", [])
    columns = slide_dict.get("columns", [])
    layers = slide_dict.get("layers", [])
    takeaway = slide_dict.get("key_message", "")

    # Gather all architectural component candidates
    component_candidates = []
    for b in bullets:
        if ":" in b:
            component_candidates.append(b.split(":", 1)[0].strip())
        else:
            component_candidates.append(b.strip())
    for col in columns:
        heading = col.get("heading") or col.get("header") or col.get("title") or ""
        if heading:
            component_candidates.append(heading.strip())
    for lay in layers:
        title = lay.get("title") or lay.get("name") or ""
        if title:
            component_candidates.append(title.strip())

    # 1. Semantic Architecture Requirements: Must define at least 2 distinct structural components or subsystems
    distinct_components = [c for c in component_candidates if len(c.split()) >= 1 and not is_generic_filler(c)]
    if len(distinct_components) < 2:
        errors.append("CONTENT_INSUFFICIENT: Architecture slide must define at least 2 distinct structural components or subsystems")

    # 2. Check for displaced or unrelated content:
    # An architecture slide must not be displaced by unrelated exception handling snippets or disconnected clauses
    all_text = " ".join([takeaway] + bullets + [c.get("heading", "") + " " + " ".join(c.get("points", [])) for c in columns]).lower()
    if any(k in all_text for k in ("uncaught promise", "unhandled rejection", "async/await")) and not any(k in all_text for k in ("v8", "libuv", "kernel", "engine", "platform", "subsystem", "layer", "tier")):
        errors.append("CONTENT_INSUFFICIENT: Architecture content displaced by unrelated async/await or uncaught promise rejection text")

    # 3. Component functional binding: Components must convey operational or structural roles, not empty labels
    substantive_descriptions = 0
    for b in bullets:
        if ":" in b:
            desc = b.split(":", 1)[1].strip()
            if len(desc.split()) >= 4 and not is_generic_filler(desc):
                substantive_descriptions += 1
        elif len(b.split()) >= 6 and not is_generic_filler(b):
            substantive_descriptions += 1

    for col in columns:
        pts = col.get("points") or col.get("items") or []
        for pt in pts:
            if len(pt.split()) >= 4 and not is_generic_filler(pt):
                substantive_descriptions += 1

    if substantive_descriptions < 2:
        errors.append("CONTENT_INSUFFICIENT: Architecture components must include functional descriptions of subsystem roles")

    return errors


def validate_misconception_slide(slide_dict: Dict[str, Any]) -> List[str]:
    """Validate misconception and correction completeness."""
    errors = []
    columns = slide_dict.get("columns", [])
    bullets = slide_dict.get("body_bullets", [])

    left_points = []
    right_points = []
    if len(columns) >= 2:
        left_points = columns[0].get("points") or columns[0].get("items") or []
        right_points = columns[1].get("points") or columns[1].get("items") or []
    elif bullets:
        mid = (len(bullets) + 1) // 2
        left_points = bullets[:mid]
        right_points = bullets[mid:]

    if not left_points:
        errors.append("CONTENT_INSUFFICIENT: Misconception slide missing trap/misconception points")
    if not right_points:
        errors.append("CONTENT_INSUFFICIENT: Misconception slide has empty discipline/best practice card")

    return errors


def validate_summary_slide(slide_dict: Dict[str, Any]) -> List[str]:
    """Validate summary slide synthesis depth."""
    errors = []
    bullets = slide_dict.get("body_bullets", [])
    for b in bullets:
        if b.strip().startswith("Synthesis:"):
            words = b.strip().split()
            if len(words) <= 3:
                errors.append(f"Generic template synthesis placeholder detected: '{b}'")
    return errors


def validate_slide_content_completeness(slide_dict: Dict[str, Any], seen_titles: Set[str]) -> List[str]:
    """Validate semantic and structural completeness for a single slide."""
    errors = []
    title = (slide_dict.get("title") or "").strip()
    takeaway = (slide_dict.get("key_message") or "").strip()
    bullets = slide_dict.get("body_bullets", [])
    raw_type = slide_dict.get("type")
    type_str = getattr(raw_type, "value", str(raw_type) if raw_type is not None else "")
    intent = (str(slide_dict.get("intent") or type_str)).split(".")[-1].lower().strip()

    # 1. Duplicate title check
    norm_title = re.sub(r"[^\w\s]", "", title).lower().strip()
    if norm_title in seen_titles:
        errors.append(f"Duplicate semantic title across presentation: '{title}'")
    elif norm_title:
        seen_titles.add(norm_title)

    # 2. Incomplete sentence checks
    title_err = check_sentence_completeness(title)
    if title_err:
        errors.append(f"Slide title incomplete: {title_err} in '{title}'")

    takeaway_err = check_sentence_completeness(takeaway)
    if takeaway_err:
        errors.append(f"Primary takeaway incomplete: {takeaway_err} in '{takeaway}'")

    # 3. Semantic completeness check on body points / bullets
    # A slide containing 2 complete, meaningful points is valid.
    # A slide containing 3 generic filler points must NOT pass merely because it meets a count.
    if bullets:
        valid_points = 0
        filler_points = 0
        for idx, b in enumerate(bullets):
            is_valid, reason = is_semantically_complete_point(b)
            if is_valid:
                valid_points += 1
            else:
                if is_generic_filler(b):
                    filler_points += 1
                errors.append(f"Bullet {idx + 1} invalid: {reason}")
        if filler_points > 0 and valid_points < 2:
            errors.append("CONTENT_INSUFFICIENT: Slide relies on generic filler points instead of substantive content")
        elif valid_points < 2 and not slide_dict.get("columns") and not slide_dict.get("steps") and intent not in ("cover", "summary", "closing", "title"):
            errors.append("CONTENT_INSUFFICIENT: Slide must contain at least 2 complete, meaningful points")

    # 4. Visible placeholder check
    all_slide_strings = [title, takeaway] + bullets
    for col in slide_dict.get("columns", []):
        all_slide_strings.append(col.get("heading", ""))
        all_slide_strings.extend(col.get("points", []))

    for s in all_slide_strings:
        sl = s.lower().strip()
        if sl in ("option 1", "option 2", "option a", "option b", "tbd", "placeholder", "lorem ipsum"):
            errors.append(f"Visible internal placeholder label detected: '{s}'")

    # 5. Intent-specific validations
    is_misconception = (
        "misconception" in intent or "common_mistakes" in intent
        or slide_dict.get("content_pattern") == "contrast_pair"
        or "misconception" in str(slide_dict.get("narrative_role", "")).lower()
        or (isinstance(slide_dict.get("content"), dict) and bool(slide_dict["content"].get("misconceptions") or slide_dict["content"].get("misconception")))
    )
    if is_misconception:
        errors.extend(validate_misconception_slide(slide_dict))
    elif "comparison" in intent:
        errors.extend(validate_comparison_slide(slide_dict))
    elif "process" in intent or "workflow" in intent or slide_dict.get("steps"):
        errors.extend(validate_process_slide(slide_dict))
    elif "architecture" in intent or "system_overview" in intent or "component_breakdown" in intent:
        errors.extend(validate_architecture_slide(slide_dict))
    elif "summary" in intent:
        errors.extend(validate_summary_slide(slide_dict))

    return errors


class ContentCompletenessAuditResult:
    def __init__(self, passed: bool, error_count: int, errors: List[str], slide_errors: Dict[int, List[str]]):
        self.passed = passed
        self.is_valid = passed
        self.error_count = error_count
        self.errors = errors
        self.violations = errors
        self.slide_errors = slide_errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "is_valid": self.is_valid,
            "error_count": self.error_count,
            "errors": self.errors,
            "violations": self.violations,
            "slide_errors": self.slide_errors,
        }

    def __getitem__(self, item):
        return getattr(self, item)


def audit_deck_content_completeness(slides_or_spec: Any) -> ContentCompletenessAuditResult:
    """Audit an entire slide deck before PPTX rendering."""
    raw_slides = []
    if hasattr(slides_or_spec, "slides"):
        raw_slides = getattr(slides_or_spec, "slides")
    elif isinstance(slides_or_spec, list):
        raw_slides = slides_or_spec
    else:
        raw_slides = [slides_or_spec]

    dict_slides = []
    for s in raw_slides:
        if isinstance(s, dict):
            dict_slides.append(s)
        elif hasattr(s, "model_dump"):
            dict_slides.append(s.model_dump())
        elif hasattr(s, "dict"):
            dict_slides.append(s.dict())
        else:
            dict_slides.append(vars(s))

    seen_titles: Set[str] = set()
    slide_errors: Dict[int, List[str]] = {}
    all_errors: List[str] = []

    for idx, slide_dict in enumerate(dict_slides):
        slide_no = slide_dict.get("slide_no", idx + 1)
        errs = validate_slide_content_completeness(slide_dict, seen_titles)
        if errs:
            slide_errors[slide_no] = errs
            for e in errs:
                all_errors.append(f"Slide {slide_no}: {e}")

    return ContentCompletenessAuditResult(
        passed=len(all_errors) == 0,
        error_count=len(all_errors),
        errors=all_errors,
        slide_errors=slide_errors,
    )

