"""
LearnByGenie Notes Context Engine — Context Snapshot Manager
==========================================================
Creates, persists, and retrieves immutable snapshots of CanonicalNotesContext.
Guarantees historical explainability and reproducibility: subsequent changes
to student mastery or lesson state will never alter past snapshots.
"""
import copy
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from .schemas import CanonicalNotesContext, ContextSnapshot

logger = logging.getLogger("learnbygenie.notes.context_snapshot")


class ContextSnapshotManager:
    """Manages immutable snapshots of CanonicalNotesContext."""

    # In-memory store for high-speed retrieval, test isolation, and offline fallback
    _snapshots: Dict[str, ContextSnapshot] = {}

    @classmethod
    def create_snapshot(
        cls,
        context: CanonicalNotesContext,
        user_id: str = "anonymous"
    ) -> ContextSnapshot:
        """
        Creates an immutable deep-copy snapshot of CanonicalNotesContext.
        Guarantees that subsequent mutations of source state cannot affect this snapshot.
        """
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        snapshot_id = f"notes_ctx_{timestamp}_{uuid.uuid4().hex[:8]}"

        # Deep-copy context via Pydantic model serialization
        cloned_context = CanonicalNotesContext.model_validate(
            copy.deepcopy(context.model_dump(mode="python"))
        )

        snapshot = ContextSnapshot(
            snapshot_id=snapshot_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            context_version=context.context_schema_version,
            user_id=user_id,
            context=cloned_context
        )

        cls._snapshots[snapshot_id] = snapshot
        logger.info(f"[ContextSnapshot] Created immutable snapshot {snapshot_id} for user {user_id}")
        return snapshot

    @classmethod
    def get_snapshot(cls, snapshot_id: str) -> Optional[ContextSnapshot]:
        """Retrieves a historical snapshot by its snapshotId."""
        return cls._snapshots.get(snapshot_id)

    @classmethod
    def clear_all(cls) -> None:
        """Testing utility to clear in-memory snapshots."""
        cls._snapshots.clear()
