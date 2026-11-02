"""DPDP Act 2023: verifiable parental consent, data export and 72-hour erasure."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import io
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.modules import store

OTP_TTL_MINUTES = 10
MAX_OTP_ATTEMPTS = 5
MAX_OTPS_PER_HOUR = 5
ERASURE_DEADLINE_HOURS = 72
PURPOSES = ("learning_analytics", "parent_reports", "school_sharing")

# (table, owner column). Includes earlier features so that erasure is complete.
PERSONAL_TABLES: tuple[tuple[str, str], ...] = (
    ("practice_attempts_v1", "student_id"), ("practice_sessions_v1", "student_id"),
    ("error_tokens", "student_id"), ("learner_bkt_state", "student_id"),
    ("review_schedule", "student_id"), ("cat_sessions", "student_id"),
    ("xp_events", "student_id"), ("tutor_audit", "student_id"),
    ("tutor_sessions_v1", "student_id"), ("safety_events", "student_id"),
    ("quests", "student_id"), ("activity_days", "student_id"),
    ("guild_members", "student_id"), ("league_entries", "student_id"),
    ("implementation_intentions", "student_id"), ("homework_assignments", "student_id"),
    ("xp_ledger", "user_id"), ("learner_streaks", "user_id"), ("learner_badges", "user_id"),
    ("spaced_repetition_reviews", "user_id"), ("spaced_repetition_cards", "user_id"),
    ("mistake_events", "user_id"), ("mistake_patterns", "user_id"),
    ("learner_skill_evidence", "user_id"), ("learner_skill_states", "user_id"),
    ("practice_responses", "user_id"), ("practice_sessions", "user_id"),
    ("diagnostic_responses", "user_id"), ("diagnostic_results", "user_id"),
    ("diagnostic_skill_results", "user_id"),
    ("diagnostic_sessions", "user_id"), ("learner_profiles", "user_id"),
    # Quiz and attempts.
    ("quiz_attempts", "user_id"), ("quiz_scores", "user_id"), ("quiz_results", "user_id"),
    ("quizzes", "owner_user_id"), ("live_quiz_participants", "user_id"),
    # Tutor and chat.
    ("socratic_check_responses", "user_id"), ("socratic_tutor_sessions", "user_id"),
    ("chat_sessions", "user_id"), ("teach_sessions", "user_id"),
    # Notes and generated content.
    ("generated_notes", "user_id"), ("topic_decks", "user_id"), ("video_lessons", "user_id"),
    ("document_chunks", "user_id"), ("pdfs", "user_id"),
    # Attempts and evidence.
    ("step_grader_steps", "user_id"), ("step_grader_attempts", "user_id"), ("step_grader_sessions", "user_id"),
    ("transfer_responses", "user_id"), ("transfer_sessions", "user_id"), ("mistake_repair_events", "user_id"),
    ("learning_evidence", "student_id"), ("student_concept_state", "student_id"),
    ("student_misconceptions", "student_id"), ("learner_mastery", "user_id"),
    # Plans, usage and telemetry.
    ("roadmap_events", "user_id"), ("learning_roadmaps", "user_id"), ("course_graphs", "user_id"),
    ("daily_usage", "user_id"), ("monthly_deck_usage", "user_id"), ("daily_activity", "user_id"),
    # Links and identity data.
    ("classroom_enrollments", "student_id"), ("parent_student_links", "student_id"),
    ("parent_student_invitations", "student_id"), ("parent_student_audit", "student_id"),
    ("consent_otps", "student_id"), ("mfa_factors", "user_id"), ("profiles", "id"),
)
# Rows owned through a parent, removed before the parent: (table, fk, parent, parent owner).
CHILD_TABLES: tuple[tuple[str, str, str, str], ...] = (
    ("chat_messages", "session_id", "chat_sessions", "user_id"),
    ("live_quiz_responses", "participant_id", "live_quiz_participants", "user_id"),
)


class ConsentError(Exception):
    def __init__(self, code: str, status: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_dev() -> bool:
    return (settings.ENVIRONMENT or "").lower().strip() in ("development", "test", "local")


def _otp_key() -> bytes:
    secret = os.environ.get("OTP_HASH_SECRET") or settings.SUPABASE_JWT_SECRET
    if not secret:
        if _is_dev():
            return b"local-development-only"
        raise ConsentError("otp_not_configured", 503)
    return str(secret).encode()


def _hash(otp: str, request_id: str) -> str:
    return hmac.new(_otp_key(), f"{request_id}:{otp}".encode(), hashlib.sha256).hexdigest()


def _deliver(contact: str, otp: str) -> bool:
    """Send through OTP_WEBHOOK_URL (your SMS or email gateway). True if handed over."""
    url = os.environ.get("OTP_WEBHOOK_URL")
    if not url:
        return False
    token = os.environ.get("OTP_WEBHOOK_TOKEN", "")
    response = httpx.post(url, json={"to": contact, "otp": otp, "minutes": OTP_TTL_MINUTES},
                          headers={"Authorization": f"Bearer {token}"}, timeout=10)
    response.raise_for_status()
    return True


def request_otp(student_id: str, guardian_contact: str, purpose: str) -> dict[str, Any]:
    if purpose not in PURPOSES:
        raise ConsentError("unknown_purpose")
    cutoff = (_now() - timedelta(hours=1)).isoformat()
    recent = [r for r in store.select("consent_otps", student_id=student_id) if r["created_at"] >= cutoff]
    if len(recent) >= MAX_OTPS_PER_HOUR:
        raise ConsentError("too_many_requests", 429)

    otp = f"{secrets.randbelow(1_000_000):06d}"
    request_id = secrets.token_urlsafe(16)
    try:
        delivered = _deliver(guardian_contact, otp)
    except httpx.HTTPError as exc:
        logger.error(f"[Consent] OTP delivery failed: {type(exc).__name__}")
        raise ConsentError("otp_delivery_failed", 502) from exc
    if not delivered and not _is_dev():
        raise ConsentError("otp_delivery_not_configured", 503)

    store.insert("consent_otps", {
        "request_id": request_id, "student_id": student_id, "purpose": purpose,
        "contact_hash": hashlib.sha256(guardian_contact.encode()).hexdigest(),
        "otp_hash": _hash(otp, request_id), "attempts": 0, "consumed": False,
        "expires_at": (_now() + timedelta(minutes=OTP_TTL_MINUTES)).isoformat(),
        "created_at": _now().isoformat(),
    })
    response = {"request_id": request_id, "expires_in_minutes": OTP_TTL_MINUTES}
    if not delivered:  # Only reachable in development.
        response["dev_otp"] = otp
    return response


def verify_otp(student_id: str, request_id: str, otp: str, guardian_id: Optional[str] = None) -> dict[str, Any]:
    row = store.get_one("consent_otps", request_id=request_id, student_id=student_id)
    if row is None:
        raise ConsentError("invalid_request", 404)
    if row["consumed"] or row["expires_at"] < _now().isoformat():
        raise ConsentError("otp_expired", 410)
    if row["attempts"] >= MAX_OTP_ATTEMPTS:
        raise ConsentError("too_many_attempts", 429)
    store.update("consent_otps", {"request_id": request_id}, {"attempts": row["attempts"] + 1})
    if not hmac.compare_digest(row["otp_hash"], _hash(otp, request_id)):
        raise ConsentError("otp_incorrect", 400)
    store.update("consent_otps", {"request_id": request_id}, {"consumed": True})
    consent = store.insert("guardian_consents", {
        "student_id": student_id, "guardian_id": guardian_id, "purpose": row["purpose"],
        "method": "otp", "granted_at": _now().isoformat(), "withdrawn_at": None,
    })
    return {"consent_id": consent["id"], "purpose": row["purpose"], "status": "granted"}


def has_consent(student_id: str, purpose: str) -> bool:
    return any(row["withdrawn_at"] is None for row in
               store.select("guardian_consents", student_id=student_id, purpose=purpose))


def withdraw(student_id: str, purpose: str) -> int:
    return store.update("guardian_consents", {"student_id": student_id, "purpose": purpose},
                        {"withdrawn_at": _now().isoformat()})


def consent_status(student_id: str) -> dict[str, bool]:
    return {purpose: has_consent(student_id, purpose) for purpose in PURPOSES}


def is_linked_guardian(parent_id: str, student_id: str) -> bool:
    return any(link.get("verification_status") == "verified" for link in
               store.select("parent_student_links", parent_id=parent_id, student_id=student_id))


def collect_export(student_id: str) -> dict[str, Any]:
    tables: dict[str, Any] = {}
    errors: list[str] = []
    for table, column in PERSONAL_TABLES + (("guardian_consents", "student_id"),):
        try:
            rows = store.select(table, **{column: student_id})
        except Exception:
            logger.error(f"[Privacy] Export could not read {table}")
            errors.append(table)
            continue
        if rows:
            tables[table] = rows
    return {"student_id": student_id, "generated_at": _now().isoformat(), "tables": tables,
            "unavailable_tables": errors}


def export_pdf(export: dict[str, Any]) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer
    from xml.sax.saxutils import escape

    styles = getSampleStyleSheet()
    code = styles["Code"].clone("export", fontSize=7, leading=9)
    story = [Paragraph("Learn Genie: your data export", styles["Title"]),
             Paragraph(f"Generated {escape(export['generated_at'])}", styles["Normal"]), Spacer(1, 12)]
    for table, rows in export["tables"].items():
        story.append(Paragraph(escape(f"{table} ({len(rows)} records)"), styles["Heading3"]))
        for row in rows:
            line = json.dumps(row, ensure_ascii=True, default=str)
            wrapped = "\n".join(line[i:i + 110] for i in range(0, len(line), 110))
            story.append(Preformatted(escape(wrapped), code))
    buffer = io.BytesIO()
    SimpleDocTemplate(buffer, pagesize=A4).build(story)
    return buffer.getvalue()


def request_erasure(student_id: str, requested_by: str) -> dict[str, Any]:
    open_requests = [r for r in store.select("erasure_requests", student_id=student_id) if r["status"] != "completed"]
    if open_requests:
        return run_erasure(open_requests[0])
    row = store.insert("erasure_requests", {
        "student_id": student_id, "requested_by": requested_by, "status": "pending", "failed_tables": [],
        "requested_at": _now().isoformat(),
        "due_at": (_now() + timedelta(hours=ERASURE_DEADLINE_HOURS)).isoformat(),
        "completed_at": None,
    })
    return run_erasure(row)


def run_erasure(request: dict[str, Any]) -> dict[str, Any]:
    """Delete everything now; tables that fail stay listed so the worker can retry them."""
    student_id = request["student_id"]
    failed: list[str] = []
    deleted = 0
    for table, foreign_key, parent, owner in CHILD_TABLES:
        try:
            for row in store.select(parent, **{owner: student_id}):
                deleted += store.delete(table, **{foreign_key: row["id"]})
        except Exception as exc:
            if not _table_absent(exc):
                logger.error(f"[Privacy] Erasure could not clear {table}")
                failed.append(table)
    for table, column in PERSONAL_TABLES:
        try:
            deleted += store.delete(table, **{column: student_id})
        except Exception as exc:
            if not _table_absent(exc):
                logger.error(f"[Privacy] Erasure could not clear {table}")
                failed.append(table)
    patch: dict[str, Any] = {"status": "partial" if failed else "completed", "failed_tables": failed,
                             "completed_at": None if failed else _now().isoformat()}
    if not failed:
        # Keep only an anonymised receipt: proof of consent and erasure, not who it was.
        pseudonym = _pseudonym(student_id)
        store.update("guardian_consents", {"student_id": student_id}, {"student_id": pseudonym, "guardian_id": None})
        patch.update(student_id=pseudonym, requested_by=_pseudonym(request["requested_by"]))
        _clear_process_caches(student_id)
    store.update("erasure_requests", {"id": request["id"]}, patch)
    return {**request, **patch, "records_deleted": deleted}


def _table_absent(exc: Exception) -> bool:
    """An optional older table that this deployment never created holds no data."""
    text = str(exc)
    return "PGRST205" in text or "42P01" in text or "does not exist" in text


def _pseudonym(identifier: str) -> str:
    digest = hmac.new(_otp_key(), f"erased:{identifier}".encode(), hashlib.sha256).hexdigest()
    return str(uuid.UUID(digest[:32]))


def _clear_process_caches(student_id: str) -> None:
    from app.services.learner_context.repository import LearnerProfileRepository

    LearnerProfileRepository.clear_memory_cache(student_id)


async def erasure_retry_loop(interval_seconds: int = 6 * 3600) -> None:
    """Runs at startup and then every 6 hours, for as long as the server process lives."""
    while True:
        try:
            processed = await asyncio.to_thread(run_pending_erasures)
            if processed:
                logger.info(f"[Privacy] Erasure retry processed {processed} request(s)")
        except Exception as exc:
            logger.error(f"[Privacy] Erasure retry failed: {type(exc).__name__}")
        await asyncio.sleep(interval_seconds)


def run_pending_erasures() -> int:
    """Retry worker: call on a schedule so that retries land inside the 72-hour limit."""
    pending = [r for r in store.select("erasure_requests") if r["status"] != "completed"]
    for request in pending:
        run_erasure(request)
    return len(pending)
