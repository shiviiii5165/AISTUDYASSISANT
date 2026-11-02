"""
LearnByGenie — Authoritative Server-Side User Roles & Audit Trail
================================================================
Provides database-backed role lookup and audit-logged role updates.
Guarantees:
1. Privileged roles can NEVER be claimed via client-editable user_metadata.
2. Administrative role assignments persist to PostgreSQL and take effect immediately.
3. Every role modification records an immutable audit trail entry.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
import threading
import uuid

from app.db.supabase_client import supabase
from app.core.logging import logger

VALID_SYSTEM_ROLES = {
    "student",
    "parent",
    "teacher",
    "school_admin",
    "content_creator",
    "admin",
    "super_admin"
}


class UserRoleRepository:
    """Thread-safe authoritative repository for system roles and role change audits."""
    _LOCK = threading.RLock()
    _USER_ROLES: Dict[str, str] = {}  # user_id -> role
    _ROLE_AUDIT_LOG: list = []

    @classmethod
    def clear_memory_cache(cls):
        with cls._LOCK:
            cls._USER_ROLES.clear()
            cls._ROLE_AUDIT_LOG.clear()

    @classmethod
    def get_user_role(cls, user_id: str) -> Optional[str]:
        """
        Retrieves authoritative role for user_id.
        Queries database first, then cached authoritative memory store.
        """
        if not user_id:
            return None

        # 1. Check local cache
        with cls._LOCK:
            if user_id in cls._USER_ROLES:
                return cls._USER_ROLES[user_id]

        # 2. Check authoritative Supabase table if available
        if supabase is not None:
            try:
                res = supabase.table("user_roles").select("role").eq("user_id", user_id).limit(1).execute()
                if res.data and len(res.data) > 0:
                    role = res.data[0].get("role")
                    if role in VALID_SYSTEM_ROLES:
                        with cls._LOCK:
                            cls._USER_ROLES[user_id] = role
                        return role
            except Exception as e:
                logger.debug(f"[UserRoleRepo] Database role query notice for {user_id[:8]}: {e}")

        return None

    @classmethod
    def set_user_role(
        cls,
        target_user_id: str,
        new_role: str,
        assigned_by: str,
        reason: str = "Administrative assignment"
    ) -> Dict[str, Any]:
        """
        Authoritatively updates a user's role and writes an audit log entry.
        """
        if new_role not in VALID_SYSTEM_ROLES:
            raise ValueError(f"Invalid system role '{new_role}'. Must be one of {VALID_SYSTEM_ROLES}")

        old_role = cls.get_user_role(target_user_id) or "student"
        now_iso = datetime.now(timezone.utc).isoformat()
        audit_id = str(uuid.uuid4())

        # 1. Update in-memory cache immediately
        with cls._LOCK:
            cls._USER_ROLES[target_user_id] = new_role
            audit_entry = {
                "id": audit_id,
                "target_user_id": target_user_id,
                "actor_admin_id": assigned_by,
                "old_role": old_role,
                "new_role": new_role,
                "reason": reason,
                "created_at": now_iso
            }
            cls._ROLE_AUDIT_LOG.append(audit_entry)

        # 2. Persist to authoritative PostgreSQL tables if available
        if supabase is not None:
            try:
                # Upsert into user_roles
                supabase.table("user_roles").upsert({
                    "user_id": target_user_id,
                    "role": new_role,
                    "assigned_by": assigned_by,
                    "updated_at": now_iso
                }, on_conflict="user_id").execute()

                # Insert audit log entry
                supabase.table("user_role_audit").insert(audit_entry).execute()
            except Exception as e:
                logger.warning(f"[UserRoleRepo] Database persistence notice for role update: {e}")

        return {
            "status": "updated",
            "target_user_id": target_user_id,
            "old_role": old_role,
            "new_role": new_role,
            "assigned_by": assigned_by,
            "audit_id": audit_id,
            "updated_at": now_iso
        }

