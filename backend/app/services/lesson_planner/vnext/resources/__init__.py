"""
Resource Intelligence Suite for Lesson Planner VNext
=====================================================
Includes:
- Resource Source Registry & Need Detector
- YouTube Segment Precision Intelligence Engine
- Academic Evidence Engine (Q1-Q4, A*, safety gates, paper sections)
- Course Intelligence Engine (NPTEL, MIT OCW, SWAYAM, module/lecture mapping)
- Coding Resource Engine (GFG vs LeetCode)
- Official Documentation Engine
- Resource Trust & Universal Resource Card Builder
- Redundancy Detector & Minimum Effective Resource Set Optimizer
- Resource Outcome Learning & Adaptive Ranking Engine
- Source Health Telemetry & Circuit Breaker Tracking
- Unified Resource Intelligence Contracts
"""

from .contracts import (
    ResourcePurpose, ResourceFeedbackType, ResourceIntent,
    ResourceProvenance, ResourceQualityScore, ResourceSegment,
    CourseResource, NormalizedResource, ResourceCandidate,
    ResourceOutcomeSignal, ProviderHealthRecord, ResourceBundle
)
from .registry import ResourceSourceEntry, BUILTIN_SOURCE_REGISTRY, ResourceNeedDetector
from .youtube_router import YouTubeSegmentRouter
from .academic_engine import AcademicEvidenceEngine
from .course_engine import CourseIntelligenceEngine
from .coding_engine import CodingResourceEngine
from .docs_engine import OfficialDocsEngine
from .redundancy_detector import RedundancyDetector
from .outcome_engine import ResourceOutcomeEngine
from .source_health import SourceHealthTracker
from .trust_engine import ResourceTrustEngine

__all__ = [
    "ResourcePurpose",
    "ResourceFeedbackType",
    "ResourceIntent",
    "ResourceProvenance",
    "ResourceQualityScore",
    "ResourceSegment",
    "CourseResource",
    "NormalizedResource",
    "ResourceCandidate",
    "ResourceOutcomeSignal",
    "ProviderHealthRecord",
    "ResourceBundle",
    "ResourceSourceEntry",
    "BUILTIN_SOURCE_REGISTRY",
    "ResourceNeedDetector",
    "YouTubeSegmentRouter",
    "AcademicEvidenceEngine",
    "CourseIntelligenceEngine",
    "CodingResourceEngine",
    "OfficialDocsEngine",
    "RedundancyDetector",
    "ResourceOutcomeEngine",
    "SourceHealthTracker",
    "ResourceTrustEngine"
]
