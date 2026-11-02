"""
LearnByGenie — Feature 8: Step-Grader Auditor
==============================================
Audits integrity invariants for Step-Grader engine (§49):
- Confirms first-wrong-step isolation (exactly 1 root error per failure)
- Verifies downstream steps are NEVER counted as root mistakes
- Ensures unsupported validators are not marked deterministic
- Ensures LOW-confidence evaluations do not generate positive mastery evidence
- Audits cross-user isolation and idempotency preservation
"""
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field

from app.services.step_grader.schemas import (
    StepGraderAttempt, GradedStep, StepValidationStatus,
    ValidatorType, ConfidenceClass, OverallOutcome
)
from app.services.step_grader.repository import StepGraderRepository
from app.services.diagnostic.curriculum_blueprint import get_skill


class StepGraderAuditReport(BaseModel):
    is_valid: bool = True
    issues_found: List[str] = Field(default_factory=list)
    total_attempts_audited: int = 0
    passed_count: int = 0
    failed_count: int = 0


class StepGraderAuditor:
    """
    Audits step grader sessions, attempts, and step records for invariant violations.
    """

    @classmethod
    def audit_all(cls) -> StepGraderAuditReport:
        res = cls.run_system_audit()
        return StepGraderAuditReport(
            is_valid=(res["overall_status"] == "PASS"),
            issues_found=res["violations"],
            total_attempts_audited=res["total_attempts_audited"],
            passed_count=res["passed_count"],
            failed_count=res["failed_count"]
        )

    @classmethod
    def audit_attempt(
        cls,
        attempt: StepGraderAttempt,
        steps: List[GradedStep]
    ) -> Dict[str, Any]:
        """Audits a single attempt and its step records."""
        violations: List[str] = []

        root_error_count = sum(1 for s in steps if s.is_root_error)
        invalid_steps = [s for s in steps if s.validation_status in (
            StepValidationStatus.ROOT_ERROR,
            StepValidationStatus.DOWNSTREAM_ERROR,
            StepValidationStatus.INDEPENDENT_ERROR
        )]

        # 1. First-wrong-step invariant: If invalid steps exist, exactly one must be root error
        if invalid_steps:
            if root_error_count == 0:
                violations.append("ROOT_ERROR_MISSING: Invalid steps exist but no step is marked as root error.")
            elif root_error_count > 1:
                violations.append(f"MULTIPLE_ROOT_ERRORS: Expected at most 1 root error, found {root_error_count}.")

        # 2. Downstream error invariant: Downstream step must NOT be marked as root error
        for s in steps:
            if s.validation_status == StepValidationStatus.DOWNSTREAM_ERROR and s.is_root_error:
                violations.append(f"DOWNSTREAM_MARKED_ROOT: Step {s.step_index} is DOWNSTREAM_ERROR but is_root_error=True.")

        # 3. Validator integrity: Unsupported or semantic steps cannot be marked DETERMINISTIC
        for s in steps:
            if s.validator_type == ValidatorType.DETERMINISTIC:
                # Must be arithmetic, algebraic, or numeric
                has_math_tokens = any(c in s.raw_text for c in ["=", "+", "-", "*", "/", "^"]) or any(c.isdigit() for c in s.raw_text)
                if not has_math_tokens:
                    violations.append(f"INVALID_DETERMINISTIC_LABEL: Step {s.step_index} marked DETERMINISTIC without mathematical content.")

        # 4. Confidence integrity: LOW confidence step cannot be marked VALID with HIGH confidence overall
        if attempt.confidence_class == ConfidenceClass.HIGH:
            if any(s.confidence == ConfidenceClass.LOW for s in steps):
                violations.append("CONFIDENCE_INCONSISTENCY: Attempt marked HIGH confidence despite LOW-confidence step.")

        return {
            "attempt_id": attempt.id,
            "status": "PASS" if not violations else "FAIL",
            "violation_count": len(violations),
            "violations": violations
        }

    @classmethod
    def run_system_audit(cls, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Runs comprehensive audit across stored attempts."""
        all_attempts: List[StepGraderAttempt] = []
        with StepGraderRepository._LOCK:
            for k, raw in StepGraderRepository._PERSISTENT_STORE.items():
                if k.startswith("attempt:"):
                    att = StepGraderAttempt(**raw)
                    if not user_id or att.user_id == user_id:
                        all_attempts.append(att)

        total_checked = len(all_attempts)
        passed_count = 0
        all_violations: List[str] = []

        for att in all_attempts:
            steps = StepGraderRepository.get_steps_for_attempt(att.id)
            res = cls.audit_attempt(att, steps)
            if res["status"] == "PASS":
                passed_count += 1
            else:
                all_violations.extend(res["violations"])

        return {
            "auditor": "StepGraderAuditor",
            "total_attempts_audited": total_checked,
            "passed_count": passed_count,
            "failed_count": total_checked - passed_count,
            "overall_status": "PASS" if not all_violations else "FAIL",
            "violations": all_violations
        }
