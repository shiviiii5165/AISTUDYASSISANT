"""
TeachGenie Canary Infrastructure — Structured Authorization & Consent Engine
============================================================================
Safeguard #2:
- Replaces loose boolean consent states with structured authorization records.
- Records authorization scope, timestamp, source/actor category, status, and revocation state.
- Enforces data minimization: only captures necessary pedagogical telemetry.
"""

import uuid
from enum import Enum
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class AuthorizationScope(str, Enum):
    CANARY_TELEMETRY = "canary_telemetry"
    ADAPTIVE_LEARNING = "adaptive_learning"
    OUTCOME_ANALYTICS = "outcome_analytics"
    DELAYED_RETENTION = "delayed_retention"
    ANONYMIZED_RESEARCH = "anonymized_research"


class ActorCategory(str, Enum):
    INDEPENDENT_TEACHER = "independent_teacher"
    INSTITUTIONAL_FACULTY = "institutional_faculty"
    STUDENT = "student"
    PARENT_GUARDIAN = "parent_guardian"
    RESEARCH_PARTNER = "research_partner"


class AuthorizationStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class StructuredAuthorizationRecord(BaseModel):
    """
    Structured authorization contract strictly replacing legacy boolean consent flags.
    """
    authorization_id: str = Field(default_factory=lambda: f"auth_{uuid.uuid4().hex[:12]}")
    pseudonym_id: str
    entity_role: str = "student"  # "teacher" or "student"
    actor_category: ActorCategory = ActorCategory.STUDENT
    scopes: List[AuthorizationScope] = Field(default_factory=lambda: [
        AuthorizationScope.CANARY_TELEMETRY,
        AuthorizationScope.ADAPTIVE_LEARNING
    ])
    granted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    status: AuthorizationStatus = AuthorizationStatus.ACTIVE
    
    # Revocation state
    is_revoked: bool = False
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None
    revocation_actor: Optional[str] = None

    # Data minimization specification
    data_minimization_policy: str = "TELEMETRY_ONLY_NO_PII"
    retained_fields: List[str] = Field(default_factory=lambda: [
        "pseudonym_id", "canonical_concept_id", "pre_state", "post_state",
        "misconception_tag", "time_spent_seconds", "score_gain"
    ])


class AuthorizationRegistry:
    """
    Authoritative state tracker for participant authorization records.
    """
    _records: Dict[str, StructuredAuthorizationRecord] = {}

    @classmethod
    def grant_authorization(
        cls,
        pseudonym_id: str,
        entity_role: str = "student",
        actor_category: ActorCategory = ActorCategory.STUDENT,
        scopes: Optional[List[AuthorizationScope]] = None
    ) -> StructuredAuthorizationRecord:
        """Issues and records a new structured authorization record."""
        record = StructuredAuthorizationRecord(
            pseudonym_id=pseudonym_id,
            entity_role=entity_role,
            actor_category=actor_category,
            scopes=scopes or [
                AuthorizationScope.CANARY_TELEMETRY,
                AuthorizationScope.ADAPTIVE_LEARNING,
                AuthorizationScope.OUTCOME_ANALYTICS,
                AuthorizationScope.DELAYED_RETENTION
            ]
        )
        cls._records[pseudonym_id] = record
        return record

    @classmethod
    def revoke_authorization(
        cls,
        pseudonym_id: str,
        reason: str = "Participant requested revocation",
        actor: str = "self"
    ) -> bool:
        """Revokes an existing authorization record and terminates telemetry collection."""
        if pseudonym_id in cls._records:
            rec = cls._records[pseudonym_id]
            rec.is_revoked = True
            rec.status = AuthorizationStatus.REVOKED
            rec.revoked_at = datetime.now(timezone.utc)
            rec.revocation_reason = reason
            rec.revocation_actor = actor
            return True
        return False

    @classmethod
    def is_authorized(
        cls,
        pseudonym_id: str,
        scope: AuthorizationScope = AuthorizationScope.CANARY_TELEMETRY
    ) -> bool:
        """
        Validates whether a participant has an active, non-revoked authorization
        for the requested scope.
        """
        rec = cls._records.get(pseudonym_id)
        if not rec:
            return False
        if rec.is_revoked or rec.status != AuthorizationStatus.ACTIVE:
            return False
        if rec.expires_at and datetime.now(timezone.utc) > rec.expires_at:
            rec.status = AuthorizationStatus.EXPIRED
            return False
        return scope in rec.scopes

    @classmethod
    def get_record(cls, pseudonym_id: str) -> Optional[StructuredAuthorizationRecord]:
        """Retrieves authorization record for a pseudonym."""
        return cls._records.get(pseudonym_id)

    @classmethod
    def clear_all(cls) -> None:
        """Testing utility."""
        cls._records.clear()

