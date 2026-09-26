"""
LearnByGenie Canary Infrastructure — Anonymized Export & Privacy Verification Engine
==================================================================================
Safeguard #1 & Validation:
- Exports canary telemetry and learner session evidence into anonymized CSV / JSON formats.
- Guarantees 100% pseudonymous identifiers (`tc_psd_...`, `st_psd_...`).
- Strictly screens and validates zero direct PII (emails, names, phone numbers, raw IDs).
"""

import csv
import io
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from .pseudonyms import IsolatedIdentityRegistry, EMAIL_REGEX, PHONE_REGEX, IPV4_REGEX

logger = logging.getLogger("learnbygenie.canary.exports")


class CanaryDatasetExporter:
    """
    Manages export of canary telemetry and session evidence with automated privacy screening.
    """

    @classmethod
    def format_export_record(
        cls,
        session_id: str,
        teacher_pseudonym_id: str,
        student_pseudonym_id: str,
        canonical_concept_id: str,
        stage_title: str,
        pre_state: str,
        post_state: str,
        misconception_tag: Optional[str],
        time_spent_seconds: int,
        feedback_type: str,
        created_at: str
    ) -> Dict[str, Any]:
        """
        Structures an individual canary record using strictly pseudonymous fields.
        """
        assert IsolatedIdentityRegistry.is_valid_pseudonym(teacher_pseudonym_id), f"Invalid teacher pseudonym: {teacher_pseudonym_id}"
        assert IsolatedIdentityRegistry.is_valid_pseudonym(student_pseudonym_id), f"Invalid student pseudonym: {student_pseudonym_id}"

        return {
            "session_id": session_id,
            "teacher_pseudonym_id": teacher_pseudonym_id,
            "student_pseudonym_id": student_pseudonym_id,
            "canonical_concept_id": canonical_concept_id,
            "stage_title": stage_title,
            "pre_state": pre_state,
            "post_state": post_state,
            "misconception_tag": misconception_tag or "none",
            "time_spent_seconds": time_spent_seconds,
            "feedback_type": feedback_type,
            "created_at": created_at
        }

    @classmethod
    def export_to_csv(cls, records: List[Dict[str, Any]], target_file: Optional[str] = None) -> str:
        """
        Exports records to CSV string and optional file, with privacy validation.
        """
        validation = cls.validate_export_privacy(records)
        if not validation["is_privacy_compliant"]:
            raise ValueError(f"Privacy validation failed for canary export: {validation['violations']}")

        fieldnames = [
            "session_id", "teacher_pseudonym_id", "student_pseudonym_id",
            "canonical_concept_id", "stage_title", "pre_state", "post_state",
            "misconception_tag", "time_spent_seconds", "feedback_type", "created_at"
        ]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(r)

        csv_str = output.getvalue()
        if target_file:
            path = Path(target_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(csv_str)
            logger.info(f"[CanaryExport] Wrote {len(records)} anonymized records to {target_file}")

        return csv_str

    @classmethod
    def export_to_json(cls, records: List[Dict[str, Any]], target_file: Optional[str] = None) -> str:
        """
        Exports records to JSON string and optional file with privacy validation.
        """
        validation = cls.validate_export_privacy(records)
        if not validation["is_privacy_compliant"]:
            raise ValueError(f"Privacy validation failed for canary export: {validation['violations']}")

        json_str = json.dumps(records, indent=2)
        if target_file:
            path = Path(target_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(json_str)
            logger.info(f"[CanaryExport] Wrote {len(records)} anonymized records to {target_file}")

        return json_str

    @classmethod
    def validate_export_privacy(cls, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Strict automated privacy audit of export data.
        Validates:
        1. No emails, phone numbers, or IP addresses in any string field.
        2. All participant IDs match the pseudonymous prefix format.
        3. No raw user IDs or forbidden fields present.
        """
        violations: List[str] = []

        for idx, rec in enumerate(records):
            # Check ID format
            t_id = rec.get("teacher_pseudonym_id", "")
            s_id = rec.get("student_pseudonym_id", "")
            if not IsolatedIdentityRegistry.is_valid_pseudonym(t_id):
                violations.append(f"Row {idx}: Invalid teacher pseudonym '{t_id}'")
            if not IsolatedIdentityRegistry.is_valid_pseudonym(s_id):
                violations.append(f"Row {idx}: Invalid student pseudonym '{s_id}'")

            # Check for forbidden PII keys
            for k in rec.keys():
                if k.lower() in ("email", "name", "phone", "raw_user_id", "user_id", "first_name", "last_name"):
                    violations.append(f"Row {idx}: Forbidden direct PII column '{k}' detected")

            # Deep string scan
            field_violations = IsolatedIdentityRegistry.scan_for_pii(rec)
            for fv in field_violations:
                violations.append(f"Row {idx}: {fv}")

        is_compliant = len(violations) == 0
        return {
            "is_privacy_compliant": is_compliant,
            "total_records_scanned": len(records),
            "pii_leaks_detected": len(violations),
            "violations": violations
        }
