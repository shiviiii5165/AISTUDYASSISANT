"""
TeachGenie vNEXT Phase 3.1 — Visual Story Rhythm Planner
=========================================================
Generates DeckVisualRhythmPlan that orchestrates visual pacing across slides.

Governance:
  - Consumes VisualSemanticPacket (from interpreter) + DesignDNA (from design_dna).
  - Enforces rhythm constraints:
      • Maximum consecutive identical layout streak ≤ 2
      • Card-cluster usage capped at ≤ 25% of total slides
  - Zero topic-name branching.
  - All layout choices derive from visual intent, design DNA preferences,
    and deck-wide variety optimization.
"""
from app.core.logging import logger
from typing import List, Dict, Optional
from collections import Counter

from .visual_schemas import (
    VisualIntent,
    VisualAssetType,
    Phase3LayoutFamily,
    VisualWeight,
    VisualRhythmBeat,
    DeckVisualRhythmPlan,
    VisualSemanticPacket,
    DesignDNA,
)


# ═══════════════════════════════════════════════════════════════
# CONSTRAINTS
# ═══════════════════════════════════════════════════════════════

MAX_CONSECUTIVE_LAYOUT_STREAK = 2
MAX_CARD_CLUSTER_PERCENTAGE = 0.25


# ═══════════════════════════════════════════════════════════════
# VISUAL WEIGHT DERIVATION
# ═══════════════════════════════════════════════════════════════

def _derive_visual_weight(packet: VisualSemanticPacket) -> VisualWeight:
    """Derive visual weight from semantic packet visual priority and intent."""
    if packet.visual_priority >= 0.7:
        return VisualWeight.DOMINANT
    elif packet.visual_priority >= 0.4:
        return VisualWeight.MEDIUM
    else:
        return VisualWeight.LIGHT


# ═══════════════════════════════════════════════════════════════
# BEST ASSET & LAYOUT SELECTION
# ═══════════════════════════════════════════════════════════════

def _select_best_asset(
    packet: VisualSemanticPacket,
    dna: DesignDNA,
) -> VisualAssetType:
    """Select best asset type from visual candidates, considering DesignDNA preferences."""
    if packet.visual_candidates:
        return packet.visual_candidates[0].asset_type
    return VisualAssetType.TEXTUAL_STATEMENT


def _select_best_layout(
    packet: VisualSemanticPacket,
    dna: DesignDNA,
    recent_layouts: List[Phase3LayoutFamily],
) -> Phase3LayoutFamily:
    """Select best layout considering DNA preferences and streak avoidance.

    Args:
        packet: Semantic packet with ranked candidates
        dna: DesignDNA with preferred compositions
        recent_layouts: Last N layouts assigned (for streak detection)

    Returns:
        Phase3LayoutFamily that avoids consecutive streaks
    """
    # Collect candidate layouts in preference order
    candidate_layouts: List[Phase3LayoutFamily] = []

    # From visual candidates
    if packet.visual_candidates:
        for vc in packet.visual_candidates:
            if vc.layout_family not in candidate_layouts:
                candidate_layouts.append(vc.layout_family)

    # From DNA preferences
    for pref in dna.preferred_composition_families:
        if pref not in candidate_layouts:
            candidate_layouts.append(pref)

    # Fallback
    if not candidate_layouts:
        candidate_layouts = [Phase3LayoutFamily.TEXT_DOMINANT]

    # Check for streak violation and choose the best non-violating option
    if len(recent_layouts) >= MAX_CONSECUTIVE_LAYOUT_STREAK:
        last_n = recent_layouts[-MAX_CONSECUTIVE_LAYOUT_STREAK:]
        if all(layout == last_n[0] for layout in last_n):
            # The streak is at max — must pick a different layout
            streak_layout = last_n[0]
            for candidate in candidate_layouts:
                if candidate != streak_layout:
                    return candidate
            # If all candidates are the same, force a different one
            for fallback in Phase3LayoutFamily:
                if fallback != streak_layout:
                    return fallback

    return candidate_layouts[0]


# ═══════════════════════════════════════════════════════════════
# CARD CLUSTER CAP ENFORCEMENT
# ═══════════════════════════════════════════════════════════════

def _enforce_card_cluster_cap(
    beats: List[VisualRhythmBeat],
    total_slides: int,
) -> List[VisualRhythmBeat]:
    """Ensure card-cluster usage doesn't exceed 25% of total slides.
    Replaces excess card clusters with the next-best alternative."""
    max_card_clusters = max(1, int(total_slides * MAX_CARD_CLUSTER_PERCENTAGE))

    card_cluster_count = 0
    result: List[VisualRhythmBeat] = []

    for beat in beats:
        if beat.layout_family == Phase3LayoutFamily.CARD_CLUSTER:
            card_cluster_count += 1
            if card_cluster_count > max_card_clusters:
                # Replace with split layout
                beat = beat.model_copy(update={
                    "layout_family": Phase3LayoutFamily.SPLIT_40_60,
                    "rationale": f"{beat.rationale} [card_cluster→split: cap exceeded]",
                })
        result.append(beat)

    return result


# ═══════════════════════════════════════════════════════════════
# SEMANTIC FIT SCORING
# ═══════════════════════════════════════════════════════════════

def _compute_semantic_fit(
    packet: VisualSemanticPacket,
    asset: VisualAssetType,
    layout: Phase3LayoutFamily,
    dna: DesignDNA,
) -> float:
    """Compute how well the assigned asset+layout fits the semantic content."""
    score = 0.5  # Base

    # Boost if the asset matches the top visual candidate
    if packet.visual_candidates:
        top_candidate = packet.visual_candidates[0]
        if top_candidate.asset_type == asset:
            score += 0.2
        if top_candidate.layout_family == layout:
            score += 0.1

    # Boost if layout is in DNA preferences
    if layout in dna.preferred_composition_families:
        score += 0.1

    # Boost for high visual confidence
    if packet.visual_confidence >= 0.8:
        score += 0.1

    return min(1.0, score)


# ═══════════════════════════════════════════════════════════════
# RHYTHM INTEGRITY SCORING
# ═══════════════════════════════════════════════════════════════

def _compute_rhythm_integrity(
    beats: List[VisualRhythmBeat],
    total_slides: int,
) -> float:
    """Compute rhythm integrity score based on variety and constraint adherence."""
    if not beats:
        return 0.0

    score = 1.0

    # 1. Layout variety penalty
    layout_counter = Counter(b.layout_family.value for b in beats)
    unique_layouts = len(layout_counter)
    max_possible_unique = min(len(Phase3LayoutFamily), total_slides)
    variety_ratio = unique_layouts / max(1, max_possible_unique)
    if variety_ratio < 0.3:
        score -= 0.2

    # 2. Consecutive streak penalty
    max_streak = _compute_max_consecutive_streak(beats)
    if max_streak > MAX_CONSECUTIVE_LAYOUT_STREAK:
        score -= 0.1 * (max_streak - MAX_CONSECUTIVE_LAYOUT_STREAK)

    # 3. Card cluster cap penalty
    card_count = sum(1 for b in beats if b.layout_family == Phase3LayoutFamily.CARD_CLUSTER)
    card_pct = card_count / max(1, total_slides)
    if card_pct > MAX_CARD_CLUSTER_PERCENTAGE:
        score -= 0.15

    # 4. Visual weight variety bonus
    weight_counter = Counter(b.visual_weight.value for b in beats)
    if len(weight_counter) >= 2:
        score += 0.05

    # 5. Average semantic fit
    avg_fit = sum(b.semantic_fit_score for b in beats) / len(beats)
    score += (avg_fit - 0.5) * 0.2  # Center around 0.5

    return max(0.0, min(1.0, score))


def _compute_max_consecutive_streak(beats: List[VisualRhythmBeat]) -> int:
    """Compute the maximum consecutive identical layout streak."""
    if not beats:
        return 0
    max_streak = 1
    current_streak = 1
    for i in range(1, len(beats)):
        if beats[i].layout_family == beats[i - 1].layout_family:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 1
    return max_streak


# ═══════════════════════════════════════════════════════════════
# MAIN API
# ═══════════════════════════════════════════════════════════════

def plan_visual_rhythm(
    packets: List[VisualSemanticPacket],
    dna: DesignDNA,
    topic: str = "",
) -> DeckVisualRhythmPlan:
    """Generate a deck-wide visual rhythm plan.

    Args:
        packets: VisualSemanticPackets from the interpreter (one per slide)
        dna: DesignDNA for this deck
        topic: Deck topic (for metadata only, not for visual branching)

    Returns:
        DeckVisualRhythmPlan with rhythm beats, distributions, and integrity score
    """
    total_slides = len(packets)
    beats: List[VisualRhythmBeat] = []
    recent_layouts: List[Phase3LayoutFamily] = []

    for packet in packets:
        # 1. Determine visual weight
        weight = _derive_visual_weight(packet)

        # 2. Select best asset
        asset = _select_best_asset(packet, dna)

        # 3. Select best layout (streak-aware)
        layout = _select_best_layout(packet, dna, recent_layouts)

        # 4. Compute semantic fit
        semantic_fit = _compute_semantic_fit(packet, asset, layout, dna)

        # 5. Build rationale
        rationale = (
            f"{packet.visual_intent.value} → {asset.value} in {layout.value} "
            f"(weight={weight.value}, fit={semantic_fit:.2f})"
        )

        beat = VisualRhythmBeat(
            slide_no=packet.slide_no,
            visual_intent=packet.visual_intent,
            suggested_asset_type=asset,
            layout_family=layout,
            visual_weight=weight,
            rationale=rationale,
            semantic_fit_score=semantic_fit,
        )

        beats.append(beat)
        recent_layouts.append(layout)

    # Enforce card cluster cap
    beats = _enforce_card_cluster_cap(beats, total_slides)

    # Compute distributions
    layout_distribution = dict(Counter(b.layout_family.value for b in beats))
    asset_distribution = dict(Counter(b.suggested_asset_type.value for b in beats))

    # Compute max streak after enforcement
    max_streak = _compute_max_consecutive_streak(beats)

    # Compute card cluster percentage
    card_count = sum(1 for b in beats if b.layout_family == Phase3LayoutFamily.CARD_CLUSTER)
    card_pct = card_count / max(1, total_slides)

    # Compute rhythm integrity
    integrity = _compute_rhythm_integrity(beats, total_slides)

    plan = DeckVisualRhythmPlan(
        topic=topic,
        total_slides=total_slides,
        beats=beats,
        layout_distribution=layout_distribution,
        asset_distribution=asset_distribution,
        max_consecutive_layout_streak=max_streak,
        card_cluster_percentage=card_pct,
        rhythm_integrity_score=integrity,
        design_dna_reference=dna.theme_family,
    )

    logger.info(
        f"[RhythmPlanner] Generated plan: topic={topic}, "
        f"slides={total_slides}, integrity={integrity:.2f}, "
        f"max_streak={max_streak}, card_pct={card_pct:.0%}, "
        f"unique_layouts={len(layout_distribution)}"
    )

    return plan
