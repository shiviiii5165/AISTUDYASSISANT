"""Token-bucket limits: 100 requests/min per IP and 30 AI queries/day per user.

Uses Redis (atomic Lua) when REDIS_URL is set. Without it, limits are per process, which
under-counts when several workers run, so production deployments should set REDIS_URL.
"""
from __future__ import annotations

import os
import threading
import time
from typing import Optional

from app.core.logging import logger

_LUA = """
local tokens = tonumber(redis.call('HGET', KEYS[1], 't') or ARGV[1])
local stamp = tonumber(redis.call('HGET', KEYS[1], 's') or ARGV[3])
tokens = math.min(tonumber(ARGV[1]), tokens + (tonumber(ARGV[3]) - stamp) * tonumber(ARGV[2]))
local allowed = 0
if tokens >= 1 then tokens = tokens - 1; allowed = 1 end
redis.call('HSET', KEYS[1], 't', tokens, 's', ARGV[3])
redis.call('EXPIRE', KEYS[1], ARGV[4])
return allowed
"""
_LOCK = threading.Lock()
_BUCKETS: dict[str, tuple[float, float]] = {}
_redis: Optional[object] = None
_redis_checked = False


def _client():
    global _redis, _redis_checked
    if not _redis_checked:
        _redis_checked = True
        url = os.environ.get("REDIS_URL")
        if url:
            try:
                import redis

                _redis = redis.Redis.from_url(url, socket_timeout=0.5)
                _redis.ping()
            except Exception as exc:
                logger.error(f"[RateLimit] Redis unavailable, using in-process buckets: {exc}")
                _redis = None
    return _redis


def allow(key: str, capacity: int, window_seconds: int, now: Optional[float] = None) -> bool:
    current = time.time() if now is None else now
    rate = capacity / window_seconds
    client = _client()
    if client is not None:
        try:
            return bool(client.eval(_LUA, 1, f"rl:{key}", capacity, rate, current, window_seconds))
        except Exception as exc:
            logger.error(f"[RateLimit] Redis call failed, using in-process bucket: {exc}")
    with _LOCK:
        tokens, stamp = _BUCKETS.get(key, (float(capacity), current))
        tokens = min(float(capacity), tokens + (current - stamp) * rate)
        allowed = tokens >= 1
        _BUCKETS[key] = (tokens - 1 if allowed else tokens, current)
        return allowed


def allow_ip(ip: str) -> bool:
    return allow(f"ip:{ip}", 100, 60)


def allow_ai_query(user_id: str) -> bool:
    return allow(f"ai:{user_id}", 30, 86400)


def clear() -> None:
    with _LOCK:
        _BUCKETS.clear()
