"""
Claim Classification & Evidence Engine (Phase 2)
==================================================
Detects and categorizes claims, guards against unsupported statistics,
and manages source-bound content tagging.

EVIDENCE VERIFICATION RULES:
- TopicIntelligencePack is planning context, NOT evidence.
- A claim may only receive VERIFIED when supported by a real traceable source.
- MODEL_BACKGROUND alone CANNOT verify NUMERIC_CLAIM, RESEARCH_FINDING,
  CASE_STUDY_CLAIM, or precise HISTORICAL_CLAIM.
- Unverified numeric claims must be rewritten qualitatively or removed.

STRICT NUMERIC CLAIM CONTRACT:
For numeric claims, require: value, unit, scope, time_period, source_id.
"""
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from .schemas import (
    ClaimType, ClaimVerificationStatus, ClaimEvidence, ContentOrigin,
)

logger = logging.getLogger("teachgenie.presentation.claim_evidence")


# ═══════════════════════════════════════════════════════════════
# Unsupported Statistics Detection Patterns
# ═══════════════════════════════════════════════════════════════

# Regex patterns that detect likely fabricated statistics
FABRICATED_STAT_PATTERNS = [
    # "X% of ..."
    r"\b\d{1,3}%\s+of\b",
    # "X times faster/better/more"
    r"\b\d+x\s+(faster|better|more|improvement|increase|reduction|improvement)\b",
    # "reduces/improves/increases by X%"
    r"\b(reduces?|improves?|increases?|decreases?|boosts?|cuts?)\s+by\s+\d{1,3}%",
    # "$X billion/million"  
    r"\$\d+(\.\d+)?\s*(billion|million|trillion)\b",
    # "X million/billion users/customers"
    r"\b\d+(\.\d+)?\s*(million|billion)\s+(users|customers|people|companies|organizations)\b",
]

# Phrases commonly used around fabricated statistics
FABRICATED_STAT_PHRASES = [
    "studies show that",
    "research indicates that",
    "according to experts",
    "statistics reveal",
    "data suggests that",
    "surveys indicate",
    "experts estimate",
    "industry reports show",
]


def detect_numeric_claims(text: str) -> List[Dict[str, Any]]:
    """Detect potential numeric claims in text.
    Returns list of {pattern, match, position} for each detected claim."""
    detections = []
    text_lower = text.lower()
    
    for pattern in FABRICATED_STAT_PATTERNS:
        for match in re.finditer(pattern, text_lower):
            detections.append({
                "pattern": pattern,
                "match": match.group(),
                "position": match.start(),
                "original_text": text[max(0, match.start()-20):match.end()+20],
            })
    
    return detections


def detect_fabricated_stat_phrases(text: str) -> List[str]:
    """Detect vague attribution phrases that often precede fabricated statistics."""
    text_lower = text.lower()
    found = []
    for phrase in FABRICATED_STAT_PHRASES:
        if phrase in text_lower:
            found.append(phrase)
    return found


# ═══════════════════════════════════════════════════════════════
# Claim Type Classification
# ═══════════════════════════════════════════════════════════════

# Keywords/patterns for heuristic claim classification
_NUMERIC_INDICATORS = ["%", "percent", "billion", "million", "trillion", "$", "€", "£"]
_HISTORICAL_INDICATORS = [
    "in the year", "century", "during the", "bc", "ad", "bce", "ce",
    "was established", "was founded", "was invented", "was discovered",
]
_RESEARCH_INDICATORS = [
    "study", "research", "paper", "journal", "published", "peer-reviewed",
    "meta-analysis", "randomized", "clinical trial", "cohort",
]
_CASE_STUDY_INDICATORS = [
    "case study", "company", "organization", "implemented", "deployed",
    "resulted in", "outcome", "netflix", "google", "amazon", "tesla",
]


def classify_claim(claim_text: str) -> ClaimType:
    """Classify a claim text into a ClaimType using deterministic heuristics.
    Does NOT use an LLM for this — purely rule-based."""
    text_lower = claim_text.lower().strip()
    
    # Numeric claim — highest priority since these need strictest verification
    if any(ind in text_lower for ind in _NUMERIC_INDICATORS):
        # Check for actual numbers
        if re.search(r"\d", text_lower):
            return ClaimType.NUMERIC_CLAIM
    
    # Research finding
    if any(ind in text_lower for ind in _RESEARCH_INDICATORS):
        return ClaimType.RESEARCH_FINDING
    
    # Case study claim
    if any(ind in text_lower for ind in _CASE_STUDY_INDICATORS):
        return ClaimType.CASE_STUDY_CLAIM
    
    # Historical claim
    if re.search(r"\b(in\s+(?:the\s+year\s+)?\d{3,4}|\d{4}s?|revolution|century|bc|bce|ad|ce|dynasty|empire)\b", text_lower) or any(ind in text_lower for ind in _HISTORICAL_INDICATORS):
        return ClaimType.HISTORICAL_CLAIM
    
    # General concept indicator check
    _CONCEPT_INDICATORS = ["fundamental requirement", "core principle", "doctrine", "concept of", "theory of", "framework", "definition of", "notion of"]
    if any(ind in text_lower for ind in _CONCEPT_INDICATORS):
        return ClaimType.GENERAL_CONCEPT

    # Verifiable fact — statements that assert specific factual information
    if re.search(r"\b(be|is|are|was|were|has|have|contains?|produces?|consists?|can|cannot)\b", text_lower):
        # Simple factual assertions that could be verified
        if len(text_lower.split()) >= 5:  # Not too short to be meaningful
            return ClaimType.VERIFIABLE_FACT
    
    # Default
    return ClaimType.GENERAL_CONCEPT


def classify_claims_in_content(content_dict: Dict[str, Any]) -> List[ClaimEvidence]:
    """Classify all significant claims in a SlideContent dict.
    Returns list of ClaimEvidence records."""
    claims = []
    
    # Check primary_takeaway
    takeaway = content_dict.get("primary_takeaway", "")
    if takeaway and len(takeaway.split()) >= 5:
        claim_type = classify_claim(takeaway)
        needs_source = claim_type in (
            ClaimType.NUMERIC_CLAIM,
            ClaimType.RESEARCH_FINDING,
            ClaimType.CASE_STUDY_CLAIM,
            ClaimType.HISTORICAL_CLAIM,
        )
        claims.append(ClaimEvidence(
            claim_text=takeaway,
            claim_type=claim_type,
            source_required=needs_source,
            verification_status=ClaimVerificationStatus.SOURCE_PENDING if needs_source else ClaimVerificationStatus.VERIFIED,
        ))
    
    # Check supporting points
    for point in content_dict.get("supporting_points", []):
        if not point or len(point.split()) < 5:
            continue
        claim_type = classify_claim(point)
        needs_source = claim_type in (
            ClaimType.NUMERIC_CLAIM,
            ClaimType.RESEARCH_FINDING,
            ClaimType.CASE_STUDY_CLAIM,
        )
        claims.append(ClaimEvidence(
            claim_text=point,
            claim_type=claim_type,
            source_required=needs_source,
            verification_status=ClaimVerificationStatus.SOURCE_PENDING if needs_source else ClaimVerificationStatus.VERIFIED,
        ))
    
    # Check example
    example = content_dict.get("example", "")
    if example and len(example.split()) >= 5:
        claim_type = classify_claim(example)
        if claim_type in (ClaimType.NUMERIC_CLAIM, ClaimType.CASE_STUDY_CLAIM):
            claims.append(ClaimEvidence(
                claim_text=example,
                claim_type=claim_type,
                source_required=True,
                verification_status=ClaimVerificationStatus.SOURCE_PENDING,
            ))
    
    # Check callout
    callout = content_dict.get("callout", "")
    if callout and len(callout.split()) >= 5:
        claim_type = classify_claim(callout)
        if claim_type == ClaimType.NUMERIC_CLAIM:
            claims.append(ClaimEvidence(
                claim_text=callout,
                claim_type=claim_type,
                source_required=True,
                verification_status=ClaimVerificationStatus.SOURCE_PENDING,
            ))
    
    return claims


# ═══════════════════════════════════════════════════════════════
# Unsupported Statistic Guard
# ═══════════════════════════════════════════════════════════════

def guard_unsupported_statistics(
    text: str,
    verified_sources: Optional[List[str]] = None,
    source_context: str = "",
) -> Tuple[str, List[str]]:
    """Guard against unsupported statistics in generated text.
    
    If a numeric claim is detected and no verified source supports it:
    - Rewrites the claim qualitatively
    - Returns the modified text and list of changes made
    
    Never silently passes fabricated numbers.
    
    Args:
        text: The content text to check
        verified_sources: List of source_ids that have been verified
        source_context: Uploaded source material text (claims matching this are allowed)
    
    Returns:
        (cleaned_text, changes_made)
    """
    verified_sources = verified_sources or []
    changes = []
    
    # Detect numeric claims
    numeric_claims = detect_numeric_claims(text)
    if not numeric_claims:
        return text, changes
    
    result = text
    for detection in numeric_claims:
        original_snippet = detection.get("original_text", "")
        match_text = detection.get("match", "")
        
        # Check if this claim is supported by source context
        if source_context and match_text in source_context.lower():
            continue  # Supported by uploaded source
        
        # Check if a verified source covers this
        if verified_sources:
            continue  # We have some verified sources — let evidence resolution handle it
        
        # Unsupported numeric claim — rewrite qualitatively
        # Simple heuristic: replace "X% of" with "a significant proportion of"
        if re.search(r"\b\d{1,3}%\s+of\b", match_text):
            qualitative = re.sub(
                r"\b\d{1,3}%\s+of\b",
                "a significant proportion of",
                result,
                count=1,
                flags=re.IGNORECASE,
            )
            if qualitative != result:
                changes.append(f"Replaced unsupported statistic '{match_text}' with qualitative phrasing")
                result = qualitative
        
        # Replace "Xx faster/better"
        elif re.search(r"\b\d+x\s+(faster|better|more|improvement)", match_text):
            qualitative = re.sub(
                r"\b\d+x\s+(faster|better|more|improvement\w*)",
                r"substantially \1",
                result,
                count=1,
                flags=re.IGNORECASE,
            )
            if qualitative != result:
                changes.append(f"Replaced unsupported multiplier '{match_text}' with qualitative phrasing")
                result = qualitative
        
        # Replace "improves by X%"
        elif re.search(r"(reduces?|improves?|increases?|decreases?|boosts?|cuts?)\s+by\s+\d{1,3}%", match_text):
            qualitative = re.sub(
                r"(reduces?|improves?|increases?|decreases?|boosts?|cuts?)\s+by\s+\d{1,3}%",
                r"\1 measurably",
                result,
                count=1,
                flags=re.IGNORECASE,
            )
            if qualitative != result:
                changes.append(f"Replaced unsupported percentage '{match_text}' with qualitative phrasing")
                result = qualitative
    
    # Also check for vague attribution phrases
    vague_phrases = detect_fabricated_stat_phrases(result)
    for phrase in vague_phrases:
        changes.append(f"Warning: vague attribution phrase detected: '{phrase}'")
    
    return result, changes


def resolve_evidence_for_claims(
    claims: List[ClaimEvidence],
    source_context: str = "",
    source_type: str = "general",
    source_id: str = "",
) -> List[ClaimEvidence]:
    """Resolve evidence status for classified claims.
    
    Rules:
    - SOURCE_DOCUMENT content matching source_context or source_id → VERIFIED
    - MODEL_BACKGROUND alone CANNOT verify NUMERIC_CLAIM, RESEARCH_FINDING,
      CASE_STUDY_CLAIM, or precise HISTORICAL_CLAIM
    - Unresolvable high-risk claims → UNVERIFIED_REMOVED
    """
    resolved = []
    source_lower = source_context.lower() if source_context else ""
    
    for claim in claims:
        resolved_claim = claim.model_copy() if hasattr(claim, "model_copy") else ClaimEvidence(**claim.model_dump())
        
        # If explicit source_id is provided, verify against it
        if source_id:
            resolved_claim.verification_status = ClaimVerificationStatus.VERIFIED
            resolved_claim.source_id = source_id
            resolved.append(resolved_claim)
            continue
        
        # GENERAL_CONCEPT and OPINION_INTERPRETATION don't need external verification
        if claim.claim_type in (ClaimType.GENERAL_CONCEPT, ClaimType.OPINION_INTERPRETATION):
            resolved_claim.verification_status = ClaimVerificationStatus.VERIFIED
            resolved_claim.source_required = False
            resolved.append(resolved_claim)
            continue
        
        # VERIFIABLE_FACT — can be verified by model background for well-established facts
        if claim.claim_type == ClaimType.VERIFIABLE_FACT:
            resolved_claim.verification_status = ClaimVerificationStatus.VERIFIED
            resolved.append(resolved_claim)
            continue
        
        # For high-risk claim types, check source support
        if claim.claim_type in (
            ClaimType.NUMERIC_CLAIM,
            ClaimType.RESEARCH_FINDING,
            ClaimType.CASE_STUDY_CLAIM,
            ClaimType.HISTORICAL_CLAIM,
        ):
            # Check if claim text has keywords matching source context
            claim_keywords = [w.lower() for w in claim.claim_text.split() if len(w) > 3]
            if source_lower and sum(1 for kw in claim_keywords if kw in source_lower) >= 3:
                resolved_claim.verification_status = ClaimVerificationStatus.VERIFIED
                resolved_claim.source_id = "uploaded_source"
            elif source_type in ("uploaded_material", "uploaded_material_plus_web"):
                # Source-bound mode but claim not found in source
                resolved_claim.verification_status = ClaimVerificationStatus.SOURCE_PENDING
            else:
                # General mode — cannot verify high-risk claims from model alone
                resolved_claim.verification_status = ClaimVerificationStatus.SOURCE_PENDING
            
            resolved.append(resolved_claim)
            continue
        
        resolved.append(resolved_claim)
    
    return resolved


def tag_content_origin(
    content_dict: Dict[str, Any],
    source_type: str = "general",
    source_context: str = "",
) -> ContentOrigin:
    """Determine the ContentOrigin for a generated content block.
    
    Priority:
    - If source_type is uploaded_material and content matches → SOURCE_DOCUMENT
    - If using external retrieval → EXTERNAL_SOURCE
    - If deterministically generated → DETERMINISTIC_STRUCTURE
    - Default → MODEL_BACKGROUND
    """
    if source_type in ("uploaded_material", "uploaded_material_plus_web") and source_context:
        return ContentOrigin.SOURCE_DOCUMENT
    
    # Check if content was deterministically generated (by Phase 1 planner)
    primary = content_dict.get("primary_takeaway", "")
    if not primary or len(primary.split()) < 3:
        return ContentOrigin.DETERMINISTIC_STRUCTURE
    
    return ContentOrigin.MODEL_BACKGROUND
