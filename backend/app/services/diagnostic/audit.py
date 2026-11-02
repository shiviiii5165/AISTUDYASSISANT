"""
LearnByGenie — Diagnostic Content Quality & Audit Tooling (§35, §9)
===================================================================
Deterministic auditor inspecting diagnostic items for:
- Missing answers or empty prompts
- Invalid or broken skill mappings
- Unsupported grade bands or difficulty bands
- Broken or duplicate MCQ options
- Correct answer option alignment
- Duplicate question stems
- Valid language tags
- Prerequisite reference integrity
- Quarantine detection for invalid/unverified items
"""
from typing import List, Dict, Any, Tuple, Set
from pydantic import BaseModel, Field

from .schemas import DiagnosticItem, QuestionType, VerificationStatus, GradeBand, DifficultyBand
from .curriculum_blueprint import get_skill, CANONICAL_SKILLS
from .item_bank import get_all_items


class ItemAuditIssue(BaseModel):
    item_id: str
    code: str
    message: str
    severity: str = "ERROR"  # "ERROR", "WARNING"


class ContentAuditReport(BaseModel):
    total_items: int = 0
    valid_items: int = 0
    invalid_items: int = 0
    quarantined_items: int = 0
    issues: List[ItemAuditIssue] = Field(default_factory=list)
    is_healthy: bool = True

    # Backwards compatibility properties
    @property
    def total_items_audited(self) -> int:
        return self.total_items

    @property
    def passed_items_count(self) -> int:
        return self.valid_items


def audit_diagnostic_item(item: DiagnosticItem) -> List[ItemAuditIssue]:
    issues: List[ItemAuditIssue] = []

    # 1. Prompt check
    if not item.prompt or not item.prompt.strip():
        issues.append(ItemAuditIssue(item_id=item.id, code="EMPTY_PROMPT", message="Item prompt is empty."))

    # 2. Correct answer check
    if item.correct_answer is None or str(item.correct_answer).strip() == "":
        issues.append(ItemAuditIssue(item_id=item.id, code="MISSING_CORRECT_ANSWER", message="Item is missing correct_answer."))

    # 3. Skill mapping check
    skill = get_skill(item.skill_id)
    if not skill:
        issues.append(ItemAuditIssue(item_id=item.id, code="INVALID_SKILL_MAPPING", message=f"Mapped skill_id '{item.skill_id}' not found in blueprint."))
    else:
        # Check prerequisite references validity
        for prereq_id in skill.prerequisite_skill_ids:
            if not get_skill(prereq_id):
                issues.append(ItemAuditIssue(item_id=item.id, code="INVALID_PREREQ_REFERENCE", message=f"Skill '{skill.id}' references non-existent prerequisite '{prereq_id}'."))

    # 4. Grade band check
    valid_grade_bands = {gb.value for gb in GradeBand}
    if item.grade_band not in valid_grade_bands:
        issues.append(ItemAuditIssue(item_id=item.id, code="UNSUPPORTED_GRADE_BAND", message=f"Grade band '{item.grade_band}' is not supported."))

    # 5. Difficulty band check
    valid_difficulties = {db.value for db in DifficultyBand}
    if item.difficulty_band not in valid_difficulties:
        issues.append(ItemAuditIssue(item_id=item.id, code="INVALID_DIFFICULTY", message=f"Difficulty '{item.difficulty_band}' is invalid."))

    # 6. Language check
    valid_languages = {"english", "hindi", "hinglish", "bengali", "tamil", "telugu", "all"}
    if item.language.lower() not in valid_languages:
        issues.append(ItemAuditIssue(item_id=item.id, code="INVALID_LANGUAGE_TAG", message=f"Language '{item.language}' is not an approved language tag."))

    # 7. Verification status check
    if item.verification_status != VerificationStatus.VERIFIED:
        issues.append(ItemAuditIssue(item_id=item.id, code="UNVERIFIED_ITEM", message="Item verification status is not VERIFIED.", severity="WARNING"))

    # 8. MCQ option integrity
    if item.question_type == QuestionType.MCQ:
        if not item.options or len(item.options) < 2:
            issues.append(ItemAuditIssue(item_id=item.id, code="TOO_FEW_OPTIONS", message="MCQ requires at least 2 distinct options."))
        else:
            cleaned = [str(o).strip().lower() for o in item.options]
            if len(set(cleaned)) != len(cleaned):
                issues.append(ItemAuditIssue(item_id=item.id, code="DUPLICATE_OPTIONS", message="MCQ has duplicate options."))

            # Ensure correct answer matches one of the options
            target = str(item.correct_answer).strip().lower()
            if target not in cleaned:
                issues.append(ItemAuditIssue(item_id=item.id, code="CORRECT_ANSWER_NOT_IN_OPTIONS", message="MCQ correct answer does not match any provided option."))

    return issues


def audit_entire_item_bank() -> ContentAuditReport:
    """Runs a full audit over all registered diagnostic items and checks global properties."""
    items = get_all_items()
    report = ContentAuditReport(total_items=len(items))

    # Track prompt stems to detect stem duplication
    stems_seen: Dict[str, str] = {}

    for item in items:
        item_issues = audit_diagnostic_item(item)

        # Check stem uniqueness
        normalized_stem = " ".join(item.prompt.strip().lower().split()[:8])
        if normalized_stem in stems_seen:
            item_issues.append(ItemAuditIssue(
                item_id=item.id,
                code="DUPLICATE_STEM",
                message=f"Prompt stem closely matches item {stems_seen[normalized_stem]}.",
                severity="WARNING"
            ))
        else:
            stems_seen[normalized_stem] = item.id

        if item_issues:
            report.issues.extend(item_issues)
            has_error = any(i.severity == "ERROR" for i in item_issues)
            if has_error:
                report.invalid_items += 1
                report.quarantined_items += 1
                report.is_healthy = False
            else:
                report.valid_items += 1
        else:
            report.valid_items += 1

    return report
