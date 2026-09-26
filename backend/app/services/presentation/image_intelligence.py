"""
LearnByGenie PPT vNext — Phase 3.4 Image Intelligence Engine
===========================================================
Implements typed image-need assessment, semantic query construction,
candidate relevance ranking, asset decision routing, and fallback orchestration.

Governance:
  - Consumes frozen VisualSemanticPacket, SlideContent, ContentBinding,
    CompositionInputManifest, DesignDNA, and SlideCompositionPlan.
  - Never regenerates slide content or recalculates layout families.
  - Never replaces an approved editable chart or diagram with a raster image.
  - Uses transparent multi-factor relevance scoring (not a single opaque AI score).
  - Records rejection reasons for every discarded candidate.
  - Produces typed ImageAssetDecision with full provenance.
"""
from __future__ import annotations

import hashlib
import time
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple

from pydantic import BaseModel, Field

from app.services.presentation.schemas import SlideContent
from app.services.presentation.visual_schemas import (
    VisualSemanticPacket,
    VisualAssetType,
    VisualIntent,
    DesignDNA,
)
from app.services.presentation.composition_schemas import (
    ResolvedRegionBounds,
    ContentBinding,
    ContentRegion,
    RegionSemanticRole,
)


# ═══════════════════════════════════════════════════════════════
# 1. IMAGE ASSET DECISION OUTCOMES
# ═══════════════════════════════════════════════════════════════

class ImageDecisionOutcome(str, Enum):
    """Typed outcomes for image-need assessment."""
    IMAGE_REQUIRED       = "image_required"
    IMAGE_USEFUL         = "image_useful"
    IMAGE_OPTIONAL       = "image_optional"
    IMAGE_UNNECESSARY    = "image_unnecessary"
    DIAGRAM_PREFERRED    = "diagram_preferred"
    CHART_PREFERRED      = "chart_preferred"
    IMAGE_DEFERRED       = "image_deferred"
    IMAGE_UNAVAILABLE    = "image_unavailable"


class ImageTypeClassification(str, Enum):
    """Semantic image category classification."""
    PHOTOGRAPH              = "photograph"
    SCIENTIFIC_ILLUSTRATION = "scientific_illustration"
    HISTORICAL_IMAGE        = "historical_image"
    OBJECT_REFERENCE        = "object_reference"
    DOCUMENTARY_IMAGE       = "documentary_image"
    MAP_REFERENCE           = "map_reference"
    BACKGROUND_TEXTURE      = "background_texture"
    DECORATIVE_IMAGE        = "decorative_image"
    EXISTING_SOURCE_IMAGE   = "existing_source_image"


class CropMode(str, Enum):
    """Image cropping strategy for region placement."""
    CONTAIN          = "contain"
    COVER            = "cover"
    SMART_CROP       = "smart_crop"
    NO_CROP          = "no_crop"
    BACKGROUND_CROP  = "background_crop"


class ImageDefectCode(str, Enum):
    """Structured defect codes for image quality auditing."""
    IMAGE_SEMANTIC_MISMATCH          = "IMAGE_SEMANTIC_MISMATCH"
    IMAGE_RIGHTS_UNVERIFIED          = "IMAGE_RIGHTS_UNVERIFIED"
    IMAGE_RESOLUTION_INSUFFICIENT    = "IMAGE_RESOLUTION_INSUFFICIENT"
    IMAGE_ASPECT_RATIO_INCOMPATIBLE  = "IMAGE_ASPECT_RATIO_INCOMPATIBLE"
    IMAGE_CROP_UNSAFE                = "IMAGE_CROP_UNSAFE"
    IMAGE_FILE_CORRUPT               = "IMAGE_FILE_CORRUPT"
    IMAGE_FORMAT_UNSUPPORTED         = "IMAGE_FORMAT_UNSUPPORTED"
    IMAGE_SOURCE_UNAVAILABLE         = "IMAGE_SOURCE_UNAVAILABLE"
    IMAGE_DOWNLOAD_FAILED            = "IMAGE_DOWNLOAD_FAILED"
    IMAGE_DUPLICATE_UNJUSTIFIED      = "IMAGE_DUPLICATE_UNJUSTIFIED"
    IMAGE_ALT_TEXT_MISSING           = "IMAGE_ALT_TEXT_MISSING"
    IMAGE_ATTRIBUTION_MISSING        = "IMAGE_ATTRIBUTION_MISSING"
    IMAGE_REGION_MAPPING_INVALID     = "IMAGE_REGION_MAPPING_INVALID"
    IMAGE_PROVENANCE_INCOMPLETE      = "IMAGE_PROVENANCE_INCOMPLETE"
    IMAGE_RENDERING_FAILED           = "IMAGE_RENDERING_FAILED"


# ═══════════════════════════════════════════════════════════════
# 2. IMAGE PROVENANCE & RIGHTS METADATA
# ═══════════════════════════════════════════════════════════════

class ImageRightsMetadata(BaseModel):
    """Traceable rights metadata for every externally sourced asset."""
    provider: str = ""
    original_source_url: str = ""
    asset_identifier: str = ""
    creator: str = ""
    license_or_usage_terms: str = ""
    retrieval_timestamp: str = ""
    attribution_requirement: bool = False
    attribution_text: str = ""
    permitted_usage_scope: str = "educational"
    source_metadata: Dict[str, Any] = Field(default_factory=dict)
    content_hash: str = ""
    rights_verified: bool = False


class ImageProvenance(BaseModel):
    """Full provenance record for an image placed in a deck."""
    slide_no: int = 0
    region_id: str = ""
    source_binding_hash: str = ""
    asset_identifier: str = ""
    source_hash: str = ""
    downloaded_asset_hash: str = ""
    rights_metadata: ImageRightsMetadata = Field(default_factory=ImageRightsMetadata)
    pptx_picture_shape_id: int = 0
    alt_text: str = ""
    image_type: ImageTypeClassification = ImageTypeClassification.PHOTOGRAPH
    crop_mode: CropMode = CropMode.CONTAIN
    image_width_px: int = 0
    image_height_px: int = 0
    file_size_bytes: int = 0
    search_query_used: str = ""
    candidate_count: int = 0
    selection_rationale: str = ""
    rejection_reasons: List[str] = Field(default_factory=list)


class ImageAssetDecision(BaseModel):
    """Typed image-need assessment result for a single slide region."""
    slide_no: int = 0
    region_id: str = ""
    outcome: ImageDecisionOutcome = ImageDecisionOutcome.IMAGE_UNNECESSARY
    image_type: ImageTypeClassification = ImageTypeClassification.PHOTOGRAPH
    rationale: str = ""
    search_query: str = ""
    fallback_reason: str = ""
    defects: List[ImageDefectCode] = Field(default_factory=list)
    provenance: Optional[ImageProvenance] = None
    image_bytes: Optional[bytes] = None
    crop_mode: CropMode = CropMode.CONTAIN
    alt_text: str = ""
    estimated_api_cost: float = 0.0

    model_config = {"arbitrary_types_allowed": True}


class ImageRelevanceScore(BaseModel):
    """Transparent multi-factor relevance scoring for a candidate image."""
    semantic_relevance: float = 0.0    # 0.0 - 1.0
    subject_correctness: float = 0.0   # 0.0 - 1.0
    visual_clarity: float = 0.0        # 0.0 - 1.0
    source_reliability: float = 0.0    # 0.0 - 1.0
    rights_suitability: float = 0.0    # 0.0 - 1.0 (hard gate: 0.0 = ineligible)
    resolution_adequacy: float = 0.0   # 0.0 - 1.0
    aspect_ratio_fit: float = 0.0      # 0.0 - 1.0
    contextual_appropriateness: float = 0.0
    composite_score: float = 0.0       # weighted combination
    rejection_reason: str = ""         # non-empty if rejected

    def compute_composite(self) -> float:
        """Computes weighted composite. Rights=hard gate (score=0 if unverified)."""
        if self.rights_suitability < 0.5:
            self.composite_score = 0.0
            self.rejection_reason = "Rights suitability below threshold"
            return 0.0
        weights = {
            "semantic_relevance": 0.30,
            "subject_correctness": 0.25,
            "visual_clarity": 0.10,
            "source_reliability": 0.10,
            "resolution_adequacy": 0.10,
            "aspect_ratio_fit": 0.10,
            "contextual_appropriateness": 0.05,
        }
        self.composite_score = sum(
            getattr(self, k, 0.0) * w for k, w in weights.items()
        )
        return self.composite_score


class ImageCandidate(BaseModel):
    """A scored image candidate from provider search."""
    provider: str = ""
    image_url: str = ""
    asset_id: str = ""
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    width_px: int = 0
    height_px: int = 0
    content_hash: str = ""
    rights: ImageRightsMetadata = Field(default_factory=ImageRightsMetadata)
    score: ImageRelevanceScore = Field(default_factory=ImageRelevanceScore)
    image_bytes: Optional[bytes] = None

    model_config = {"arbitrary_types_allowed": True}


# ═══════════════════════════════════════════════════════════════
# 3. TELEMETRY
# ═══════════════════════════════════════════════════════════════

class ImageTelemetry(BaseModel):
    """Cost and performance telemetry for image intelligence operations."""
    provider_requests: int = 0
    cache_hits: int = 0
    successful_retrievals: int = 0
    failed_retrievals: int = 0
    timeouts: int = 0
    quota_errors: int = 0
    asset_reuse_count: int = 0
    estimated_cost_usd: float = 0.0
    decision_latency_ms: float = 0.0
    retrieval_latency_ms: float = 0.0
    validation_latency_ms: float = 0.0
    processing_latency_ms: float = 0.0
    pptx_insertion_latency_ms: float = 0.0
    total_image_bytes: int = 0
    images_placed: int = 0
    images_rejected: int = 0
    cost_status: str = "MEASURED"  # "MEASURED" | "COST_UNKNOWN"


# ═══════════════════════════════════════════════════════════════
# 4. IMAGE NEED ASSESSMENT
# ═══════════════════════════════════════════════════════════════

# Visual intents that semantically prefer diagrams/charts over photographs
_DIAGRAM_PREFERRED_INTENTS = {
    VisualIntent.SHOW_PROCESS,
    VisualIntent.SHOW_CAUSALITY,
    VisualIntent.SHOW_HIERARCHY,
    VisualIntent.SHOW_SYSTEM_ARCHITECTURE,
    VisualIntent.SHOW_RELATIONSHIP,
    VisualIntent.SHOW_FORMULA,
    VisualIntent.SHOW_TRANSFORMATION,
}

_CHART_PREFERRED_INTENTS = {
    VisualIntent.SHOW_DATA_PATTERN,
}

_IMAGE_SUPPORTIVE_INTENTS = {
    VisualIntent.SHOW_OBJECT,
    VisualIntent.SHOW_LOCATION,
    VisualIntent.SHOW_EVIDENCE,
    VisualIntent.SHOW_EXAMPLE,
    VisualIntent.EXPLAIN_STRUCTURE,
}


def assess_image_need(
    packet: Optional[VisualSemanticPacket],
    content: Optional[SlideContent],
    region: ContentRegion,
) -> ImageAssetDecision:
    """
    Evaluates whether a slide region genuinely needs a photographic/illustration image.
    Uses semantic context — never inserts images purely to fill space.
    """
    decision = ImageAssetDecision(
        slide_no=packet.slide_no if packet else 0,
        region_id=region.region_id,
    )

    role = region.semantic_role

    # Non-visual regions never need images
    if role not in {
        RegionSemanticRole.PRIMARY_VISUAL,
        RegionSemanticRole.SECONDARY_VISUAL,
        RegionSemanticRole.BLEED_BACKGROUND,
    }:
        decision.outcome = ImageDecisionOutcome.IMAGE_UNNECESSARY
        decision.rationale = f"Region role '{role.value}' is not a visual region"
        return decision

    if not packet:
        decision.outcome = ImageDecisionOutcome.IMAGE_UNNECESSARY
        decision.rationale = "No VisualSemanticPacket available"
        return decision

    intent = packet.visual_intent

    # If chart or diagram is semantically preferred, defer to those engines
    if intent in _CHART_PREFERRED_INTENTS:
        decision.outcome = ImageDecisionOutcome.CHART_PREFERRED
        decision.rationale = f"Visual intent '{intent.value}' is best served by a native chart"
        return decision

    if intent in _DIAGRAM_PREFERRED_INTENTS:
        # Check if packet has relationship/process structures that diagram engine handles
        has_diagram_data = bool(
            packet.relationships or packet.causal_structure or
            packet.process_nodes or packet.temporal_structure or
            packet.hierarchy_tree or packet.system_components
        )
        if has_diagram_data:
            decision.outcome = ImageDecisionOutcome.DIAGRAM_PREFERRED
            decision.rationale = f"Visual intent '{intent.value}' with structured relationship data prefers editable diagram"
            return decision

    # Image-supportive intents with image candidates
    if packet.image_candidate_concepts:
        if intent in _IMAGE_SUPPORTIVE_INTENTS:
            decision.outcome = ImageDecisionOutcome.IMAGE_REQUIRED
            decision.rationale = f"Visual intent '{intent.value}' with image candidates: {packet.image_candidate_concepts[:3]}"
        else:
            decision.outcome = ImageDecisionOutcome.IMAGE_USEFUL
            decision.rationale = f"Image candidates available: {packet.image_candidate_concepts[:3]}"

        # Build semantic search query
        decision.search_query = build_semantic_query(packet, content)
        decision.image_type = classify_image_type(packet, content)
        return decision

    # Visual region with visual content intent but no image candidates
    if role == RegionSemanticRole.BLEED_BACKGROUND:
        decision.outcome = ImageDecisionOutcome.IMAGE_OPTIONAL
        decision.rationale = "Background region may benefit from contextual texture"
        decision.image_type = ImageTypeClassification.BACKGROUND_TEXTURE
        decision.search_query = build_semantic_query(packet, content)
        return decision

    # Default: image unnecessary when no image candidates and no strong image intent
    decision.outcome = ImageDecisionOutcome.IMAGE_UNNECESSARY
    decision.rationale = "No image candidates and no strong visual intent requiring photography"
    return decision


# ═══════════════════════════════════════════════════════════════
# 5. SEMANTIC QUERY CONSTRUCTION
# ═══════════════════════════════════════════════════════════════

def build_semantic_query(
    packet: Optional[VisualSemanticPacket],
    content: Optional[SlideContent],
) -> str:
    """
    Constructs a contextual image search query from verified semantic data.
    Avoids generic queries; combines subject, domain entities, and visual intent.
    Never includes private or sensitive information.
    """
    if not packet:
        return ""

    parts: List[str] = []

    # Primary visual message (most specific)
    if packet.primary_visual_message:
        # Extract key noun phrases, limit length
        msg = packet.primary_visual_message.strip()
        if len(msg) > 80:
            msg = msg[:80]
        parts.append(msg)

    # Key entities (top 3)
    for entity in packet.key_entities[:3]:
        if entity and entity.strip() not in [p.lower() for p in parts]:
            parts.append(entity.strip())

    # Image candidate concepts
    for concept in packet.image_candidate_concepts[:2]:
        if concept and concept.strip().lower() not in [p.lower() for p in parts]:
            parts.append(concept.strip())

    # Content title for context
    if content and content.title:
        title_words = content.title.strip()
        if title_words.lower() not in [p.lower() for p in parts]:
            parts.append(title_words)

    # Intent qualifier
    intent_qualifiers = {
        VisualIntent.SHOW_OBJECT: "reference photograph",
        VisualIntent.SHOW_LOCATION: "geographical reference",
        VisualIntent.SHOW_EVIDENCE: "documentary evidence",
        VisualIntent.EXPLAIN_STRUCTURE: "labeled educational illustration",
        VisualIntent.SHOW_EXAMPLE: "example illustration",
        VisualIntent.HERO_STATEMENT: "professional background",
    }
    if packet.visual_intent in intent_qualifiers:
        parts.append(intent_qualifiers[packet.visual_intent])

    # Quality qualifier
    parts.append("educational")

    query = " ".join(parts[:6])  # Cap at 6 terms for precision
    return query.strip()


def classify_image_type(
    packet: Optional[VisualSemanticPacket],
    content: Optional[SlideContent],
) -> ImageTypeClassification:
    """Classifies the semantic image type based on slide intent and content."""
    if not packet:
        return ImageTypeClassification.PHOTOGRAPH

    intent = packet.visual_intent

    # Scientific/biological content
    if any(kw in (packet.primary_visual_message or "").lower()
           for kw in ["cell", "organism", "molecule", "dna", "anatomy", "tissue",
                       "chemical", "microscope", "biology", "organ"]):
        return ImageTypeClassification.SCIENTIFIC_ILLUSTRATION

    # Historical content
    if any(kw in (packet.primary_visual_message or "").lower()
           for kw in ["historical", "century", "ancient", "medieval", "colonial",
                       "war", "revolution", "empire"]):
        return ImageTypeClassification.HISTORICAL_IMAGE

    # Location/geographic
    if intent == VisualIntent.SHOW_LOCATION:
        return ImageTypeClassification.MAP_REFERENCE

    # Object reference
    if intent == VisualIntent.SHOW_OBJECT:
        return ImageTypeClassification.OBJECT_REFERENCE

    # Evidence/documentary
    if intent == VisualIntent.SHOW_EVIDENCE:
        return ImageTypeClassification.DOCUMENTARY_IMAGE

    return ImageTypeClassification.PHOTOGRAPH


# ═══════════════════════════════════════════════════════════════
# 6. CANDIDATE RELEVANCE SCORING
# ═══════════════════════════════════════════════════════════════

def score_candidate(
    candidate: ImageCandidate,
    query: str,
    target_width_px: int,
    target_height_px: int,
    region_aspect_ratio: float,
) -> ImageRelevanceScore:
    """
    Evaluates an image candidate using transparent multi-factor scoring.
    Rights suitability is a hard gate — ineligible candidates score 0.
    """
    score = ImageRelevanceScore()

    # 1. Semantic relevance: keyword overlap between query and description/tags
    query_words = set(w.lower() for w in query.split() if len(w) > 2)
    desc_text = f"{candidate.description} {' '.join(candidate.tags)}".lower()
    if query_words:
        matched = sum(1 for w in query_words if w in desc_text)
        score.semantic_relevance = min(1.0, matched / max(len(query_words), 1))
    else:
        score.semantic_relevance = 0.5

    # 2. Subject correctness: based on semantic relevance threshold
    score.subject_correctness = score.semantic_relevance  # proportional

    # 3. Visual clarity: based on resolution (higher = clearer)
    total_pixels = candidate.width_px * candidate.height_px
    if total_pixels >= 1_000_000:  # 1MP+
        score.visual_clarity = 1.0
    elif total_pixels >= 500_000:
        score.visual_clarity = 0.8
    elif total_pixels >= 200_000:
        score.visual_clarity = 0.6
    else:
        score.visual_clarity = 0.3

    # 4. Source reliability
    reliable_providers = {"pexels", "unsplash", "pixabay", "wikimedia"}
    score.source_reliability = 1.0 if candidate.provider.lower() in reliable_providers else 0.5

    # 5. Rights suitability (hard gate)
    if candidate.rights.rights_verified:
        score.rights_suitability = 1.0
    elif candidate.provider.lower() in {"pexels", "pixabay", "unsplash"}:
        # These providers serve content under permissive licenses
        score.rights_suitability = 0.9
    elif candidate.provider.lower() == "wikimedia":
        score.rights_suitability = 0.8  # CC licensed, needs attribution
    else:
        score.rights_suitability = 0.0
        score.rejection_reason = "Rights not verified for this provider"

    # 6. Resolution adequacy
    if candidate.width_px >= target_width_px and candidate.height_px >= target_height_px:
        score.resolution_adequacy = 1.0
    elif candidate.width_px >= target_width_px * 0.7 and candidate.height_px >= target_height_px * 0.7:
        score.resolution_adequacy = 0.7
    else:
        score.resolution_adequacy = 0.4

    # 7. Aspect ratio compatibility
    if candidate.width_px > 0 and candidate.height_px > 0:
        cand_ratio = candidate.width_px / candidate.height_px
        ratio_diff = abs(cand_ratio - region_aspect_ratio) / max(region_aspect_ratio, 0.01)
        score.aspect_ratio_fit = max(0.0, 1.0 - ratio_diff * 0.5)
    else:
        score.aspect_ratio_fit = 0.5

    # 8. Contextual appropriateness (assume appropriate unless evidence otherwise)
    score.contextual_appropriateness = 0.8

    score.compute_composite()
    return score


# ═══════════════════════════════════════════════════════════════
# 7. CANDIDATE SELECTION
# ═══════════════════════════════════════════════════════════════

def select_best_candidate(
    candidates: List[ImageCandidate],
    query: str,
    bounds: ResolvedRegionBounds,
    used_hashes: set,
) -> Tuple[Optional[ImageCandidate], List[str]]:
    """
    Selects the best image candidate from scored results.
    Rejects duplicates, low-relevance, and rights-unverified candidates.
    Returns (selected_candidate, rejection_reasons).
    """
    if not candidates:
        return None, ["No candidates available"]

    w_in = float(getattr(bounds, "width_in", getattr(bounds, "width", 7.0)))
    h_in = float(getattr(bounds, "height_in", getattr(bounds, "height", 5.0)))
    target_w = int(w_in * 96)  # approximate DPI
    target_h = int(h_in * 96)
    region_ar = w_in / max(h_in, 0.01)

    rejection_reasons: List[str] = []
    scored: List[Tuple[float, ImageCandidate]] = []

    for cand in candidates:
        score = score_candidate(cand, query, target_w, target_h, region_ar)
        cand.score = score

        # Deduplication check
        if cand.content_hash and cand.content_hash in used_hashes:
            rejection_reasons.append(f"Duplicate hash {cand.content_hash[:12]} from {cand.provider}")
            continue

        if score.rights_suitability < 0.5:
            rejection_reasons.append(f"Rights unverified: {cand.provider}/{cand.asset_id}")
            continue

        if score.composite_score < 0.15:
            rejection_reasons.append(
                f"Low relevance ({score.composite_score:.2f}): {cand.provider}/{cand.asset_id}"
            )
            continue

        scored.append((score.composite_score, cand))

    if not scored:
        return None, rejection_reasons

    # Sort by composite score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1], rejection_reasons


def compute_content_hash(data: bytes) -> str:
    """Compute SHA-256 hash of image bytes for deduplication and provenance."""
    return hashlib.sha256(data).hexdigest()


def determine_crop_mode(
    image_type: ImageTypeClassification,
    region_role: RegionSemanticRole,
    image_ar: float,
    region_ar: float,
) -> CropMode:
    """
    Determines safe cropping strategy based on image purpose and region geometry.
    Scientific illustrations and documentary images use CONTAIN to preserve labels.
    """
    # Scientific/documentary content: never crop critical content
    if image_type in {
        ImageTypeClassification.SCIENTIFIC_ILLUSTRATION,
        ImageTypeClassification.DOCUMENTARY_IMAGE,
        ImageTypeClassification.HISTORICAL_IMAGE,
        ImageTypeClassification.MAP_REFERENCE,
    }:
        return CropMode.CONTAIN

    # Background regions can use aggressive cropping
    if region_role == RegionSemanticRole.BLEED_BACKGROUND:
        return CropMode.BACKGROUND_CROP

    # If aspect ratios are close enough, use cover for cleaner fill
    ar_diff = abs(image_ar - region_ar) / max(region_ar, 0.01)
    if ar_diff < 0.2:
        return CropMode.COVER

    # Default: contain to avoid losing important content
    return CropMode.CONTAIN


def generate_alt_text(
    image_type: ImageTypeClassification,
    search_query: str,
    description: str,
    content_title: str,
) -> str:
    """
    Generates concise, accurate alt text from verified source metadata.
    Does not hallucinate unseen objects or events.
    """
    if image_type == ImageTypeClassification.DECORATIVE_IMAGE:
        return ""  # Decorative images get empty alt text per WCAG

    if description and len(description) > 10:
        # Use verified source description
        alt = description.strip()
        if len(alt) > 125:
            alt = alt[:122] + "..."
        return alt

    # Fall back to search query context + content title
    parts = []
    if content_title:
        parts.append(content_title)
    if search_query:
        # Remove qualifier words
        clean_q = search_query.replace("educational", "").replace("reference photograph", "").strip()
        if clean_q and clean_q not in parts:
            parts.append(clean_q)

    if parts:
        alt = " — ".join(parts[:2])
        if len(alt) > 125:
            alt = alt[:122] + "..."
        return alt


    return "ALT_TEXT_REVIEW_REQUIRED"
