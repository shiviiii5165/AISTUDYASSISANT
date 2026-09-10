"""
Source Grounding & Provenance Validator
=======================================
Verifies citation integrity, detects fabricated sources, and audits factual claims
against grounded source material provided in the context or pipeline.
"""
from typing import List, Dict, Any, Tuple, Optional, Set
import re

from ...schemas import NotesDocument
from ...context.schemas import CanonicalNotesContext
from ...generation.schemas import GroundedSources
from ..schemas import (
    ValidationViolation, ViolationSeverity, ValidationDimension
)


class SourceGroundingValidator:
    """Audits document citations and source grounding integrity."""

    @staticmethod
    def validate(
        doc: NotesDocument,
        ctx: CanonicalNotesContext,
        sources: Optional[GroundedSources] = None
    ) -> Tuple[List[ValidationViolation], Dict[str, Any], float]:
        violations: List[ValidationViolation] = []
        details: Dict[str, Any] = {"verified_citations": [], "unverified_citations": []}
        score: float = 100.0

        # Collect verified source IDs
        verified_source_ids: Set[str] = set()
        if sources and sources.items:
            for s in sources.items:
                verified_source_ids.add(s.source_id)
        elif ctx.source_evidence:
            for ev in ctx.source_evidence:
                if isinstance(ev, dict) and ev.get("source_id"):
                    verified_source_ids.add(ev["source_id"])

        details["supplied_source_ids"] = list(verified_source_ids)

        # ── 1. Citation Provenance Verification ──
        for idx, citation in enumerate(doc.source_citations):
            if not isinstance(citation, dict):
                continue
            cid = citation.get("source_id")

            # If sources were explicitly provided, check if the citation cites a non-existent source
            if verified_source_ids and cid not in verified_source_ids:
                violations.append(ValidationViolation(
                    code="FABRICATED_SOURCE_ID",
                    severity=ViolationSeverity.CRITICAL,
                    dimension=ValidationDimension.GROUNDING,
                    message=f"Document cites nonexistent or fabricated source ID '{cid}'. Supplying sources: {list(verified_source_ids)}.",
                    section_id=f"citation_{idx+1}",
                    evidence=citation,
                    expected=f"One of {list(verified_source_ids)}",
                    actual=cid,
                    repairable=True
                ))
                score -= 25.0
                details["unverified_citations"].append(cid)
            elif cid:
                details["verified_citations"].append(cid)

            # Check fabricated URLs in citations
            url = citation.get("url")
            if url and not url.startswith(("http://", "https://", "internal://")):
                violations.append(ValidationViolation(
                    code="MALFORMED_OR_INVENTED_URL",
                    severity=ViolationSeverity.WARNING,
                    dimension=ValidationDimension.GROUNDING,
                    message=f"Citation '{cid}' contains malformed or fabricated URL: '{url}'.",
                    section_id=f"citation_{idx+1}",
                    expected="Valid HTTP/HTTPS or internal URI",
                    actual=url,
                    repairable=True
                ))
                score -= 5.0

        # ── 2. Unsupported Claim Detection ──
        # Check if citations or content refer to explicit fabricated claims
        for s in doc.sections:
            # Check for claims asserting grounded textbook authority without citations
            if "according to the verified source" in s.content.lower() and not doc.source_citations and not verified_source_ids:
                violations.append(ValidationViolation(
                    code="UNSUPPORTED_FACTUAL_CLAIM",
                    severity=ViolationSeverity.WARNING,
                    dimension=ValidationDimension.GROUNDING,
                    message=f"Section '{s.title}' claims authority from verified sources, but no verified source evidence exists.",
                    section_id=s.id,
                    evidence=s.title,
                    expected="Explicit grounded source evidence",
                    actual="Unbacked claim of external source authority",
                    repairable=True
                ))
                score -= 10.0

        return violations, details, max(0.0, min(100.0, score))
