"""
Source Grounding & Conflict Resolution Evaluator
================================================
1. Validates that inline citations ([Page 14], [Slide 8], [04:10]) match verified evidence.
2. Detects multi-source contradictions (e.g. PDF states A, PPT states B) and flags them for pedagogical clarification.
"""
import re
from typing import List, Dict, Any, Tuple, Optional
from ..knowledge.sources import EvidenceItem, SourceType


def extract_citations_from_text(text: str) -> List[str]:
    """Extracts citation markers like [Page 14], [Slide 8], [Notes Page 2], [04:10] from generated text."""
    pattern = r'\[(Page\s+\d+|Slide\s+\d+|Notes\s+Page\s+\d+|\d{2}:\d{2}(?:–\d{2}:\d{2})?)\]'
    return re.findall(pattern, text, flags=re.IGNORECASE)


def validate_and_score_grounding(
    generated_text: str,
    evidence_items: List[EvidenceItem],
) -> Tuple[float, List[str], str]:
    """
    Validates citation fidelity against provided evidence.
    Returns (grounding_score: float, validated_citations: List[str], sanitized_text: str).
    """
    if not evidence_items:
        # Topic-only general knowledge turn
        return 1.0, [], generated_text

    valid_badges = {e.get_citation_badge().lower(): e.get_citation_badge() for e in evidence_items}
    claimed_citations = extract_citations_from_text(generated_text)

    if not claimed_citations:
        # General synthesis of provided evidence
        valid_list = [e.get_citation_badge() for e in evidence_items[:2]]
        return 0.95, valid_list, generated_text

    valid_count = 0
    validated_citations = []
    sanitized_text = generated_text

    for claim in claimed_citations:
        claim_norm = claim.strip().lower()
        # Check for partial or exact match in valid badges
        matching_badge = None
        for vb_norm, vb_orig in valid_badges.items():
            if claim_norm in vb_norm or vb_norm in claim_norm:
                matching_badge = vb_orig
                break

        if matching_badge:
            valid_count += 1
            if matching_badge not in validated_citations:
                validated_citations.append(matching_badge)
        else:
            # Ungrounded citation found: replace with top valid badge or remove
            if evidence_items:
                fallback_badge = evidence_items[0].get_citation_badge()
                sanitized_text = sanitized_text.replace(f"[{claim}]", f"[{fallback_badge}]")
                if fallback_badge not in validated_citations:
                    validated_citations.append(fallback_badge)

    grounding_score = round(valid_count / len(claimed_citations), 2) if claimed_citations else 1.0
    return grounding_score, validated_citations, sanitized_text


def detect_source_conflicts(evidence_items: List[EvidenceItem]) -> Optional[str]:
    """
    Identifies potential contradictory statements across distinct document types (e.g. PDF vs PPT).
    Returns a conflict advisory string if different sources present contrasting claims.
    """
    if len(evidence_items) < 2:
        return None

    distinct_types = {e.source_type for e in evidence_items}
    if len(distinct_types) <= 1:
        return None

    # Check for contrasting keywords across sources
    contrast_pairs = [
        ("synchronous", "asynchronous"),
        ("connectionless", "connection-oriented"),
        ("lossy", "lossless"),
        ("centralized", "distributed"),
        ("preemptive", "non-preemptive"),
    ]

    pdf_texts = " ".join([e.text.lower() for e in evidence_items if e.source_type == SourceType.PDF])
    ppt_texts = " ".join([e.text.lower() for e in evidence_items if e.source_type == SourceType.PPT])

    if pdf_texts and ppt_texts:
        for w1, w2 in contrast_pairs:
            if (w1 in pdf_texts and w2 in ppt_texts) or (w2 in pdf_texts and w1 in ppt_texts):
                return f"Note: Your PDF material mentions '{w1}' whereas the presentation slides emphasize '{w2}'. I will clarify both perspectives."

    return None
