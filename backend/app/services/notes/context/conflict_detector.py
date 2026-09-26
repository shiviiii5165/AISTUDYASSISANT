"""
LearnByGenie Notes Context Engine — Conflict Detector
===================================================
Detects and records contradictions across multiple educational context sources.
Preserves complete conflicting evidence in metadata rather than silently overwriting.
"""
from typing import List, Dict, Any, Optional
from .schemas import ContextConflict, NotesContextSource


class CandidateValue:
    """Represents a candidate field value from a specific context source."""
    def __init__(self, source: NotesContextSource, value: Any, raw_value: Optional[Any] = None, priority: int = 8):
        self.source = source
        self.value = value
        self.raw_value = raw_value if raw_value is not None else value
        self.priority = priority


class ConflictDetector:
    """Detects and formalizes contradictions between candidate values from different sources."""

    @staticmethod
    def detect_field_conflict(
        field_name: str,
        candidates: List[CandidateValue],
        resolved_candidate: Optional[CandidateValue]
    ) -> Optional[ContextConflict]:
        """
        Examines candidate values for a given field.
        If more than one distinct non-null value exists across sources, generates a ContextConflict.
        """
        valid_candidates = [c for c in candidates if c.value is not None and str(c.value).strip() != ""]
        if len(valid_candidates) <= 1:
            return None

        # Check if distinct values exist (case-insensitive string comparison)
        unique_normalized = set(str(c.value).strip().lower() for c in valid_candidates)
        if len(unique_normalized) <= 1:
            return None

        # Determine severity based on pedagogical field impact
        severity = "medium"
        if field_name in ("subject", "topic"):
            severity = "high"
        elif field_name in ("language", "teaching_method"):
            severity = "low"
        elif field_name in ("class_level", "grade", "curriculum"):
            severity = "medium"

        # Format values record
        values_record = [
            {
                "source": c.source.value if hasattr(c.source, "value") else str(c.source),
                "value": str(c.value),
                "raw_value": str(c.raw_value),
                "priority": c.priority
            }
            for c in valid_candidates
        ]

        res_val = resolved_candidate.value if resolved_candidate else None
        res_source = (resolved_candidate.source.value if hasattr(resolved_candidate.source, "value") else str(resolved_candidate.source)) if resolved_candidate else "unknown"

        reason = f"Conflict on '{field_name}' resolved in favor of '{res_source}' due to higher source priority."

        return ContextConflict(
            field=field_name,
            severity=severity,
            values=values_record,
            resolved_value=res_val,
            resolved_from=res_source,
            reason=reason
        )
