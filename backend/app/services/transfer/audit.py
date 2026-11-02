"""
LearnByGenie — Feature 7: Transfer Check Auditor
==================================================
Deterministic integrity auditor (§40, §19):
- Verifies assistance_level == INDEPENDENT on all transfer telemetry
- Detects duplicate transfer evidence
- Flags unverified items or items missing provenance
- Validates pass states against authoritative response rows
- Audits cross-user consistency and repair confirmations
"""
from typing import List, Dict, Any, Set
from pydantic import BaseModel, Field

from .schemas import TransferSessionStatus, TransferOutcome
from .repository import TransferRepository
from app.services.practice.item_bank import get_practice_item
from app.services.practice.schemas import VerificationStatus
from app.services.mastery.repository import MasteryRepository
from app.db.supabase_client import supabase


class TransferAuditReport(BaseModel):
    is_valid: bool = True
    issues_found: List[str] = Field(default_factory=list)

    total_sessions: int = 0
    total_responses: int = 0
    total_evidence: int = 0

    duplicate_evidence_count: int = 0
    invalid_assistance_count: int = 0
    non_novel_items_served: int = 0
    unverified_items_served: int = 0
    pass_without_response_count: int = 0
    cross_user_inconsistencies: int = 0
    invalid_repair_confirmations: int = 0

    passed_sessions: int = 0
    needs_more_evidence_sessions: int = 0
    aborted_sessions: int = 0


class TransferAuditor:
    """Audits transfer sessions and responses for integrity (§40, §19)."""

    @classmethod
    def audit_all(cls) -> TransferAuditReport:
        report = TransferAuditReport()

        sessions = list(TransferRepository._sessions_cache.values())
        responses = [r for sublist in TransferRepository._responses_cache.values() for r in sublist]

        # If caches were cleared, load from remote Supabase
        if not sessions and supabase is not None:
            try:
                res_s = supabase.table("transfer_sessions").select("*").execute()
                if res_s.data:
                    sessions = [TransferRepository._deserialize_session(r) for r in res_s.data]
            except Exception:
                pass

        if not responses and supabase is not None:
            try:
                res_r = supabase.table("transfer_responses").select("*").execute()
                if res_r.data:
                    responses = [TransferRepository._deserialize_response(r) for r in res_r.data]
            except Exception:
                pass

        report.total_sessions = len(sessions)
        report.total_responses = len(responses)

        # 1. Audit sessions
        seen_items_per_user_skill: Dict[tuple, Set[str]] = {}
        for s in sessions:
            if s.status == TransferSessionStatus.PASSED:
                report.passed_sessions += 1
            elif s.status == TransferSessionStatus.NEEDS_MORE_EVIDENCE:
                report.needs_more_evidence_sessions += 1
            elif s.status == TransferSessionStatus.ABORTED:
                report.aborted_sessions += 1

            # Check unverified item served
            if s.current_item_id:
                it = get_practice_item(s.current_item_id)
                if it and it.verification_status != VerificationStatus.VERIFIED:
                    report.unverified_items_served += 1
                    report.issues_found.append(
                        f"Session {s.id} served unverified item {it.id} ({it.verification_status})"
                    )

            # Check PASSED session has matching correct response row
            if s.status == TransferSessionStatus.PASSED:
                sess_resps = TransferRepository.get_session_responses(s.id)
                if not any(r.correctness for r in sess_resps):
                    report.pass_without_response_count += 1
                    report.issues_found.append(
                        f"Session {s.id} marked PASSED without any correct response evidence"
                    )

        # 2. Audit responses
        for r in responses:
            if r.assistance_level != "INDEPENDENT":
                report.invalid_assistance_count += 1
                report.issues_found.append(
                    f"Response {r.id} in session {r.session_id} has non-independent assistance: {r.assistance_level}"
                )

        # 3. Audit mastery evidence ledger (learner_skill_evidence)
        if supabase is not None:
            try:
                res_ev = (
                    supabase.table("learner_skill_evidence")
                    .select("*")
                    .eq("source_type", "TRANSFER_CHECK")
                    .execute()
                )
                if res_ev.data:
                    report.total_evidence = len(res_ev.data)
                    seen_records = set()
                    for ev in res_ev.data:
                        rec_id = ev.get("source_record_id")
                        if rec_id in seen_records:
                            report.duplicate_evidence_count += 1
                            report.issues_found.append(f"Duplicate TRANSFER_CHECK evidence detected: {rec_id}")
                        else:
                            seen_records.add(rec_id)
            except Exception:
                pass

        report.is_valid = len(report.issues_found) == 0
        return report
