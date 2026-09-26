"""
Deck Content Memory & Progression Tracker (Phase 2)
=====================================================
Tracks deck-level semantic memory to prevent cross-slide repetition.
Maintains canonical terminology map for consistent nomenclature.

ISOLATION RULES:
- Must be instantiated PER generation job/deck.
- Never global mutable state.
- Never shared between users or concurrent deck jobs.
- Zero cross-request leakage.
"""
import logging
from typing import Dict, Any, List, Set, Optional, Tuple

logger = logging.getLogger("teachgenie.presentation.deck_content_memory")


class DeckContentMemory:
    """Per-deck semantic memory tracking concepts, examples, analogies, and claims.
    
    MUST be instantiated fresh for each deck generation job.
    MUST NOT be stored as global/module-level state.
    MUST NOT be shared between concurrent requests.
    """
    
    def __init__(self):
        """Initialize a fresh, isolated memory instance."""
        self._concepts_introduced: List[str] = []
        self._examples_used: List[str] = []
        self._statistics_used: List[str] = []
        self._case_studies_used: List[str] = []
        self._analogies_used: List[str] = []
        self._claims_used: List[str] = []
        self._comparison_pairs_used: List[str] = []  # "A vs B" strings
        self._definitions_given: List[str] = []
        
        # Canonical terminology map: {preferred_term: [variants]}
        self._terminology_map: Dict[str, List[str]] = {}
        # Reverse lookup: {variant_lower: canonical_term}
        self._term_reverse: Dict[str, str] = {}
        
        # Slide summaries for progression tracking
        self._slide_summaries: List[str] = []
        self._takeaways_used: List[str] = []
        self._relationships_used: List[str] = []
        self._slide_records: List[Dict[str, Any]] = []
        self._checkpoints: List[Dict[str, Any]] = []
        
        # Track per-slide content fingerprints for novelty
        self._content_fingerprints: List[Set[str]] = []

    # ─── Transactional Checkpoint Methods ──────────────────────

    def create_checkpoint(self) -> None:
        """Save state snapshot for transactional slide generation/repair."""
        state = {
            "concepts_introduced": list(self._concepts_introduced),
            "examples_used": list(self._examples_used),
            "statistics_used": list(self._statistics_used),
            "case_studies_used": list(self._case_studies_used),
            "analogies_used": list(self._analogies_used),
            "claims_used": list(self._claims_used),
            "comparison_pairs_used": list(self._comparison_pairs_used),
            "definitions_given": list(self._definitions_given),
            "slide_summaries": list(self._slide_summaries),
            "takeaways_used": list(self._takeaways_used),
            "relationships_used": list(self._relationships_used),
            "content_fingerprints": [set(fp) for fp in self._content_fingerprints],
            "slide_records": [dict(r) for r in self._slide_records],
        }
        self._checkpoints.append(state)

    def commit_checkpoint(self) -> None:
        """Commit the most recent checkpoint upon successful slide validation."""
        if self._checkpoints:
            self._checkpoints.pop()

    def rollback_checkpoint(self) -> None:
        """Roll back to the previous checkpoint if slide generation/repair fails."""
        if not self._checkpoints:
            return
        state = self._checkpoints.pop()
        self._concepts_introduced = state["concepts_introduced"]
        self._examples_used = state["examples_used"]
        self._statistics_used = state["statistics_used"]
        self._case_studies_used = state["case_studies_used"]
        self._analogies_used = state["analogies_used"]
        self._claims_used = state["claims_used"]
        self._comparison_pairs_used = state["comparison_pairs_used"]
        self._definitions_given = state["definitions_given"]
        self._slide_summaries = state["slide_summaries"]
        self._takeaways_used = state["takeaways_used"]
        self._relationships_used = state["relationships_used"]
        self._content_fingerprints = [set(fp) for fp in state["content_fingerprints"]]
        self._slide_records = [dict(r) for r in state["slide_records"]]

    # ─── Structured Slide Record & Substantive Duplication Check ─

    def register_slide_record(
        self,
        slide_no: int,
        intent: str,
        title: str,
        primary_takeaway: str,
        supporting_points: List[str],
        relationships: Optional[List[str]] = None,
        concepts: Optional[List[str]] = None,
    ) -> None:
        """Register a validated slide record in memory."""
        rec = {
            "slide_no": slide_no,
            "intent": intent,
            "title": title,
            "primary_takeaway": primary_takeaway,
            "supporting_points": list(supporting_points),
            "relationships": list(relationships or []),
            "concepts": list(concepts or []),
        }
        self._slide_records.append(rec)
        self.register_takeaway(primary_takeaway)
        self.register_slide_summary(primary_takeaway)
        if concepts:
            for c in concepts:
                self.register_concept(c)
        if relationships:
            for r in relationships:
                self.register_relationship(r)

    def is_concept_previously_introduced(self, concept: str) -> bool:
        """Check if concept was introduced in an earlier slide."""
        if not concept:
            return False
        c_clean = concept.lower().strip()
        return any(c.lower().strip() == c_clean for c in self._concepts_introduced)

    def is_relationship_already_explained(self, relationship: str) -> bool:
        """Check if this specific relationship has already been explained."""
        return self.is_relationship_already_used(relationship)

    def is_substantive_content_duplicated(
        self,
        takeaway: str,
        supporting_points: List[str],
        intent: str = "",
    ) -> Tuple[bool, str]:
        """
        Distinguish allowable pedagogical recurrence (review, summary, application)
        from illegitimate content duplication.
        Returns (is_duplicated, reason).
        """
        # Allowable pedagogical intents
        intent_lower = intent.lower() if intent else ""
        if intent_lower in (
            "summary", "recap", "knowledge_check", "q_and_a", "references",
            "prerequisite_recall", "misconception", "misconception_correction",
            "application", "spaced_review", "review"
        ):
            return False, ""
        
        t_clean = takeaway.lower().strip()
        t_words = set(w for w in t_clean.split() if len(w) > 3)
        pts_clean = [p.lower().strip() for p in supporting_points if p]

        for prev in self._slide_records:
            prev_intent = prev.get("intent", "")
            if prev_intent in ("cover", "agenda"):
                continue

            prev_t = prev.get("primary_takeaway", "").lower().strip()
            prev_words = set(w for w in prev_t.split() if len(w) > 3)

            # Check takeaway proposition overlap
            t_overlap = 0.0
            if t_words and prev_words:
                t_overlap = len(t_words & prev_words) / max(len(t_words), len(prev_words))

            # Check supporting points overlap
            prev_pts = [p.lower().strip() for p in prev.get("supporting_points", []) if p]
            identical_pts = sum(1 for p in pts_clean if any(p == prev_p for prev_p in prev_pts))
            pts_ratio = identical_pts / max(len(pts_clean), 1) if pts_clean else 0.0

            if t_overlap >= 0.8 and pts_ratio >= 0.6:
                return True, f"Substantive content duplicated with Slide {prev.get('slide_no')}"
            
            if t_clean == prev_t and len(t_words) >= 4:
                return True, f"Identical primary takeaway with Slide {prev.get('slide_no')}"

            if pts_ratio >= 0.75 and len(pts_clean) >= 2:
                return True, f"Identical supporting points with Slide {prev.get('slide_no')}"

        return False, ""
    
    # ─── Registration Methods ──────────────────────────────────
    
    def register_concept(self, concept: str) -> None:
        """Register a concept as introduced in the deck."""
        if concept and concept.lower().strip() not in {c.lower() for c in self._concepts_introduced}:
            self._concepts_introduced.append(concept.strip())
    
    def register_example(self, example: str) -> None:
        """Register an example as used."""
        if example and len(example.strip()) > 5:
            self._examples_used.append(example.strip()[:100])
    
    def register_statistic(self, statistic: str) -> None:
        """Register a statistic/numeric claim as used."""
        if statistic:
            self._statistics_used.append(statistic.strip()[:100])
    
    def register_case_study(self, case_study: str) -> None:
        """Register a case study as used."""
        if case_study:
            self._case_studies_used.append(case_study.strip()[:100])
    
    def register_analogy(self, analogy: str) -> None:
        """Register an analogy as used."""
        if analogy:
            self._analogies_used.append(analogy.strip()[:100])
    
    def register_claim(self, claim: str) -> None:
        """Register a factual claim as used."""
        if claim and len(claim.strip()) > 5:
            self._claims_used.append(claim.strip()[:120])
    
    def register_comparison_pair(self, target_a: str, target_b: str) -> None:
        """Register a comparison pair as used."""
        pair = f"{target_a.strip()} vs {target_b.strip()}"
        if pair not in self._comparison_pairs_used:
            self._comparison_pairs_used.append(pair)
    
    def register_definition(self, term: str) -> None:
        """Register that a term has been formally defined."""
        if term:
            self._definitions_given.append(term.strip().lower())
    
    def register_slide_summary(self, summary: str) -> None:
        """Register a one-sentence summary of a completed slide."""
        self._slide_summaries.append(summary)
    
    def register_takeaway(self, takeaway: str) -> None:
        """Register a primary takeaway as used in the deck."""
        if takeaway and len(takeaway.strip()) > 5:
            self._takeaways_used.append(takeaway.strip())
            self.register_claim(takeaway.strip())
    
    def register_relationship(self, relationship: str) -> None:
        """Register a relationship assertion as used."""
        if relationship and len(relationship.strip()) > 3:
            self._relationships_used.append(relationship.strip())
    
    # ─── Terminology Management ────────────────────────────────
    
    def register_canonical_term(self, canonical: str, variants: Optional[List[str]] = None) -> None:
        """Register a canonical term and its variants."""
        canonical = canonical.strip()
        if not canonical:
            return
        variants = variants or []
        
        if canonical not in self._terminology_map:
            self._terminology_map[canonical] = []
        
        self._term_reverse[canonical.lower()] = canonical
        for v in variants:
            v_clean = v.strip()
            if v_clean and v_clean not in self._terminology_map[canonical]:
                self._terminology_map[canonical].append(v_clean)
                self._term_reverse[v_clean.lower()] = canonical
    
    def get_canonical_term(self, text: str) -> Optional[str]:
        """Look up the canonical form of a term."""
        return self._term_reverse.get(text.strip().lower())
    
    def normalize_terminology(self, text: str) -> str:
        """Replace variant terms with their canonical forms in text."""
        result = text
        for variant_lower, canonical in self._term_reverse.items():
            if variant_lower != canonical.lower() and variant_lower in result.lower():
                # Simple case-preserving replacement
                import re
                result = re.sub(
                    re.escape(variant_lower),
                    canonical,
                    result,
                    flags=re.IGNORECASE,
                    count=1,
                )
        return result
    
    # ─── Duplication Checks ────────────────────────────────────
    
    def is_concept_already_introduced(self, concept: str) -> bool:
        """Check if a concept has already been introduced."""
        return concept.lower().strip() in {c.lower() for c in self._concepts_introduced}
    
    def is_example_already_used(self, example: str) -> bool:
        """Check if a similar example has already been used."""
        ex_lower = example.lower().strip()[:80]
        for used in self._examples_used:
            used_lower = used.lower()[:80]
            # Check for high overlap (shared significant words)
            ex_words = set(w for w in ex_lower.split() if len(w) > 3)
            used_words = set(w for w in used_lower.split() if len(w) > 3)
            if ex_words and used_words:
                overlap = len(ex_words & used_words) / max(len(ex_words), len(used_words))
                if overlap > 0.6:
                    return True
        return False
    
    def is_comparison_pair_used(self, target_a: str, target_b: str) -> bool:
        """Check if a comparison pair has already been used."""
        pair = f"{target_a.strip()} vs {target_b.strip()}"
        pair_reverse = f"{target_b.strip()} vs {target_a.strip()}"
        return pair in self._comparison_pairs_used or pair_reverse in self._comparison_pairs_used
    
    def is_definition_already_given(self, term: str) -> bool:
        """Check if a term has already been defined."""
        return term.strip().lower() in self._definitions_given
    
    def is_claim_already_used(self, claim: str) -> bool:
        """Check if a similar claim has been made."""
        claim_lower = claim.lower().strip()[:100]
        for used in self._claims_used:
            used_lower = used.lower()[:100]
            claim_words = set(w for w in claim_lower.split() if len(w) > 3)
            used_words = set(w for w in used_lower.split() if len(w) > 3)
            if claim_words and used_words:
                overlap = len(claim_words & used_words) / max(len(claim_words), len(used_words))
                if overlap > 0.7:
                    return True
        return False

    def is_takeaway_already_used(self, takeaway: str, threshold: float = 0.55) -> bool:
        """Check if an identical or semantically duplicate takeaway has been used."""
        if not takeaway:
            return False
        clean = takeaway.lower().strip()
        for used in self._takeaways_used:
            used_clean = used.lower().strip()
            if clean == used_clean:
                return True
            w1 = set(w for w in clean.split() if len(w) > 3)
            w2 = set(w for w in used_clean.split() if len(w) > 3)
            if w1 and w2:
                overlap = len(w1 & w2) / max(len(w1), len(w2))
                if overlap >= threshold:
                    return True
        return False

    def is_relationship_already_used(self, rel: str) -> bool:
        """Check if a relationship assertion has already been introduced in this deck."""
        if not rel:
            return False
        clean = rel.lower().strip()
        for used in self._relationships_used:
            used_clean = used.lower().strip()
            if clean == used_clean:
                return True
            w1 = set(w for w in clean.split() if len(w) > 3)
            w2 = set(w for w in used_clean.split() if len(w) > 3)
            if w1 and w2 and (len(w1 & w2) / max(len(w1), len(w2))) >= 0.7:
                return True
        return False
    
    # ─── Content Fingerprinting for Cross-Slide Novelty ────────
    
    def compute_content_fingerprint(self, content_dict: Dict[str, Any]) -> Set[str]:
        """Compute a set of significant content words as a fingerprint."""
        texts = [
            content_dict.get("primary_takeaway", ""),
            content_dict.get("example", ""),
            content_dict.get("callout", ""),
        ]
        texts.extend(content_dict.get("supporting_points", []))
        texts.extend(content_dict.get("process_steps", []))
        
        combined = " ".join(t for t in texts if t).lower()
        words = set(w for w in combined.split() if len(w) > 3)
        # Remove very common words
        stop = {"this", "that", "with", "from", "which", "have", "been", "also",
                "into", "more", "than", "each", "such", "when", "what", "they",
                "will", "does", "their", "about", "through", "between", "after",
                "before", "while", "where", "other", "these", "those", "most"}
        return words - stop
    
    def register_content_fingerprint(self, fingerprint: Set[str]) -> None:
        """Register a slide's content fingerprint."""
        self._content_fingerprints.append(fingerprint)
    
    def compute_novelty_score(self, fingerprint: Set[str]) -> float:
        """Compute novelty score (0.0–1.0) of new content relative to all prior slides.
        1.0 = completely novel, 0.0 = complete duplicate."""
        if not self._content_fingerprints or not fingerprint:
            return 1.0
        
        # Compare against all previous slides
        max_overlap = 0.0
        for prev_fp in self._content_fingerprints:
            if not prev_fp:
                continue
            overlap = len(fingerprint & prev_fp) / max(len(fingerprint), 1)
            max_overlap = max(max_overlap, overlap)
        
        return round(1.0 - max_overlap, 2)
    
    # ─── Context for Next Slide Generation ─────────────────────
    
    def get_generation_context(self) -> Dict[str, Any]:
        """Return deck memory context for the next slide generation call."""
        return {
            "concepts_introduced": self._concepts_introduced[-10:],
            "examples_used": self._examples_used[-6:],
            "statistics_used": self._statistics_used[-6:],
            "case_studies_used": self._case_studies_used[-4:],
            "analogies_used": self._analogies_used[-4:],
            "comparison_pairs_used": self._comparison_pairs_used[-4:],
            "definitions_given": self._definitions_given[-8:],
            "previous_slide_summaries": self._slide_summaries[-3:],
            "canonical_terms": list(self._terminology_map.keys())[:15],
        }
    
    def get_previous_slide_summary(self) -> str:
        """Get the most recent slide summary for narrative continuity."""
        if self._slide_summaries:
            return self._slide_summaries[-1]
        return ""
    
    # ─── Serialization ─────────────────────────────────────────
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize memory state (for debugging/telemetry only)."""
        return {
            "concepts_count": len(self._concepts_introduced),
            "examples_count": len(self._examples_used),
            "statistics_count": len(self._statistics_used),
            "case_studies_count": len(self._case_studies_used),
            "analogies_count": len(self._analogies_used),
            "claims_count": len(self._claims_used),
            "comparison_pairs_count": len(self._comparison_pairs_used),
            "definitions_count": len(self._definitions_given),
            "terminology_entries": len(self._terminology_map),
            "slides_tracked": len(self._slide_summaries),
        }
