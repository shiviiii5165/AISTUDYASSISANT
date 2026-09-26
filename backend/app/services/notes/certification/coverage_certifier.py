"""
LearnByGenie Artifact Certification — Coverage Certifier
======================================================
Evaluates syllabus coverage and substantive instructional evidence.
Invariants:
1. Originates strictly from CanonicalNotesContext, curriculum, and NotesGenerationPlan.
2. NEVER invents syllabus structure.
3. Evaluates substantive instructional evidence (explanation, relationship, example,
   application, exception, worked problem, practice target, recap) rather than raw word count.
4. Outputs CoverageManifest with explicit concept tracking.
"""
import re
from typing import List, Dict, Any, Optional, Tuple

from .schemas import (
    CoverageStatus, CoverageEvidenceType, CoverageManifestItem,
    CoverageManifest, ContentCertificationResult, SubConceptCoverageItem
)
from ..schemas import NotesDocument
from ..context.schemas import CanonicalNotesContext
from ..decision.schemas import NotesGenerationPlan


class CoverageCertifier:
    """Certifies content completeness against authoritative syllabus and plan."""

    @classmethod
    def certify_content_coverage(
        cls,
        doc: NotesDocument,
        plan: NotesGenerationPlan,
        ctx: Optional[CanonicalNotesContext] = None
    ) -> ContentCertificationResult:
        """
        Builds and evaluates CoverageManifest with sub-concept granularity,
        instructional evidence verification, worked-example procedural quality,
        and practice distribution auditing.
        """
        manifest_items: List[CoverageManifestItem] = []
        findings: List[str] = []

        # ── 1. Collect Authoritative Objectives & Sub-Concepts (Strict Non-Invention) ──
        # (concept_id, concept_name, source, sub_concepts)
        required_concepts: List[Tuple[str, str, str, List[str]]] = []

        # Check structured_objectives on ctx.lesson if present
        ctx_structured = getattr(ctx.lesson, "structured_objectives", None) if ctx and getattr(ctx, "lesson", None) else None

        if ctx and getattr(ctx, "lesson", None) and ctx.lesson.learning_objectives:
            for idx, obj in enumerate(ctx.lesson.learning_objectives):
                cname = str(obj).strip()
                sub_list: List[str] = []
                if ctx_structured and isinstance(ctx_structured, dict):
                    # Match objective name in structured dict
                    for k, v in ctx_structured.items():
                        if k.lower() in cname.lower() or cname.lower() in k.lower():
                            sub_list = [str(item).strip() for item in v if str(item).strip()]
                            break
                required_concepts.append((f"obj_{idx+1}", cname, "canonical_context.lesson.learning_objectives", sub_list))

        if not required_concepts and ctx and getattr(ctx, "learning_objectives", None):
            for idx, obj in enumerate(ctx.learning_objectives):
                cname = str(obj).strip()
                required_concepts.append((f"obj_{idx+1}", cname, "canonical_context.learning_objectives", []))

        # Also pull required targets from NotesGenerationPlan.section_plan
        for idx, sp in enumerate(plan.section_plan):
            if sp.required and sp.target:
                sub_list = getattr(sp, "sub_concepts", []) or []
                required_concepts.append((f"plan_sec_{sp.type}", sp.target, "generation_plan.section_plan", sub_list))

        # Deduplicate required concepts, merging sub_concepts if found
        deduped_map: Dict[str, Tuple[str, str, str, List[str]]] = {}
        for cid, cname, src, subs in required_concepts:
            key = cname.lower()
            if key not in deduped_map:
                deduped_map[key] = (cid, cname, src, list(subs))
            else:
                # Merge any newly discovered sub_concepts
                existing_cid, existing_name, existing_src, existing_subs = deduped_map[key]
                combined_subs = list(existing_subs)
                for s in subs:
                    if s.lower() not in [x.lower() for x in combined_subs]:
                        combined_subs.append(s)
                deduped_map[key] = (existing_cid, existing_name, existing_src, combined_subs)

        deduped_concepts = list(deduped_map.values())

        # If no explicit objectives were supplied in context, extract core topic concepts
        if not deduped_concepts and ctx:
            topic_str = ctx.topic or doc.topic
            deduped_concepts.append(("core_topic", topic_str, "canonical_context.topic", []))

        # ── 2. Inspect Sections for Substantive Evidence & Sub-Concepts ──
        covered_count = 0
        partially_covered_count = 0
        missing_count = 0

        sub_concepts_total = 0
        sub_concepts_covered = 0
        sub_concepts_partial = 0
        sub_concepts_missing = 0
        sub_concepts_unverified = 0

        _NORM_TRANS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉", "01234567890123456789")
        all_doc_content = " ".join([f"{s.title} {s.content}" for s in doc.sections])
        all_doc_lower = all_doc_content.translate(_NORM_TRANS).lower()

        for cid, cname, src, subs in deduped_concepts:
            c_clean = cname.strip().translate(_NORM_TRANS)
            keywords = [w for w in re.findall(r'\w+', c_clean.lower()) if len(w) > 3 and w not in ('state', 'explain', 'describe', 'understand', 'theory')]
            if not keywords:
                keywords = [w for w in re.findall(r'\w+', c_clean.lower()) if len(w) > 2]

            matching_sections = []
            found_evidence_type = None
            evidence_snippet = None

            for sec in doc.sections:
                sec_text = f"{sec.title} {sec.content}".translate(_NORM_TRANS).lower()
                matched_kw = sum(1 for kw in keywords if kw in sec_text)

                if matched_kw >= max(1, len(keywords) // 2):
                    matching_sections.append(sec)
                    if sec.examples and any(kw in " ".join(sec.examples).lower() for kw in keywords):
                        found_evidence_type = CoverageEvidenceType.EXAMPLE
                        evidence_snippet = sec.examples[0][:140]
                    elif sec.formulas and any(kw in " ".join(sec.formulas).lower() for kw in keywords):
                        found_evidence_type = CoverageEvidenceType.WORKED_PROBLEM
                        evidence_snippet = sec.formulas[0][:140]
                    elif "exception" in sec_text or "limitation" in sec_text:
                        found_evidence_type = CoverageEvidenceType.EXCEPTION
                        evidence_snippet = sec.content[:140]
                    elif any(r in sec_text for r in ["proportional", "increases", "decreases", "order:", "repulsion", "greater than", "vs"]):
                        found_evidence_type = CoverageEvidenceType.RELATIONSHIP
                        evidence_snippet = sec.content[:140]
                    elif len(sec.content.split()) >= 25:
                        found_evidence_type = CoverageEvidenceType.EXPLANATION
                        evidence_snippet = sec.content[:140]
                    else:
                        found_evidence_type = CoverageEvidenceType.RECAP
                        evidence_snippet = sec.content[:140]

            # Assess Top-Level Status
            if len(matching_sections) > 0 and found_evidence_type:
                top_status = CoverageStatus.COVERED
                covered_count += 1
                sec_id = matching_sections[0].id or matching_sections[0].section_type
            elif len(matching_sections) > 0:
                top_status = CoverageStatus.PARTIALLY_COVERED
                partially_covered_count += 1
                sec_id = matching_sections[0].id or matching_sections[0].section_type
            else:
                top_status = CoverageStatus.MISSING
                missing_count += 1
                sec_id = None
                findings.append(f"Required syllabus concept '{cname}' was omitted from document content.")

            # Assess Sub-Concepts (if authoritative data provided them)
            sub_items: List[SubConceptCoverageItem] = []
            has_missing_sub = False

            for s_idx, sub_name in enumerate(subs):
                sub_concepts_total += 1
                sub_clean = sub_name.strip().translate(_NORM_TRANS)
                sub_id = f"{cid}_sub_{s_idx+1}"
                sub_kws = [w for w in re.findall(r'\w+', sub_clean.lower()) if len(w) >= 3 and w not in ('the', 'and', 'for', 'are', 'not', 'its', 'state', 'explain', 'understand', 'that', 'with', 'from', 'have')]
                if not sub_kws:
                    sub_kws = [w for w in re.findall(r'\w+', sub_clean.lower()) if len(w) >= 2]

                min_kw_match = max(2, int(len(sub_kws) * 0.6)) if len(sub_kws) >= 3 else len(sub_kws)

                matched_sub_sec = None
                sub_snippet = None
                sub_ev_type = None

                # Search through doc sections
                for s in doc.sections:
                    s_full = f"{s.title} {s.content} {' '.join(s.key_points)} {' '.join(s.examples)} {' '.join(s.common_mistakes)}".translate(_NORM_TRANS).lower()
                    m_kw = sum(1 for kw in sub_kws if kw in s_full)
                    if m_kw >= min_kw_match:
                        matched_sub_sec = s
                        sub_snippet = s.content[:120]
                        if s.examples:
                            sub_ev_type = CoverageEvidenceType.EXAMPLE
                        elif "|" in s.content and "--" in s.content:
                            sub_ev_type = CoverageEvidenceType.RELATIONSHIP
                        else:
                            sub_ev_type = CoverageEvidenceType.EXPLANATION
                        break

                # Also search practice questions
                if not matched_sub_sec:
                    for p in doc.practice:
                        p_full = f"{p.get('question', '')} {p.get('answer', '')} {p.get('explanation', '')}".translate(_NORM_TRANS).lower()
                        p_kw = sum(1 for kw in sub_kws if kw in p_full)
                        if p_kw >= min_kw_match:
                            sub_snippet = p.get('question', '')[:120]
                            sub_ev_type = CoverageEvidenceType.PRACTICE_TARGET
                            matched_sub_sec = True
                            break

                if matched_sub_sec and sub_snippet and len(sub_snippet) > 20:
                    sub_status = CoverageStatus.COVERED
                    sub_concepts_covered += 1
                elif matched_sub_sec:
                    sub_status = CoverageStatus.PARTIALLY_COVERED
                    sub_concepts_partial += 1
                else:
                    sub_status = CoverageStatus.MISSING
                    sub_concepts_missing += 1
                    has_missing_sub = True
                    findings.append(f"Authoritative sub-concept '{sub_name}' under '{cname}' was missing.")

                sub_items.append(SubConceptCoverageItem(
                    concept_id=sub_id,
                    concept_name=sub_name,
                    parent_objective_id=cid,
                    status=sub_status,
                    section_id=matched_sub_sec.id if hasattr(matched_sub_sec, 'id') else None,
                    evidence=sub_snippet,
                    evidence_type=sub_ev_type
                ))

            # Rule: If any required sub-concept is MISSING, do not allow top-level 100% claim
            if has_missing_sub:
                findings.append(f"Topic '{cname}' cannot be 100% complete because one or more sub-concepts are MISSING.")

            # ── 3. Instructional Evidence Audit per Concept ──
            sec_focus = matching_sections[0] if matching_sections else None
            sec_focus_text = f"{sec_focus.title}\n{sec_focus.content}" if sec_focus else ""
            instructional_ev = {
                "simple_explanation": bool(sec_focus and ("simple idea" in sec_focus_text.lower() or len(sec_focus.content.split()) >= 20)),
                "intuition": bool(sec_focus and any(k in sec_focus_text.lower() for k in ["intuition", "analogy", "think of", "like a", "benchmark"])),
                "formal_definition": bool(sec_focus and any(k in sec_focus_text.lower() for k in ["formal", "postulate", "definition", "stated as", "law"])),
                "mechanism": bool(sec_focus and any(k in sec_focus_text.lower() for k in ["mechanism", "process", "overlap", "sharing", "transfer", "mixing"])),
                "example": bool(sec_focus and (sec_focus.examples or any(k in sec_focus_text for k in ["SF6", "NH3", "H2O", "PCl5", "CH4", "BeCl2"]))),
                "worked_example": bool(sec_focus and sec_focus.examples and any("step 1" in ex.lower() or "problem" in ex.lower() for ex in sec_focus.examples)),
                "comparison": bool(sec_focus and ("|" in sec_focus.content or "vs" in sec_focus_text.lower() or "comparison" in sec_focus_text.lower())),
                "misconception": bool(sec_focus and (sec_focus.common_mistakes or any(c.type == "misconception" for c in sec_focus.callouts))),
                "application": bool(sec_focus and any(k in sec_focus_text.lower() for k in ["application", "boiling point", "geometry", "physical properties"])),
                "practice": any(any(kw in str(p.get("question", "")).lower() for kw in keywords) for p in doc.practice),
                "revision": bool(sec_focus and (sec_focus.key_points or "takeaways" in sec_focus_text.lower()))
            }

            manifest_items.append(CoverageManifestItem(
                concept_id=cid,
                concept_name=cname,
                source=src,
                status=top_status,
                section_id=sec_id,
                evidence_type=found_evidence_type,
                evidence_snippet=evidence_snippet,
                evidence=evidence_snippet,
                sub_concepts=sub_items,
                instructional_evidence=instructional_ev
            ))

        total_req = len(deduped_concepts)
        manifest = CoverageManifest(
            total_required=total_req,
            covered=covered_count,
            partial=partially_covered_count,
            partially_covered=partially_covered_count,
            missing=missing_count,
            unverified=0,
            out_of_scope=0,
            items=manifest_items,
            sub_concepts_total=sub_concepts_total,
            sub_concepts_covered=sub_concepts_covered,
            sub_concepts_partial=sub_concepts_partial,
            sub_concepts_missing=sub_concepts_missing,
            sub_concepts_unverified=sub_concepts_unverified
        )

        # ── 4. Worked Example Quality Audit (Section 4) ──
        total_worked_examples = 0
        procedural_worked_examples = 0
        stub_worked_examples = 0
        worked_example_findings = []

        for sec in doc.sections:
            for ex in sec.examples:
                total_worked_examples += 1
                ex_lower = ex.lower()
                has_problem = "problem" in ex_lower
                has_concept = any(k in ex_lower for k in ["concept", "method", "given", "formula"])
                has_steps = any(k in ex_lower for k in ["step 1", "step 2", "1.", "2."])
                has_final_ans = any(k in ex_lower for k in ["final answer", "result", "answer:"])
                has_explanation = any(k in ex_lower for k in ["why", "explanation", "rationale", "because"])

                if has_problem and has_steps and (has_final_ans or has_explanation):
                    procedural_worked_examples += 1
                elif len(ex.split()) < 15 or ("->" in ex and not has_steps):
                    stub_worked_examples += 1
                    worked_example_findings.append(f"Worked example in {sec.title} is a non-procedural shorthand stub.")
                else:
                    procedural_worked_examples += 1

        # ── 5. Practice Coverage & Distribution Audit (Section 5 & 6) ──
        practice_dist = {"recall": 0, "conceptual": 0, "application": 0, "exam-style": 0, "challenge": 0, "other": 0}
        practice_findings = []
        seen_questions = []

        for p_idx, p in enumerate(doc.practice):
            q_text = str(p.get("question", "")).strip()
            # Check non-repetitive
            q_tokens = set(re.findall(r'\w+', q_text.lower()))
            for prev_q in seen_questions:
                prev_tokens = set(re.findall(r'\w+', prev_q.lower()))
                if q_tokens and prev_tokens:
                    jaccard = len(q_tokens & prev_tokens) / len(q_tokens | prev_tokens)
                    if jaccard > 0.8:
                        practice_findings.append(f"Practice question {p_idx+1} is repetitive of an earlier question.")
            seen_questions.append(q_text)

            cat = str(p.get("type") or p.get("category") or "").lower()
            if cat in practice_dist:
                practice_dist[cat] += 1
            else:
                # Infer category if missing
                if any(k in q_text.lower() for k in ["state", "define", "name"]):
                    practice_dist["recall"] += 1
                elif any(k in q_text.lower() for k in ["why", "explain", "how"]):
                    practice_dist["conceptual"] += 1
                elif any(k in q_text.lower() for k in ["calculate", "determine", "find"]):
                    practice_dist["application"] += 1
                elif any(k in q_text.lower() for k in ["exam", "jee", "neet", "cbse"]):
                    practice_dist["exam-style"] += 1
                else:
                    practice_dist["other"] += 1

        # Calculate Substantive Score
        substantive_score = 100.0
        if total_req > 0:
            top_ratio = (covered_count + 0.5 * partially_covered_count) / total_req
            substantive_score = round(top_ratio * 100.0, 1)

        # Penalize if authoritative sub-concepts are missing
        if sub_concepts_total > 0:
            sub_ratio = (sub_concepts_covered + 0.5 * sub_concepts_partial) / sub_concepts_total
            if sub_concepts_missing > 0:
                substantive_score = min(substantive_score, round(sub_ratio * 100.0, 1))
                if substantive_score >= 100.0:
                    substantive_score = 95.0

        is_valid = (missing_count == 0 and sub_concepts_missing == 0 and stub_worked_examples == 0)
        final_status = "passed" if is_valid else "incomplete"

        findings.extend(worked_example_findings)
        findings.extend(practice_findings)

        return ContentCertificationResult(
            status=final_status,
            valid=is_valid,
            coverage=manifest,
            substantive_score=substantive_score,
            findings=findings,
            worked_example_quality={
                "total": total_worked_examples,
                "procedural": procedural_worked_examples,
                "stubs": stub_worked_examples,
                "findings": worked_example_findings
            },
            practice_distribution={
                "total": len(doc.practice),
                "distribution": practice_dist,
                "findings": practice_findings
            }
        )

    @classmethod
    def certify_coverage(
        cls,
        doc: NotesDocument,
        plan: NotesGenerationPlan,
        context: Optional[CanonicalNotesContext] = None
    ) -> Tuple[CoverageManifest, List[str]]:
        """Convenience alias returning (manifest, findings)."""
        res = cls.certify_content_coverage(doc, plan, context)
        return res.coverage, res.findings

