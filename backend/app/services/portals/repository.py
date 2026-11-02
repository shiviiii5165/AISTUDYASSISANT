from datetime import datetime, timezone, date, timedelta
from typing import Dict, Any, Optional, List
import threading
import uuid
import copy
import secrets

from app.db.supabase_client import supabase
from app.core.logging import logger
from app.services.practice.item_bank import register_practice_item, PracticeItem, VerificationStatus


class PortalsRepository:
    """Thread-safe persistence layer for multi-tenant institutional portals and parent-student security."""
    _LOCK = threading.RLock()
    _SCHOOLS: Dict[str, Dict[str, Any]] = {}
    _MEMBERSHIPS: List[Dict[str, Any]] = []
    _CLASSROOMS: Dict[str, Dict[str, Any]] = {}
    _ENROLLMENTS: List[Dict[str, Any]] = []
    _PARENT_LINKS: List[Dict[str, Any]] = []
    _INVITE_CODES: Dict[str, Dict[str, Any]] = {}
    _CREATOR_ITEMS: Dict[str, Dict[str, Any]] = {}
    _PARENT_AUDIT_LOG: List[Dict[str, Any]] = []

    @classmethod
    def clear_memory_cache(cls):
        with cls._LOCK:
            cls._SCHOOLS.clear()
            cls._MEMBERSHIPS.clear()
            cls._CLASSROOMS.clear()
            cls._ENROLLMENTS.clear()
            cls._PARENT_LINKS.clear()
            cls._INVITE_CODES.clear()
            cls._CREATOR_ITEMS.clear()
            cls._PARENT_AUDIT_LOG.clear()

    @classmethod
    def get_or_create_default_school(cls) -> Dict[str, Any]:
        with cls._LOCK:
            if not cls._SCHOOLS:
                sch_id = "11111111-2222-3333-4444-555555555555"
                sch = {
                    "id": sch_id,
                    "name": "Delhi Public School RK Puram",
                    "domain": "dpsrkp.net",
                    "subscription_tier": "enterprise",
                    "max_seats": 500,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                cls._SCHOOLS[sch_id] = sch
            return copy.deepcopy(list(cls._SCHOOLS.values())[0])

    # ─── PARENT REPOSITORY METHODS ────────────────────────────────────────────

    @classmethod
    def generate_student_invite_code(cls, student_id: str, expires_in_hours: int = 24) -> str:
        """
        Generates a cryptographically secure, high-entropy single-use invitation code.
        Format: GENIE-XXXX-YYYY (using secrets.choice over unambiguous alphanumeric set).
        Persists to PostgreSQL parent_student_invitations table with explicit expiration.
        """
        charset = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        part1 = "".join(secrets.choice(charset) for _ in range(4))
        part2 = "".join(secrets.choice(charset) for _ in range(4))
        code = f"GENIE-{part1}-{part2}"

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=expires_in_hours)
        now_iso = now.isoformat()
        exp_iso = expires_at.isoformat()
        inv_id = str(uuid.uuid4())

        record = {
            "id": inv_id,
            "code": code,
            "student_id": student_id,
            "created_at": now_iso,
            "expires_at": exp_iso,
            "is_redeemed": False,
            "is_revoked": False,
            "redeemed_by_parent_id": None,
            "redeemed_at": None
        }

        with cls._LOCK:
            cls._INVITE_CODES[code] = record
            cls._PARENT_AUDIT_LOG.append({
                "id": str(uuid.uuid4()),
                "event_type": "INVITATION_GENERATED",
                "student_id": student_id,
                "parent_id": None,
                "invitation_code": code,
                "metadata": {"expires_at": exp_iso},
                "created_at": now_iso
            })

        # Persist to database if available
        if supabase is not None:
            try:
                supabase.table("parent_student_invitations").insert({
                    "id": inv_id,
                    "student_id": student_id,
                    "invitation_code": code,
                    "expires_at": exp_iso,
                    "is_redeemed": False,
                    "is_revoked": False,
                    "created_at": now_iso
                }).execute()

                supabase.table("parent_student_audit").insert({
                    "event_type": "INVITATION_GENERATED",
                    "student_id": student_id,
                    "invitation_code": code,
                    "metadata": {"expires_at": exp_iso}
                }).execute()
            except Exception as e:
                logger.warning(f"[PortalsRepo] Failed to persist invitation to database: {e}")

        return code

    @classmethod
    def revoke_student_invite_code(cls, student_id: str, invite_code: str) -> bool:
        """Allows a student to revoke an unused pending invitation code."""
        code_clean = (invite_code or "").strip().upper()
        now_iso = datetime.now(timezone.utc).isoformat()
        with cls._LOCK:
            inv = cls._INVITE_CODES.get(code_clean)
            if not inv or inv.get("student_id") != student_id:
                return False
            if inv.get("is_redeemed"):
                raise ValueError("Cannot revoke an invitation code that has already been redeemed.")
            inv["is_revoked"] = True

            cls._PARENT_AUDIT_LOG.append({
                "id": str(uuid.uuid4()),
                "event_type": "INVITATION_REVOKED",
                "student_id": student_id,
                "parent_id": None,
                "invitation_code": code_clean,
                "created_at": now_iso
            })

        if supabase is not None:
            try:
                supabase.table("parent_student_invitations").update({
                    "is_revoked": True
                }).eq("invitation_code", code_clean).eq("student_id", student_id).execute()

                supabase.table("parent_student_audit").insert({
                    "event_type": "INVITATION_REVOKED",
                    "student_id": student_id,
                    "invitation_code": code_clean,
                    "metadata": {}
                }).execute()
            except Exception:
                pass
        return True

    @classmethod
    def link_parent_with_code(cls, parent_id: str, invite_code: str, relationship: str = "guardian") -> Dict[str, Any]:
        """
        Validates an invitation code and creates a verified parent-student link.
        Enforces:
        1. Removal of all demo codes. Direct student UUID linking is strictly rejected.
        2. Cryptographic code lookup in PostgreSQL / memory store.
        3. Single-use redemption (atomic compare-and-swap).
        4. Expiration check.
        5. Revocation check.
        6. Replay attack rejection.
        7. Audit logging.
        """
        code_clean = (invite_code or "").strip().upper()
        if not code_clean:
            raise ValueError("Invitation code cannot be empty.")

        # Reject direct UUID linking attempts
        if len(code_clean) == 36 and "-" in code_clean:
            raise ValueError("Direct student UUID linking is prohibited for child safety. Student must generate a secure invitation code.")

        # Reject legacy demo codes
        if code_clean in ("DEMO-CHILD-1", "DEMO-CHILD", "GENIE-DEMO"):
            raise ValueError("Demo invitation codes are not valid in production.")

        now = datetime.now(timezone.utc)

        with cls._LOCK:
            invitation = None

            # 1. Check database if connected
            if supabase is not None:
                try:
                    res = supabase.table("parent_student_invitations").select("*").eq("invitation_code", code_clean).limit(1).execute()
                    if res.data and len(res.data) > 0:
                        invitation = res.data[0]
                except Exception as e:
                    logger.debug(f"[PortalsRepo] DB query invitation notice: {e}")

            # 2. Check local store if not found in DB
            if not invitation:
                invitation = cls._INVITE_CODES.get(code_clean)

            if not invitation:
                raise ValueError("Invalid invitation code: not found.")

            student_id = invitation.get("student_id")
            if not student_id:
                raise ValueError("Corrupt invitation record: missing student_id.")

            # Check revocation
            if invitation.get("is_revoked"):
                raise ValueError("Invitation code has been revoked by the student.")

            # Check single-use redemption (replay attack check)
            if invitation.get("is_redeemed"):
                raise ValueError("Invitation code has already been redeemed. Each invitation code is strictly single-use.")

            # Check expiration
            exp_raw = invitation.get("expires_at")
            if exp_raw:
                if isinstance(exp_raw, str):
                    exp_dt = datetime.fromisoformat(exp_raw.replace("Z", "+00:00"))
                else:
                    exp_dt = exp_raw
                if now > exp_dt:
                    raise ValueError("Invitation code has expired. Please request a new code from the student.")

            from app.modules.privacy import service as privacy

            if not privacy.has_consent(student_id, "parent_reports"):
                raise PermissionError("consent_required")

            # Atomic mark as redeemed
            invitation["is_redeemed"] = True
            invitation["redeemed_by_parent_id"] = parent_id
            invitation["redeemed_at"] = now.isoformat()
            cls._INVITE_CODES[code_clean] = invitation

            # Check if link already exists
            for link in cls._PARENT_LINKS:
                if link["parent_id"] == parent_id and link["student_id"] == student_id:
                    return copy.deepcopy(link)

            link_id = str(uuid.uuid4())
            now_iso = now.isoformat()
            link_rec = {
                "id": link_id,
                "parent_id": parent_id,
                "student_id": student_id,
                "relationship": relationship,
                "verification_status": "verified",
                "linked_at": now_iso
            }
            cls._PARENT_LINKS.append(link_rec)

            cls._PARENT_AUDIT_LOG.append({
                "id": str(uuid.uuid4()),
                "event_type": "INVITATION_REDEEMED",
                "student_id": student_id,
                "parent_id": parent_id,
                "invitation_code": code_clean,
                "metadata": {"relationship": relationship},
                "created_at": now_iso
            })

            # Persist redemption, link, and audit to PostgreSQL
            if supabase is not None:
                try:
                    supabase.table("parent_student_invitations").update({
                        "is_redeemed": True,
                        "redeemed_by_parent_id": parent_id,
                        "redeemed_at": now_iso
                    }).eq("invitation_code", code_clean).execute()

                    supabase.table("parent_student_links").upsert({
                        "id": link_id,
                        "parent_id": parent_id,
                        "student_id": student_id,
                        "relationship": relationship,
                        "verification_status": "verified",
                        "linked_at": now_iso
                    }, on_conflict="parent_id,student_id").execute()

                    supabase.table("parent_student_audit").insert({
                        "event_type": "INVITATION_REDEEMED",
                        "student_id": student_id,
                        "parent_id": parent_id,
                        "invitation_code": code_clean,
                        "metadata": {"relationship": relationship}
                    }).execute()
                except Exception as e:
                    logger.warning(f"[PortalsRepo] Failed to persist link to database: {e}")

            return copy.deepcopy(link_rec)

    @classmethod
    def get_linked_student_ids(cls, parent_id: str) -> List[str]:
        """Returns student IDs verified and linked to this parent."""
        with cls._LOCK:
            # Query remote Supabase if available
            if supabase is not None:
                try:
                    res = supabase.table("parent_student_links").select("student_id").eq("parent_id", parent_id).eq("verification_status", "verified").execute()
                    if res.data:
                        remote_ids = [r["student_id"] for r in res.data]
                        for s_id in remote_ids:
                            if not any(l["parent_id"] == parent_id and l["student_id"] == s_id for l in cls._PARENT_LINKS):
                                cls._PARENT_LINKS.append({
                                    "id": str(uuid.uuid4()),
                                    "parent_id": parent_id,
                                    "student_id": s_id,
                                    "relationship": "guardian",
                                    "verification_status": "verified",
                                    "linked_at": datetime.now(timezone.utc).isoformat()
                                })
                except Exception as e:
                    logger.debug(f"[PortalsRepo] DB query parent links notice: {e}")

            return [
                link["student_id"] for link in cls._PARENT_LINKS
                if link["parent_id"] == parent_id and link.get("verification_status") == "verified"
            ]

    @classmethod
    def link_parent_child(cls, parent_id: str, student_id: str, relationship: str = "guardian") -> Dict[str, Any]:
        """Internal linkage helper for system/seed workflows."""
        with cls._LOCK:
            for link in cls._PARENT_LINKS:
                if link["parent_id"] == parent_id and link["student_id"] == student_id:
                    return copy.deepcopy(link)
            rec = {
                "id": str(uuid.uuid4()),
                "parent_id": parent_id,
                "student_id": student_id,
                "relationship": relationship,
                "verification_status": "verified",
                "linked_at": datetime.now(timezone.utc).isoformat()
            }
            cls._PARENT_LINKS.append(rec)
            return copy.deepcopy(rec)

    # ─── TEACHER REPOSITORY METHODS ───────────────────────────────────────────

    @classmethod
    def get_teacher_classrooms(cls, teacher_id: str) -> List[Dict[str, Any]]:
        school = cls.get_or_create_default_school()
        with cls._LOCK:
            if not cls._CLASSROOMS:
                cls_id = "c1111111-2222-3333-4444-555555555555"
                cls._CLASSROOMS[cls_id] = {
                    "id": cls_id,
                    "school_id": school["id"],
                    "teacher_id": teacher_id,
                    "name": "Class 10-A (Mathematics & Physics)",
                    "grade_level": "Class 10",
                    "academic_stream": "science_pcm",
                    "academic_year": "2026-2027",
                    "created_at": datetime.now(timezone.utc)
                }
                cls._ENROLLMENTS.append({
                    "id": str(uuid.uuid4()),
                    "classroom_id": cls_id,
                    "student_id": "a56da972-0f19-418d-b0f7-de91ff114190",
                    "status": "enrolled",
                    "enrolled_at": datetime.now(timezone.utc)
                })

            return [c for c in cls._CLASSROOMS.values() if c["teacher_id"] == teacher_id]

    @classmethod
    def create_classroom(cls, teacher_id: str, name: str, grade_level: str, academic_stream: str, academic_year: str) -> Dict[str, Any]:
        school = cls.get_or_create_default_school()
        cls_id = str(uuid.uuid4())
        record = {
            "id": cls_id,
            "school_id": school["id"],
            "teacher_id": teacher_id,
            "name": name,
            "grade_level": grade_level,
            "academic_stream": academic_stream,
            "academic_year": academic_year,
            "created_at": datetime.now(timezone.utc)
        }
        with cls._LOCK:
            cls._CLASSROOMS[cls_id] = record
            return copy.deepcopy(record)

    @classmethod
    def get_classroom_students(cls, classroom_id: str) -> List[str]:
        with cls._LOCK:
            return [
                e["student_id"] for e in cls._ENROLLMENTS
                if e["classroom_id"] == classroom_id and e["status"] == "enrolled"
            ]

    # ─── CREATOR ITEM REVIEW WORKFLOW METHODS ──────────────────────────────────

    @classmethod
    def save_creator_item(cls, item: PracticeItem, author_id: str) -> Dict[str, Any]:
        """Persists a new creator question in PENDING_REVIEW state."""
        now_iso = datetime.now(timezone.utc).isoformat()
        rec = {
            "id": item.id,
            "skill_id": item.skill_id,
            "subject": item.subject,
            "grade_band": item.grade_band,
            "difficulty_band": item.difficulty_band.value if hasattr(item.difficulty_band, "value") else str(item.difficulty_band),
            "question_type": item.question_type.value if hasattr(item.question_type, "value") else str(item.question_type),
            "prompt": item.prompt,
            "options": item.options,
            "correct_answer": item.correct_answer,
            "explanation": item.explanation,
            "hints": item.hints,
            "target_mistake_types": item.target_mistake_types,
            "author_id": author_id,
            "review_status": "pending_review",
            "reviewed_by": None,
            "review_notes": None,
            "reviewed_at": None,
            "created_at": now_iso,
            "updated_at": now_iso
        }
        with cls._LOCK:
            cls._CREATOR_ITEMS[item.id] = rec

        if supabase is not None:
            try:
                supabase.table("creator_practice_items").insert(rec).execute()
            except Exception as e:
                logger.warning(f"[PortalsRepo] Failed to persist creator item to database: {e}")

        return copy.deepcopy(rec)

    @classmethod
    def approve_creator_item(cls, item_id: str, reviewer_id: str) -> Optional[Dict[str, Any]]:
        """Approves a question item and publishes it to the verified practice item bank."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with cls._LOCK:
            rec = cls._CREATOR_ITEMS.get(item_id)
            if not rec:
                return None
            rec["review_status"] = "approved"
            rec["reviewed_by"] = reviewer_id
            rec["reviewed_at"] = now_iso
            rec["updated_at"] = now_iso

            # Publish to canonical active item bank as verified
            verified_item = PracticeItem(
                id=rec["id"],
                skill_id=rec["skill_id"],
                subject=rec["subject"],
                grade_band=rec["grade_band"],
                difficulty_band=rec["difficulty_band"],
                question_type=rec["question_type"],
                prompt=rec["prompt"],
                options=rec["options"],
                correct_answer=rec["correct_answer"],
                explanation=rec["explanation"],
                hints=rec["hints"],
                target_mistake_types=rec["target_mistake_types"],
                verification_status=VerificationStatus.VERIFIED
            )
            register_practice_item(verified_item)

        if supabase is not None:
            try:
                supabase.table("creator_practice_items").update({
                    "review_status": "approved",
                    "reviewed_by": reviewer_id,
                    "reviewed_at": now_iso,
                    "updated_at": now_iso
                }).eq("id", item_id).execute()
            except Exception as e:
                logger.warning(f"[PortalsRepo] Failed to update creator item status in database: {e}")

        return copy.deepcopy(rec)

    @classmethod
    def reject_creator_item(cls, item_id: str, reviewer_id: str, notes: str) -> Optional[Dict[str, Any]]:
        """Rejects a question item with feedback notes."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with cls._LOCK:
            rec = cls._CREATOR_ITEMS.get(item_id)
            if not rec:
                return None
            rec["review_status"] = "rejected"
            rec["reviewed_by"] = reviewer_id
            rec["review_notes"] = notes
            rec["reviewed_at"] = now_iso
            rec["updated_at"] = now_iso

        if supabase is not None:
            try:
                supabase.table("creator_practice_items").update({
                    "review_status": "rejected",
                    "reviewed_by": reviewer_id,
                    "review_notes": notes,
                    "reviewed_at": now_iso,
                    "updated_at": now_iso
                }).eq("id", item_id).execute()
            except Exception as e:
                logger.warning(f"[PortalsRepo] Failed to update creator item status in database: {e}")

        return copy.deepcopy(rec)

    @classmethod
    def get_pending_creator_items(cls) -> List[Dict[str, Any]]:
        """Returns all questions waiting for review."""
        with cls._LOCK:
            return [copy.deepcopy(r) for r in cls._CREATOR_ITEMS.values() if r.get("review_status") == "pending_review"]
