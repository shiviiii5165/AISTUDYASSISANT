from datetime import datetime, timezone, date
from typing import Dict, Any, Optional, List
import threading
import uuid
import copy

from app.db.supabase_client import supabase
from app.core.logging import logger


class PortalsRepository:
    """Thread-safe persistence layer for multi-tenant institutional portals."""
    _LOCK = threading.Lock()
    _SCHOOLS: Dict[str, Dict[str, Any]] = {}
    _MEMBERSHIPS: List[Dict[str, Any]] = []
    _CLASSROOMS: Dict[str, Dict[str, Any]] = {}
    _ENROLLMENTS: List[Dict[str, Any]] = []
    _PARENT_LINKS: List[Dict[str, Any]] = []

    @classmethod
    def clear_memory_cache(cls):
        with cls._LOCK:
            cls._SCHOOLS.clear()
            cls._MEMBERSHIPS.clear()
            cls._CLASSROOMS.clear()
            cls._ENROLLMENTS.clear()
            cls._PARENT_LINKS.clear()

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
    def get_linked_student_ids(cls, parent_id: str) -> List[str]:
        with cls._LOCK:
            # Seed default demo link if none exist for dev-parent-token
            if parent_id == "00000000-0000-0000-0000-000000000077" and not cls._PARENT_LINKS:
                cls._PARENT_LINKS.append({
                    "id": str(uuid.uuid4()),
                    "parent_id": parent_id,
                    "student_id": "a56da972-0f19-418d-b0f7-de91ff114190",
                    "relationship": "guardian",
                    "verification_status": "verified",
                    "linked_at": datetime.now(timezone.utc).isoformat()
                })
            return [
                link["student_id"] for link in cls._PARENT_LINKS
                if link["parent_id"] == parent_id and link.get("verification_status") == "verified"
            ]

    @classmethod
    def link_parent_child(cls, parent_id: str, student_id: str, relationship: str = "guardian") -> Dict[str, Any]:
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
            # Seed default demo classroom if none exist
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
                # Seed enrollments
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

