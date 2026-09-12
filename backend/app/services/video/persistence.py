"""
Durable Persistence Layer for TeachGenie Video Teacher
======================================================
Provides atomic file-backed local persistence across server restarts
combined with background Supabase table syncing when available.
"""
import os
import json
import tempfile
import asyncio
from typing import Any, Dict, List, Optional
from app.core.logging import logger

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "persistence"))
os.makedirs(DATA_DIR, exist_ok=True)


def load_file_json(filename: str, default: Any = None) -> Any:
    """Reads JSON data from local persistence directory safely."""
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"[Persistence] Failed to load {filename}: {e}")
        return default


def save_file_json(filename: str, data: Any) -> None:
    """Writes JSON data atomically using a temp file and rename."""
    try:
        filepath = os.path.join(DATA_DIR, filename)
        tmp_fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, prefix=f"{filename}.tmp_")
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        if os.path.exists(filepath):
            os.replace(tmp_path, filepath)
        else:
            os.rename(tmp_path, filepath)
    except Exception as e:
        logger.error(f"[Persistence] Failed to save {filename}: {e}")
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def _fire_background_task(coro):
    """Schedules coroutine on running loop if available, else closes it cleanly."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        coro.close()


def sync_mastery_to_supabase_background(user_id: str, lesson_id: str, profile_dict: Dict[str, Any], last_active: float):
    """Schedules non-blocking async Supabase upsert for learner mastery."""
    _fire_background_task(_async_sync_mastery_supabase(user_id, lesson_id, profile_dict, last_active))


async def _async_sync_mastery_supabase(user_id: str, lesson_id: str, profile_dict: Dict[str, Any], last_active: float):
    try:
        from app.db.supabase_client import supabase
        if supabase:
            row = {
                "user_id": user_id,
                "lesson_id": lesson_id,
                "profile_data": profile_dict,
                "last_active_timestamp": last_active,
            }
            supabase.table("learner_mastery").upsert(row, on_conflict="user_id,lesson_id").execute()
    except Exception as e:
        logger.debug(f"[Persistence] Supabase learner_mastery notice: {e}")


def sync_pilot_to_supabase_background(session_dict: Dict[str, Any]):
    """Schedules non-blocking async Supabase upsert for pilot sessions."""
    _fire_background_task(_async_sync_pilot_supabase(session_dict))


async def _async_sync_pilot_supabase(session_dict: Dict[str, Any]):
    try:
        from app.db.supabase_client import supabase
        if supabase:
            row = {
                "session_id": session_dict.get("session_id"),
                "participant_id": session_dict.get("participant_id"),
                "topic": session_dict.get("topic"),
                "provenance": session_dict.get("provenance", "REAL_LEARNER_EVALUATION"),
                "pre_score": session_dict.get("pre_score"),
                "post_score": session_dict.get("post_score"),
                "delayed_score": session_dict.get("delayed_score"),
                "learning_gain": session_dict.get("learning_gain"),
                "normalized_gain": session_dict.get("normalized_gain"),
                "session_data": session_dict,
            }
            supabase.table("pilot_sessions").upsert(row, on_conflict="session_id").execute()
    except Exception as e:
        logger.debug(f"[Persistence] Supabase pilot_sessions notice: {e}")


def sync_doubt_to_supabase_background(session_dict: Dict[str, Any]):
    """Schedules non-blocking async Supabase upsert for doubt sessions."""
    _fire_background_task(_async_sync_doubt_supabase(session_dict))


async def _async_sync_doubt_supabase(session_dict: Dict[str, Any]):
    try:
        from app.db.supabase_client import supabase
        if supabase:
            row = {
                "doubt_session_id": session_dict.get("doubt_session_id"),
                "lesson_id": session_dict.get("lesson_id"),
                "current_focus_concept": session_dict.get("current_focus_concept"),
                "unresolved_confusion": session_dict.get("unresolved_confusion"),
                "session_data": session_dict,
            }
            supabase.table("doubt_sessions").upsert(row, on_conflict="doubt_session_id").execute()
    except Exception as e:
        logger.debug(f"[Persistence] Supabase doubt_sessions notice: {e}")
