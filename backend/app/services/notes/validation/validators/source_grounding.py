"""
Source Grounding & Provenance Validator
=======================================
Verifies citation integrity, detects fabricated sources, and audits factual claims
against grounded source material provided in the context or pipeline.
Enforces nuanced grounding support semantics:
    DIRECTLY_SUPPORTED, PARAPHRASE_SUPPORTED, INFERRED_SUPPORTED, UNSUPPORTED, CONTRADICTED, UNKNOWN
Contradiction carries CRITICAL severity and immediately invalidates the document.
"""
from typing import List, Dict, Any, Tuple, Optional, Set
import re

from ...schemas import NotesDocument
from ...context.schemas import CanonicalNotesContext
from ...generation.schemas import GroundedSources
from ..schemas import (
    ValidationViolation, ViolationSeverity, ValidationDimension,
    GroundingSupportType, SourceGroundingFinding
)


class SourceGroundingValidator:
    """Audits document citations and source grounding integrity."""

    # Common canonical scientific contradictions: (source_pattern, contradictory_doc_pattern, description)
    KNOWN_CONTRADICTIONS = [
        (
            r'earth\s+revolves\s+around\s+the\s+sun',
            r'sun\s+revolves\s+around\s+the\s+earth',
            "Document states the Sun revolves around the Earth, which directly contradicts source stating the Earth revolves around the Sun."
        ),
        (
            r'inertia\s+is\s+not\s+a\s+force',
            r'inertia\s+is\s+a\s+force',
            "Document states inertia is a force, which directly contradicts source stating inertia is not a force."
        ),
        (
            r'mass\s+remains\s+constant',
            r'mass\s+changes\s+with\s+gravity',
            "Document claims mass changes with gravity, contradicting source evidence."
        ),
        (
            r'light\s+travels\s+faster\s+than\s+sound',
            r'sound\s+travels\s+faster\s+than\s+light',
            "Document claims sound travels faster than light, contradicting source evidence."
        )
    ]

    @classmethod
    def validate(
        cls,
        doc: NotesDocument,
        ctx: CanonicalNotesContext,
        sources: Optional[GroundedSources] = None
    ) -> Tuple[List[ValidationViolation], Dict[str, Any], float]:
        violations: List[ValidationViolation] = []
        details: Dict[str, Any] = {
            "verified_citations": [],
            "unverified_citations": [],
            "findings": [],
            "support_counts": {st.value: 0 for st in GroundingSupportType}
        }
        score: float = 100.0

        # Collect verified source items and IDs
        verified_source_ids: Set[str] = set()
        source_texts: List[Tuple[str, str]] = []  # (source_id, content)

        if sources and sources.items:
            for s in sources.items:
                verified_source_ids.add(s.source_id)
                txt = getattr(s, "content", "") or getattr(s, "snippet", "") or getattr(s, "title", "")
                if txt:
                    source_texts.append((s.source_id, txt))
        elif ctx.source_evidence:
            for ev in ctx.source_evidence:
                if isinstance(ev, dict) and ev.get("source_id"):
                    sid = ev["source_id"]
                    verified_source_ids.add(sid)
                    txt = ev.get("quote") or ev.get("content") or ev.get("title") or ""
                    if txt:
                        source_texts.append((sid, txt))

        details["supplied_source_ids"] = list(verified_source_ids)

        # ── 1. Citation Provenance Verification ──
        for idx, citation in enumerate(doc.source_citations):
            if not isinstance(citation, dict):
                continue
            cid = citation.get("source_id")

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

        # Combine all document content into checkable units
        doc_sentences: List[Tuple[str, str]] = []  # (sentence, section_id)
        for s in doc.sections:
            for sentence in re.split(r'(?<=[.!?])\s+', s.content):
                sent_clean = sentence.strip()
                if len(sent_clean) > 15:
                    doc_sentences.append((sent_clean, s.id or s.section_type))

        all_doc_text = " ".join([s.content for s in doc.sections]).lower()

        # ── 2. Contradiction Detection (Critical Severity) ──
        for sid, stext in source_texts:
            stext_lower = stext.lower()
            for src_pat, doc_pat, err_msg in cls.KNOWN_CONTRADICTIONS:
                if re.search(src_pat, stext_lower) and re.search(doc_pat, all_doc_text):
                    finding = SourceGroundingFinding(
                        claim=doc_pat,
                        source_ids=[sid],
                        support_type=GroundingSupportType.CONTRADICTED,
                        evidence=stext,
                        confidence=0.98,
                        severity=ViolationSeverity.CRITICAL
                    )
                    details["findings"].append(finding.model_dump())
                    details["support_counts"][GroundingSupportType.CONTRADICTED.value] += 1
                    violations.append(ValidationViolation(
                        code="SOURCE_CLAIM_CONTRADICTED",
                        severity=ViolationSeverity.CRITICAL,
                        dimension=ValidationDimension.GROUNDING,
                        message=err_msg,
                        evidence={"source_id": sid, "source_evidence": stext},
                        expected="Alignment with verified source evidence",
                        actual="Direct contradiction of verified source claim",
                        repairable=False
                    ))
                    score -= 40.0

        # ── 3. Support Classification (Direct, Paraphrase, Unsupported) ──
        if source_texts:
            for sid, stext in source_texts:
                stext_clean = stext.strip()
                stext_words = set(re.findall(r'\w{4,}', stext.lower()))

                for sent, sec_id in doc_sentences:
                    sent_lower = sent.lower()
                    sent_words = set(re.findall(r'\w{4,}', sent_lower))

                    if not sent_words:
                        continue

                    # Exact / Near-verbatim substring match
                    if len(stext_clean) > 20 and (stext_clean.lower() in sent_lower or sent_lower in stext_clean.lower()):
                        finding = SourceGroundingFinding(
                            claim=sent,
                            source_ids=[sid],
                            support_type=GroundingSupportType.DIRECTLY_SUPPORTED,
                            evidence=stext_clean[:120],
                            confidence=1.0,
                            severity=ViolationSeverity.INFO
                        )
                        details["findings"].append(finding.model_dump())
                        details["support_counts"][GroundingSupportType.DIRECTLY_SUPPORTED.value] += 1
                        break

                    # Significant word / root overlap (Paraphrase match)
                    overlap = len(sent_words.intersection(stext_words))
                    sent_roots = {w[:4] for w in sent_words}
                    stext_roots = {w[:4] for w in stext_words}
                    overlap_roots = len(sent_roots.intersection(stext_roots))

                    if overlap >= 3 or overlap_roots >= 3 or (overlap_roots >= 2 and len(sent_roots) <= 8):
                        finding = SourceGroundingFinding(
                            claim=sent,
                            source_ids=[sid],
                            support_type=GroundingSupportType.PARAPHRASE_SUPPORTED,
                            evidence=stext_clean[:120],
                            confidence=0.90,
                            severity=ViolationSeverity.INFO
                        )
                        details["findings"].append(finding.model_dump())
                        details["support_counts"][GroundingSupportType.PARAPHRASE_SUPPORTED.value] += 1
                        break
        else:
            details["support_counts"][GroundingSupportType.UNKNOWN.value] += 1

        # ── 4. Unsupported Authority Claims ──
        for s in doc.sections:
            if "according to the verified source" in s.content.lower() and not doc.source_citations:
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
                finding = SourceGroundingFinding(
                    claim=s.title,
                    source_ids=[],
                    support_type=GroundingSupportType.UNSUPPORTED,
                    evidence=None,
                    confidence=0.90,
                    severity=ViolationSeverity.WARNING
                )
                details["findings"].append(finding.model_dump())
                details["support_counts"][GroundingSupportType.UNSUPPORTED.value] += 1

        return violations, details, max(0.0, min(100.0, score))
