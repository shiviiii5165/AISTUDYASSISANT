"""Student Artifact Certification & PDF Quality Gate package.

Exports:
    - StudentArtifactCertifier: Master certifier
    - LaTeXScanner: Raw LaTeX and delimiter leak detection
    - NotationQACertifier: Chemical and mathematical notation certifier
    - GeometryQACertifier: Physical PDF geometry, clipping, overflow inspector
    - VisualInspector: Rasterized visual inspection
    - CoverageCertifier: Substantive curriculum coverage certifier
    - All core certification schemas and enums
"""

from app.services.notes.certification.schemas import (
    ArtifactStatus,
    CoverageStatus,
    CoverageEvidenceType,
    CoverageManifestItem,
    CoverageManifest,
    RenderingDefectType,
    RenderingDefect,
    ContentCertificationResult,
    ArtifactCertificationResult,
    DocumentQualityResult,
    CertifyArtifactRequest,
)
from app.services.notes.certification.latex_scanner import LaTeXScanner
from app.services.notes.certification.notation_qa import NotationQACertifier
from app.services.notes.certification.geometry_qa import GeometryQACertifier
from app.services.notes.certification.visual_inspector import VisualInspector
from app.services.notes.certification.coverage_certifier import CoverageCertifier
from app.services.notes.certification.certifier import StudentArtifactCertifier

__all__ = [
    "ArtifactStatus",
    "CoverageStatus",
    "CoverageEvidenceType",
    "CoverageManifestItem",
    "CoverageManifest",
    "RenderingDefectType",
    "RenderingDefect",
    "ContentCertificationResult",
    "ArtifactCertificationResult",
    "DocumentQualityResult",
    "LaTeXScanner",
    "NotationQACertifier",
    "GeometryQACertifier",
    "VisualInspector",
    "CoverageCertifier",
    "StudentArtifactCertifier",
]
