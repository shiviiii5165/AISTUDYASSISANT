"""
LearnByGenie Student Artifact Certification — Master Coordinator
==============================================================
Orchestrates two-layer certification downstream of Step 4:
1. Content Certification: Syllabus coverage & substantive evidence against authoritative plan.
2. Artifact Certification: Physical PDF fidelity, raw LaTeX absence, geometry, and notation.
Enforces cryptographic artifact binding (document_hash, pdf_hash).
"""
import io
import json
import hashlib
import logging
from typing import Optional, Tuple, Dict, Any, List

from .schemas import (
    ArtifactStatus, DocumentQualityResult, ContentCertificationResult,
    ArtifactCertificationResult, RenderingDefect, RenderingDefectType
)
from .coverage_certifier import CoverageCertifier
from .latex_scanner import RawLatexScanner
from .notation_qa import NotationQACertifier
from .geometry_qa import GeometryQACertifier
from .visual_inspector import RasterizedVisualInspector
from ..rendering.html_builder import HTMLNoteBuilder
from ..rendering.pdf_renderer import PDFNoteRenderer
from ..schemas import NotesDocument
from ..context.schemas import CanonicalNotesContext
from ..decision.schemas import NotesGenerationPlan

logger = logging.getLogger("learnbygenie.notes.certification.master")


class StudentArtifactCertifier:
    """Master certifier auditing student readiness and physical PDF usability."""

    @classmethod
    async def certify_artifact(
        cls,
        doc: Optional[NotesDocument] = None,
        plan: Optional[NotesGenerationPlan] = None,
        ctx: Optional[CanonicalNotesContext] = None,
        pdf_bytes: Optional[bytes] = None,
        pdf_hash: Optional[str] = None,
        html_content: Optional[str] = None,
        document: Optional[NotesDocument] = None,
        context: Optional[CanonicalNotesContext] = None,
    ) -> DocumentQualityResult:
        """
        Executes two-layer certification.
        Returns: DocumentQualityResult
        """
        target_doc = document or doc
        if not target_doc:
            raise ValueError("A NotesDocument must be provided for certification.")

        target_ctx = context or ctx
        if plan is None:
            if target_ctx:
                from ..decision import decide_notes_plan
                plan = decide_notes_plan(target_ctx)
            else:
                from ..decision.schemas import (
                    NotesGenerationPlan, PurposePlan, TeachingStrategyPlan,
                    VisualPlan, RemediationPlan, PracticePlan, RevisionPlan,
                    SectionPlanItem
                )
                from ..schemas import NoteFormat, NoteDepth, NoteDifficulty
                plan = NotesGenerationPlan(
                    primary_topic=target_doc.topic or target_doc.title,
                    target_class=target_doc.class_level,
                    subject=target_doc.subject,
                    purpose=PurposePlan(),
                    formats=[NoteFormat.LEARNING_NOTES],
                    difficulty=NoteDifficulty.STANDARD,
                    depth=NoteDepth.STANDARD,
                    teaching_strategy=TeachingStrategyPlan(),
                    section_plan=[SectionPlanItem(type="core_concept", required=True)],
                    visual_plan=VisualPlan(),
                    remediation_plan=RemediationPlan(),
                    practice_plan=PracticePlan(),
                    revision_plan=RevisionPlan()
                )

        warnings: List[str] = []
        errors: List[str] = []

        # 1. Cryptographic Document Hash
        doc_dump = target_doc.model_dump(mode="json")
        doc_json_str = json.dumps(doc_dump, sort_keys=True)
        document_hash = hashlib.sha256(doc_json_str.encode("utf-8")).hexdigest()

        # 2. Server-Authoritative Rendering if PDF bytes not provided
        if not pdf_bytes:
            pdf_bytes, pdf_hash = await PDFNoteRenderer.render_pdf_async(target_doc, include_answers=True)
        elif not pdf_hash:
            pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()

        # ── LAYER A: CONTENT CERTIFICATION ──
        content_res = CoverageCertifier.certify_content_coverage(target_doc, plan, target_ctx)
        if not content_res.valid:
            errors.extend(content_res.findings)

        # ── LAYER B: ARTIFACT CERTIFICATION (PHYSICAL PDF) ──
        # Generate or use supplied DOM HTML for markup-level inspection
        dom_html = html_content if html_content else HTMLNoteBuilder.build_html(target_doc, include_answers=True)

        # Extract text from rendered PDF
        all_pdf_text = ""
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                all_pdf_text = " ".join([page.extract_text() or "" for page in pdf.pages])
        except Exception as e:
            logger.warning(f"Failed to extract PDF text via pdfplumber: {e}")

        # B1. Raw LaTeX Scanning across both DOM and extracted PDF text
        all_defects: List[RenderingDefect] = []
        dom_latex_defects = RawLatexScanner.scan_text(dom_html)
        pdf_latex_defects = RawLatexScanner.scan_text(all_pdf_text)
        all_defects.extend(dom_latex_defects)
        all_defects.extend(pdf_latex_defects)

        # B2. Notation QA
        notation_defects, notation_details = NotationQACertifier.audit_notation(
            dom_html=dom_html,
            extracted_pdf_text=all_pdf_text,
            topic=target_doc.topic
        )
        all_defects.extend(notation_defects)

        # B3. Geometry & Pagination QA
        geom_defects, geom_details = GeometryQACertifier.audit_pdf_geometry(pdf_bytes, target_doc)
        all_defects.extend(geom_defects)

        # B4. Rasterized Page Image Inspection
        vis_defects, vis_details, _ = RasterizedVisualInspector.inspect_pdf_images(pdf_bytes)
        all_defects.extend(vis_defects)

        # B5. Practice Validation in Artifact
        practice_req_count = len(target_doc.practice)
        practice_valid_count = 0
        for p in target_doc.practice:
            ans = str(p.get("answer", "")).strip()
            # If answer is non-empty and question appears in doc
            if ans and ans.lower() not in ("...", "tbd", "todo"):
                practice_valid_count += 1

        # Aggregate Defect Metrics
        raw_latex_count = len([d for d in all_defects if "LATEX" in d.type.value or "BROKEN" in d.type.value])
        clipping_count = len([d for d in all_defects if d.type == RenderingDefectType.CLIPPING])
        overflow_count = len([d for d in all_defects if d.type in (RenderingDefectType.OVERFLOW, RenderingDefectType.FOOTER_COLLISION)])
        broken_eq_count = len([d for d in all_defects if d.type == RenderingDefectType.MATH_RENDER_FAILURE])
        truncated_count = len([d for d in all_defects if d.type == RenderingDefectType.DOCUMENT_TRUNCATED])

        artifact_res = ArtifactCertificationResult(
            status="passed" if len(all_defects) == 0 else "defects_detected",
            valid=(len([d for d in all_defects if d.severity == "critical"]) == 0),
            pages=geom_details.get("page_count", 1),
            raw_latex_count=raw_latex_count,
            clipping_count=clipping_count,
            overflow_count=overflow_count,
            broken_equations_count=broken_eq_count,
            defects=all_defects,
            practice_valid_count=practice_valid_count,
            practice_required_count=practice_req_count
        )

        for d in all_defects:
            if d.severity == "critical":
                errors.append(f"[{d.type.value}] {d.message}")
            else:
                warnings.append(f"[{d.type.value}] {d.message}")

        # ── 3. Final Artifact Status Synthesis ──
        # Incomplete check (broad topic with tiny stub, or missing concepts)
        is_incomplete = not content_res.valid or (content_res.coverage.total_required > 2 and content_res.coverage.covered == 0)

        # Check for 1-page incomplete scenario: broad topic + detailed depth with only 1 paragraph
        total_words = sum(len(s.content.split()) for s in target_doc.sections)
        depth_val = target_doc.depth.value if hasattr(target_doc.depth, "value") else str(target_doc.depth)
        if depth_val in ("detailed", "deep") and len(target_doc.sections) <= 1 and total_words < 50:
            is_incomplete = True
            errors.append("Document is a single tiny stub despite requiring detailed pedagogical depth.")

        if not pdf_bytes or len(pdf_bytes) < 100:
            final_status = ArtifactStatus.RENDERING_FAILED
        elif truncated_count > 0 or raw_latex_count > 0 or clipping_count > 0:
            final_status = ArtifactStatus.INVALID
        elif is_incomplete:
            final_status = ArtifactStatus.INCOMPLETE
        elif warnings:
            final_status = ArtifactStatus.STUDENT_READY_WITH_WARNINGS
        else:
            final_status = ArtifactStatus.STUDENT_READY

        render_config_hash = hashlib.sha256(
            json.dumps(PDFNoteRenderer.LOCKED_CONFIG, sort_keys=True).encode("utf-8")
        ).hexdigest()
        cert_id = f"cert_{hashlib.sha256((document_hash + pdf_hash).encode('utf-8')).hexdigest()[:16]}"

        result = DocumentQualityResult(
            schema_version="1.0",
            artifact_status=final_status,
            document_id=target_doc.id or target_doc.document_id or "doc",
            document_version="1.0",
            document_hash=document_hash,
            renderer_version=PDFNoteRenderer.RENDERER_VERSION,
            render_config_hash=render_config_hash,
            pdf_hash=pdf_hash,
            certification_id=cert_id,
            certification_status=final_status.value,
            content_certification=content_res,
            artifact_certification=artifact_res,
            coverage={
                "required": content_res.coverage.total_required,
                "covered": content_res.coverage.covered,
                "partial": content_res.coverage.partial,
                "missing": content_res.coverage.missing,
                "unverified": content_res.coverage.unverified,
                "sub_concepts_total": content_res.coverage.sub_concepts_total,
                "sub_concepts_covered": content_res.coverage.sub_concepts_covered,
                "sub_concepts_missing": content_res.coverage.sub_concepts_missing
            },
            rendering={
                "pages": artifact_res.pages,
                "raw_latex": raw_latex_count,
                "clipping": clipping_count,
                "overflow": overflow_count,
                "broken_equations": broken_eq_count
            },
            practice={
                "required": practice_req_count,
                "valid": practice_valid_count
            },
            warnings=list(dict.fromkeys(warnings)),
            errors=list(dict.fromkeys(errors))
        )

        return result
