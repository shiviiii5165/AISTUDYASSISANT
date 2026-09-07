"""
Live Quiz Engine — Server-Authoritative Realtime Broadcaster
============================================================
Dispatches sanitized broadcast messages to Supabase Realtime channels.
Students subscribe to broadcast messages; no raw table replication with
answer keys is ever exposed to student browser clients.
"""
from __future__ import annotations
import httpx
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logging import logger


async def broadcast_session_event(
    session_id: str,
    event_name: str,
    payload: Dict[str, Any],
) -> bool:
    """
    Emits a sanitized realtime event to the channel 'session:<session_id>'.
    Uses the Supabase Realtime REST Broadcast endpoint with the service-role key.
    """
    supabase_url = getattr(settings, "SUPABASE_URL", "")
    supabase_key = getattr(settings, "SUPABASE_KEY", "")

    if not supabase_url or not supabase_key:
        logger.info(f"[RealtimeMock] broadcast to session:{session_id} event={event_name}: {payload}")
        return True

    url = f"{supabase_url.rstrip('/')}/realtime/v1/api/broadcast"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
    }
    body = {
        "messages": [
            {
                "topic": f"session:{session_id}",
                "event": event_name,
                "payload": payload,
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            if resp.status_code >= 400:
                logger.warning(
                    f"[RealtimeBroadcast] Supabase broadcast returned {resp.status_code}: {resp.text}"
                )
                return False
            return True
    except Exception as e:
        logger.warning(f"[RealtimeBroadcast] Non-blocking broadcast error: {e}")
        return False
