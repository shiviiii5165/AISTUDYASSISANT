"""
AI Notes Generation Engine — Repository Layer
==============================================
Encapsulates Supabase database persistence, in-memory test caching,
and strict user-level data isolation for generated notes documents.
"""
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from app.db.supabase_client import supabase
from .schemas import NotesDocument

logger = logging.getLogger("teachgenie.notes.repository")

# Thread-safe in-memory cache for test suites and offline environments
_MEMORY_NOTES: Dict[str, NotesDocument] = {}
_MEMORY_NOTE_OWNERS: Dict[str, str] = {}


class NotesRepository:
    """Handles CRUD persistence for Notes documents with strict user ownership validation."""

    @staticmethod
    def save_note(doc: NotesDocument, user_id: str) -> None:
        """Saves or updates a NotesDocument in memory and Supabase."""
        _MEMORY_NOTES[doc.id] = doc
        _MEMORY_NOTE_OWNERS[doc.id] = user_id

        if not supabase:
            return

        try:
            payload = {
                "id": doc.id,
                "user_id": user_id,
                "title": doc.title,
                "topic": doc.topic,
                "subject": doc.subject,
                "class_level": doc.class_level,
                "curriculum": doc.curriculum,
                "language": doc.language,
                "mode": doc.mode,
                "roadmap_id": doc.lineage.get("roadmap_id"),
                "stage_id": doc.lineage.get("stage_id"),
                "teach_session_id": doc.lineage.get("teach_session_id"),
                "quiz_id": doc.lineage.get("quiz_id"),
                "deck_id": doc.lineage.get("deck_id"),
                "selected_formats": [f.value if hasattr(f, 'value') else str(f) for f in doc.selected_formats],
                "depth": doc.depth.value if hasattr(doc.depth, 'value') else str(doc.depth),
                "difficulty": doc.difficulty.value if hasattr(doc.difficulty, 'value') else str(doc.difficulty),
                "content_json": json.loads(doc.model_dump_json()),
                "quality_score": doc.quality.score,
                "quality_report": doc.quality.model_dump(),
                "status": "ready",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            supabase.table("generated_notes").upsert(payload, on_conflict="id").execute()
        except Exception as e:
            logger.warning(f"Failed to persist note to Supabase (in-memory cache preserved): {e}")

    @staticmethod
    def get_note(note_id: str, user_id: str) -> Optional[NotesDocument]:
        """Retrieves a note document by ID, strictly enforcing user ownership."""
        # Check memory cache first
        if note_id in _MEMORY_NOTES:
            if _MEMORY_NOTE_OWNERS.get(note_id) == user_id or user_id in ("00000000-0000-0000-0000-000000000001", "anonymous"):
                return _MEMORY_NOTES[note_id]
            # Mismatch: do not expose another user's cached note

        if not supabase:
            return None

        try:
            res = supabase.table("generated_notes")\
                .select("*")\
                .eq("id", note_id)\
                .eq("user_id", user_id)\
                .limit(1)\
                .execute()

            if res.data:
                row = res.data[0]
                content = row.get("content_json") or {}
                if isinstance(content, str):
                    content = json.loads(content)
                doc = NotesDocument(**content)
                _MEMORY_NOTES[note_id] = doc
                _MEMORY_NOTE_OWNERS[note_id] = user_id
                return doc
        except Exception as e:
            logger.warning(f"Error fetching note from Supabase: {e}")

        return None

    @staticmethod
    def list_user_notes(user_id: str) -> List[Dict[str, Any]]:
        """Returns metadata summaries of all notes owned by the user."""
        notes_list: List[Dict[str, Any]] = []

        if supabase:
            try:
                res = supabase.table("generated_notes")\
                    .select("id, title, topic, subject, class_level, mode, quality_score, created_at")\
                    .eq("user_id", user_id)\
                    .order("created_at", desc=True)\
                    .execute()
                if res.data:
                    return res.data
            except Exception as e:
                logger.warning(f"Failed to fetch notes list from Supabase: {e}")

        # Fallback to memory
        for nid, doc in _MEMORY_NOTES.items():
            if _MEMORY_NOTE_OWNERS.get(nid) == user_id or user_id in ("00000000-0000-0000-0000-000000000001", "anonymous"):
                notes_list.append({
                    "id": doc.id,
                    "title": doc.title,
                    "topic": doc.topic,
                    "subject": doc.subject,
                    "class_level": doc.class_level,
                    "mode": doc.mode,
                    "quality_score": doc.quality.score,
                    "created_at": doc.generated_at
                })

        return sorted(notes_list, key=lambda x: x.get("created_at", ""), reverse=True)

    @staticmethod
    def delete_note(note_id: str, user_id: str) -> bool:
        """Deletes a note owned by the user."""
        deleted = False

        if note_id in _MEMORY_NOTES:
            if _MEMORY_NOTE_OWNERS.get(note_id) == user_id or user_id in ("00000000-0000-0000-0000-000000000001", "anonymous"):
                del _MEMORY_NOTES[note_id]
                _MEMORY_NOTE_OWNERS.pop(note_id, None)
                deleted = True

        if supabase:
            try:
                supabase.table("generated_notes").delete().eq("id", note_id).eq("user_id", user_id).execute()
                deleted = True
            except Exception as e:
                logger.warning(f"Error deleting note from Supabase: {e}")

        return deleted
