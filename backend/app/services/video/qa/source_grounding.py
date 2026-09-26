"""
LearnByGenie AI Video Teacher V2.1 — Claim-Aware Source Grounding QA
==================================================================
Enforces Decision #7 (Source Grounding Must Be Claim-Aware):
- Tracks factual claims per scene for lessons grounded in uploaded PDFs, PPTs, or notes.
- Maps claims against supplied source context.
- Flags unsupported claims or ungrounded general-knowledge drift.
- Computes scene-level and lesson-level grounding ratios.
"""
import re
from typing import List, Dict, Optional, Tuple, Any
from ..schemas import (
    Storyboard, SceneSpec, SceneGroundingResult, SourceGroundingReport, SourceRef
)
from app.core.logging import logger


class SourceGroundingQA:
    """Verifies that lesson content remains faithful to uploaded source materials."""

    @classmethod
    def evaluate_grounding(
        cls,
        storyboard: Storyboard,
        source_text: Optional[str] = None,
        source_id: str = "custom_document",
    ) -> SourceGroundingReport:
        """
        Audits narration and visual text against provided source context.
        If no source_text is provided, assumes topic-general lesson (100% baseline).
        """
        if not source_text or not source_text.strip():
            # Topic-only generation without uploaded documents: pristine general baseline
            return SourceGroundingReport(
                source_id=source_id,
                total_claims=0,
                supported_claims=0,
                unsupported_claims=[],
                source_coverage=1.0,
                grounding_score=1.0,
                scene_results=[],
                affected_scenes=[],
                has_ungrounded_claims=False,
            )

        source_clean = source_text.lower()
        source_sentences = [s.strip() for s in re.split(r"[.\n;]+", source_clean) if len(s.strip()) > 5]
        source_words = set(re.findall(r"\b[a-zA-Z0-9_-]{4,}\b", source_clean))

        scene_results: List[SceneGroundingResult] = []
        total_claims_all = 0
        supported_claims_all = 0
        unsupported_claims_all: List[str] = []
        affected_scenes: List[str] = []

        for scene in storyboard.scenes:
            scene_claims = cls._extract_claims_from_scene(scene)
            total_claims = len(scene_claims)
            total_claims_all += total_claims

            supported: List[str] = []
            unsupported: List[str] = []
            warnings: List[str] = []

            for claim in scene_claims:
                claim_words = set(re.findall(r"\b[a-zA-Z0-9_-]{4,}\b", claim.lower()))
                # Check overlap against source vocabulary and phrases
                overlap = claim_words.intersection(source_words)
                overlap_ratio = len(overlap) / max(1, len(claim_words))

                # Also check direct substring or semantic proximity
                direct_match = any(claim.lower() in s or s in claim.lower() for s in source_sentences)

                if direct_match or overlap_ratio >= 0.40:
                    supported.append(claim)
                    supported_claims_all += 1
                else:
                    unsupported.append(claim)
                    unsupported_claims_all.append(f"[{scene.scene_id}] {claim}")
                    warnings.append(f"Claim not explicitly grounded in source: '{claim}'")

            ratio = len(supported) / max(1, total_claims) if total_claims > 0 else 1.0

            if len(unsupported) > 0:
                affected_scenes.append(scene.scene_id)

            # Map source refs if present
            s_refs = scene.source_refs or [
                SourceRef(
                    source_id=source_id,
                    source_type="uploaded_document",
                    citation_label=f"Source Doc ({len(supported)}/{max(1, total_claims)} claims)",
                )
            ]

            scene_results.append(SceneGroundingResult(
                scene_id=scene.scene_id,
                total_claims=total_claims,
                supported_claims=supported,
                unsupported_claims=unsupported,
                source_refs=s_refs,
                grounding_ratio=round(ratio, 2),
                warnings=warnings,
            ))

        overall_score = round(supported_claims_all / max(1, total_claims_all), 2) if total_claims_all > 0 else 1.0

        return SourceGroundingReport(
            source_id=source_id,
            total_claims=total_claims_all,
            supported_claims=supported_claims_all,
            unsupported_claims=unsupported_claims_all,
            source_coverage=round(len(scene_results) / max(1, len(storyboard.scenes)), 2),
            grounding_score=overall_score,
            scene_results=scene_results,
            affected_scenes=affected_scenes,
            has_ungrounded_claims=len(unsupported_claims_all) > 0,
        )

    @classmethod
    def _extract_claims_from_scene(cls, scene: SceneSpec) -> List[str]:
        """Extracts individual assertional statements from scene narration and visual spec."""
        claims = []
        # Split narration into assertional clauses
        sentences = [s.strip() for s in re.split(r"[.!?\n]+", scene.narration) if len(s.strip()) > 10]
        for s in sentences:
            claims.append(s)

        # Visual bullets / steps
        for step in scene.visual_spec.steps:
            if len(step.strip()) > 5:
                claims.append(f"Visual step: {step.strip()}")

        for bullet in scene.visual_spec.bullets:
            if len(bullet.strip()) > 5:
                claims.append(f"Visual bullet: {bullet.strip()}")

        return claims
