"""
LearnByGenie — Mastery + Prerequisite Knowledge Graph API (Feature 3)
=====================================================================
REST API endpoints for:
- Subject knowledge graph retrieval (nodes, readiness, blocked concepts)
- Prerequisite repair paths & explainable next-concept recommendations
- Ingesting diagnostic evidence and future practice/quiz evidence
- Graph topology audit
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from app.core.dependencies import get_current_user
from app.services.mastery.service import MasteryGraphService
from app.services.mastery.schemas import (
    SubjectGraphView, SkillNodeView, LearningRecommendation,
    LearnerSkillState, GraphAuditReport, EvidenceSource,
    AssistanceLevel
)
from app.services.diagnostic.repository import DiagnosticRepository

router = APIRouter()


def _get_verified_user_id(current_user) -> str:
    user_id = str(getattr(current_user, "id", None) or "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID could not be identified from credentials."
        )
    return user_id


class IngestDiagnosticRequest(BaseModel):
    session_id: str


class IngestEvidenceRequest(BaseModel):
    skill_id: str
    source_type: EvidenceSource = EvidenceSource.PRACTICE
    source_record_id: str
    correctness: bool
    independence_level: AssistanceLevel = AssistanceLevel.INDEPENDENT
    metadata: Dict[str, Any] = {}


@router.get(
    "/graph",
    response_model=SubjectGraphView,
    summary="Get explainable student knowledge graph for a subject",
    description="Returns all skills, mastery states, DAG readiness, blocked concepts, repair paths, and recommendations."
)
async def get_subject_graph(
    subject: str = Query(default="Mathematics", description="Subject name (e.g. Mathematics, Physics, Chemistry, Biology, Computer Science)"),
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    return MasteryGraphService.get_subject_graph(user_id=user_id, subject=subject)


@router.get(
    "/recommendations",
    response_model=List[LearningRecommendation],
    summary="Get explainable next learning recommendations",
    description="Returns next unlocked concepts and prerequisite repair starts for the student."
)
async def get_learning_recommendations(
    subject: str = Query(default="Mathematics"),
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    return MasteryGraphService.get_next_learning_recommendations(user_id=user_id, subject=subject)


@router.get(
    "/blocked",
    response_model=List[SkillNodeView],
    summary="Get skills blocked by prerequisite requirements",
    description="Identifies concepts that cannot be studied yet because foundational skills require repair."
)
async def get_blocked_skills(
    subject: str = Query(default="Mathematics"),
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    return MasteryGraphService.get_blocked_skills(user_id=user_id, subject=subject)


@router.get(
    "/repair-path/{skill_id}",
    response_model=List[str],
    summary="Get shortest meaningful prerequisite repair path for a skill",
    description="Traverses upstream DAG ancestors to find foundational skills needing repair."
)
async def get_repair_path(
    skill_id: str,
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    return MasteryGraphService.get_repair_path(user_id=user_id, skill_id=skill_id)


@router.post(
    "/ingest-diagnostic",
    response_model=List[LearnerSkillState],
    summary="Ingest completed Feature 2 diagnostic session into mastery graph",
    description="Idempotently converts diagnostic results into durable mastery states."
)
async def ingest_diagnostic(
    req: IngestDiagnosticRequest,
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    session = DiagnosticRepository.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Diagnostic session not found.")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized access to diagnostic session.")

    result = DiagnosticRepository.get_result(req.session_id)
    if not result:
        raise HTTPException(status_code=400, detail="Diagnostic session is not yet completed or has no result.")

    return MasteryGraphService.ingest_diagnostic_evidence(
        user_id=user_id,
        session_id=session.id,
        contract_payload=result.feature3_contract_payload
    )


@router.post(
    "/ingest-evidence",
    response_model=LearnerSkillState,
    summary="Ingest practice/quiz/tutor evidence",
    description="General evidence ingestion interface for future Practice and Revision engines."
)
async def ingest_evidence(
    req: IngestEvidenceRequest,
    current_user=Depends(get_current_user)
):
    user_id = _get_verified_user_id(current_user)
    state, _ = MasteryGraphService.ingest_evidence(
        user_id=user_id,
        skill_id=req.skill_id,
        source_type=req.source_type,
        source_record_id=req.source_record_id,
        correctness=req.correctness,
        independence_level=req.independence_level,
        metadata=req.metadata
    )
    return state


@router.get(
    "/audit",
    response_model=GraphAuditReport,
    summary="Audit prerequisite graph topology",
    description="Audits graph for cycles, self-edges, duplicate edges, and orphan nodes."
)
async def audit_graph(
    current_user=Depends(get_current_user)
):
    return MasteryGraphService.audit_prerequisite_graph()
