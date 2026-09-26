"""
LearnByGenie Student Artifact Certification — Schemas & Quality Contracts
========================================================================
Strict, explainable data models for two-layer certification:
1. Content Certification: Syllabus coverage and instructional evidence.
2. Artifact Certification: PDF typography, notation QA, geometry, and pagination.
Cryptographically bound to exact NotesDocument version.
"""
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ArtifactStatus(str, Enum):
    STUDENT_READY = "STUDENT_READY"
    STUDENT_READY_WITH_WARNINGS = "STUDENT_READY_WITH_WARNINGS"
    INCOMPLETE = "INCOMPLETE"
    RENDERING_FAILED = "RENDERING_FAILED"
    INVALID = "INVALID"


class CoverageStatus(str, Enum):
    COVERED = "COVERED"
    PARTIALLY_COVERED = "PARTIALLY_COVERED"
    MISSING = "MISSING"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNVERIFIED = "UNVERIFIED"


class CoverageEvidenceType(str, Enum):
    EXPLANATION = "explanation"
    RELATIONSHIP = "relationship"
    EXAMPLE = "example"
    APPLICATION = "application"
    EXCEPTION = "exception"
    WORKED_PROBLEM = "worked_problem"
    PRACTICE_TARGET = "practice_target"
    RECAP = "recap"


class SubConceptCoverageItem(BaseModel):
    concept_id: str
    concept_name: str
    parent_objective_id: str
    status: CoverageStatus
    section_id: Optional[str] = None
    evidence: Optional[str] = None
    evidence_type: Optional[CoverageEvidenceType] = None


class CoverageManifestItem(BaseModel):
    concept_id: str
    concept_name: str
    source: str = "context"
    status: CoverageStatus
    section_id: Optional[str] = None
    evidence_type: Optional[CoverageEvidenceType] = None
    evidence_snippet: Optional[str] = None
    evidence: Optional[str] = None
    sub_concepts: List[SubConceptCoverageItem] = Field(default_factory=list)
    instructional_evidence: Dict[str, bool] = Field(default_factory=dict)


class CoverageManifest(BaseModel):
    total_required: int = 0
    covered: int = 0
    partial: int = 0
    partially_covered: int = 0
    missing: int = 0
    unverified: int = 0
    out_of_scope: int = 0
    items: List[CoverageManifestItem] = Field(default_factory=list)
    sub_concepts_total: int = 0
    sub_concepts_covered: int = 0
    sub_concepts_partial: int = 0
    sub_concepts_missing: int = 0
    sub_concepts_unverified: int = 0


class RenderingDefectType(str, Enum):
    RAW_LATEX_DELIMITER = "RAW_LATEX_DELIMITER"
    RAW_LATEX_COMMAND = "RAW_LATEX_COMMAND"
    RAW_LATEX_ESCAPE = "RAW_LATEX_ESCAPE"
    BROKEN_SUPERSCRIPT = "BROKEN_SUPERSCRIPT"
    BROKEN_SUBSCRIPT = "BROKEN_SUBSCRIPT"
    MATH_RENDER_FAILURE = "MATH_RENDER_FAILURE"
    CHEMICAL_FORMULA_UNRENDERED = "CHEMICAL_FORMULA_UNRENDERED"
    HYBRIDIZATION_UNRENDERED = "HYBRIDIZATION_UNRENDERED"
    MISSING_GLYPH = "MISSING_GLYPH"
    CLIPPING = "CLIPPING"
    OVERFLOW = "OVERFLOW"
    FOOTER_COLLISION = "FOOTER_COLLISION"
    BLANK_PAGE = "BLANK_PAGE"
    DOCUMENT_TRUNCATED = "DOCUMENT_TRUNCATED"
    PDF_CORRUPT = "PDF_CORRUPT"


class RenderingDefect(BaseModel):
    type: RenderingDefectType
    page: Optional[int] = None
    message: str
    severity: str = "critical"  # "critical", "error", "warning"
    snippet: Optional[str] = None


class ContentCertificationResult(BaseModel):
    status: str = "passed"
    valid: bool = True
    coverage: CoverageManifest = Field(default_factory=CoverageManifest)
    substantive_score: float = 100.0
    findings: List[str] = Field(default_factory=list)
    worked_example_quality: Dict[str, Any] = Field(default_factory=dict)
    practice_distribution: Dict[str, Any] = Field(default_factory=dict)


class ArtifactCertificationResult(BaseModel):
    status: str = "passed"
    valid: bool = True
    pages: int = 0
    raw_latex_count: int = 0
    clipping_count: int = 0
    overflow_count: int = 0
    broken_equations_count: int = 0
    defects: List[RenderingDefect] = Field(default_factory=list)
    practice_valid_count: int = 0
    practice_required_count: int = 0


class DocumentQualityResult(BaseModel):
    """
    Master Student Artifact Certification Result.
    Cryptographically binds certified PDF to exact NotesDocument version.
    """
    schema_version: str = "1.0"
    artifact_status: ArtifactStatus
    document_id: str
    document_version: str = "1.0"
    document_hash: str
    renderer_version: str = "1.0.0-playwright-chromium"
    render_config_hash: str = ""
    pdf_hash: str
    certification_id: str = ""
    certification_status: str = ""
    content_certification: ContentCertificationResult
    artifact_certification: ArtifactCertificationResult
    coverage: Dict[str, int] = Field(default_factory=dict)
    rendering: Dict[str, int] = Field(default_factory=dict)
    practice: Dict[str, int] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class CertifyArtifactRequest(BaseModel):
    """Request payload for artifact certification endpoint."""
    document: Dict[str, Any]
    pdf_base64: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    plan: Optional[Dict[str, Any]] = None
    html_content: Optional[str] = None

