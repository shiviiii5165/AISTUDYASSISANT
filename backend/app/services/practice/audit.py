"""
LearnByGenie — Practice Content Bank Auditor & Coverage Matrix (Feature 6, §49, §50, §51)
===========================================================================================
Deterministic validation of all practice items:
- Missing answers, bad schemas, duplicate options
- Jaccard token-set near-duplicate stem detection (§51)
- Coverage matrices across stages, subjects, skills, difficulty bands (§49)
- Distinguishes ENGINE_SUPPORTED from CONTENT_SUFFICIENT (§17, §49)
"""
from typing import List, Dict, Any, Tuple, Set, Optional
import re
from app.services.practice.schemas import (
    PracticeItem, QuestionType, DifficultyBand,
    VerificationStatus, ProvenanceType, ContentCoverageStatus, ContentAuditReport
)
from app.services.practice.item_bank import get_all_practice_items
from app.services.diagnostic.curriculum_blueprint import CANONICAL_SKILLS, get_skill

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "on", "for", "is", "are", "was", "were",
    "what", "which", "who", "how", "why", "does", "do", "did", "and", "or"
}


def _normalize_tokens(text: str) -> Set[str]:
    return {t for t in _WORD_RE.findall(text.lower()) if t not in _STOPWORDS}


def _jaccard_similarity(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class ContentAuditor:
    """
    Validates practice item bank integrity and generates audit reports.
    """

    DUPLICATE_STEM_THRESHOLD = 0.85
    MIN_ITEMS_FOR_SUFFICIENT = 2

    @classmethod
    def audit_all(cls, items: Optional[List[PracticeItem]] = None) -> ContentAuditReport:
        items_to_check = items if items is not None else get_all_practice_items()
        issues: List[str] = []

        seen_ids: Set[str] = set()
        by_subject: Dict[str, int] = {}
        by_difficulty: Dict[str, int] = {}
        by_grade_band: Dict[str, int] = {}
        by_skill: Dict[str, List[PracticeItem]] = {}
        verified_count = 0

        tokens_by_idx: List[Set[str]] = []

        for idx, item in enumerate(items_to_check):
            # 1. ID uniqueness
            if item.id in seen_ids:
                issues.append(f"Duplicate item ID: {item.id}")
            seen_ids.add(item.id)

            # 2. Skill validity
            sk = get_skill(item.skill_id)
            if not sk:
                issues.append(f"Item {item.id} references unknown skill {item.skill_id}")

            # 3. Answer presence and schema
            if item.correct_answer is None or str(item.correct_answer).strip() == "":
                issues.append(f"Item {item.id} has empty correct_answer")

            # 4. MCQ options validation
            if item.question_type == QuestionType.MCQ:
                if len(item.options) < 2:
                    issues.append(f"Item {item.id} has fewer than 2 MCQ options")
                opts_lower = [str(o).strip().lower() for o in item.options]
                if len(opts_lower) != len(set(opts_lower)):
                    issues.append(f"Item {item.id} contains duplicate options")
                # Correct answer must be among options or valid option index/letter
                ca_str = str(item.correct_answer).strip().lower()
                valid_match = (ca_str in opts_lower) or (ca_str in [chr(ord('a') + i) for i in range(len(item.options))]) or (ca_str.isdigit() and int(ca_str) < len(item.options))
                if not valid_match:
                    issues.append(f"Item {item.id} correct answer '{item.correct_answer}' not in options")

            # 5. Provenance & verification status
            if item.verification_status != VerificationStatus.VERIFIED:
                issues.append(f"Item {item.id} has non-verified status: {item.verification_status}")
            else:
                verified_count += 1

            # 6. Aggregations
            by_subject[item.subject] = by_subject.get(item.subject, 0) + 1
            by_difficulty[item.difficulty_band.value] = by_difficulty.get(item.difficulty_band.value, 0) + 1
            by_grade_band[item.grade_band] = by_grade_band.get(item.grade_band, 0) + 1
            by_skill.setdefault(item.skill_id, []).append(item)

            tokens_by_idx.append(_normalize_tokens(item.prompt))

        # 7. Check pairwise duplicate stems
        for i in range(len(items_to_check)):
            for j in range(i + 1, len(items_to_check)):
                sim = _jaccard_similarity(tokens_by_idx[i], tokens_by_idx[j])
                if sim >= cls.DUPLICATE_STEM_THRESHOLD:
                    issues.append(
                        f"Near-duplicate prompts detected between {items_to_check[i].id} and {items_to_check[j].id} (similarity {sim:.2f})"
                    )

        # 8. Coverage matrix calculation (§49, §50)
        coverage_matrix: Dict[str, ContentCoverageStatus] = {}
        for skill in CANONICAL_SKILLS:
            sk_items = by_skill.get(skill.id, [])
            val_items = [it for it in sk_items if it.verification_status == VerificationStatus.VERIFIED]
            if len(val_items) >= cls.MIN_ITEMS_FOR_SUFFICIENT:
                coverage_matrix[skill.id] = ContentCoverageStatus.COMPLETE
            elif len(val_items) > 0:
                coverage_matrix[skill.id] = ContentCoverageStatus.PARTIAL
            else:
                coverage_matrix[skill.id] = ContentCoverageStatus.INSUFFICIENT_CONTENT

        return ContentAuditReport(
            total_items=len(items_to_check),
            verified_items=verified_count,
            items_by_subject=by_subject,
            items_by_difficulty=by_difficulty,
            items_by_grade_band=by_grade_band,
            issues_found=issues,
            coverage_matrix=coverage_matrix,
            is_valid=(len(issues) == 0)
        )

    @classmethod
    def generate_coverage_matrix(cls) -> Dict[str, Any]:
        report = cls.audit_all()
        return {
            "total_items": report.total_items,
            "coverage": report.coverage_matrix,
            "by_subject": report.items_by_subject,
            "by_difficulty": report.items_by_difficulty
        }
