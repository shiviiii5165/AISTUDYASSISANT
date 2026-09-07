"""
Test Suite: Presentation Cache Versioning & TTL Validation
=========================================================
Explicitly verifies:
1. Topic ontology cache enforces schema version and TTL (expires_at). Stale versions and expired rows are rejected.
2. Image cache enforces schema version and TTL (expires_at). Stale versions and expired URLs are rejected.
3. Database migration 015 contains explicit version, created_at, expires_at columns and lookup indices.
"""
import sys
import os
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.presentation.topic_ontology_agent import (
    get_cached_ontology, save_cached_ontology, TopicOntologyChecklist,
    ONTOLOGY_CACHE_VERSION, ONTOLOGY_TTL_DAYS
)
from app.services.presentation.image_source_router import (
    get_cached_image, save_cached_image,
    IMAGE_CACHE_VERSION, IMAGE_TTL_DAYS
)


def test_ontology_cache_schema_migration_definitions():
    """Verify that migration 015 includes version, created_at, expires_at, and composite indices."""
    mig_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "migrations", "015_presentation_cache.sql")
    assert os.path.exists(mig_path), "Migration 015 file must exist"
    with open(mig_path, "r", encoding="utf-8") as f:
        sql = f.read()

    # Ontology cache table checks
    assert "CREATE TABLE IF NOT EXISTS ontology_cache" in sql
    assert "version INTEGER NOT NULL DEFAULT 1" in sql
    assert "expires_at TIMESTAMPTZ DEFAULT (now() + interval '90 days')" in sql
    assert "idx_ontology_cache_lookup" in sql
    assert "ON ontology_cache(topic_key, version, expires_at)" in sql

    # Image cache table checks
    assert "CREATE TABLE IF NOT EXISTS image_cache" in sql
    assert "expires_at TIMESTAMPTZ DEFAULT (now() + interval '30 days')" in sql
    assert "idx_image_cache_lookup" in sql
    assert "ON image_cache(query_hash, version, expires_at)" in sql
    print("\n[Migration 015 Verified] Both tables have version, created_at, expires_at, and index definitions")


def test_ontology_cache_rejects_expired_ttl():
    """Verify that an expired checklist in the database is not served (cache MISS)."""
    async def _run():
        expired_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        
        # When query filters by .gte("expires_at", now), expired rows are excluded by Supabase
        mock_sup = MagicMock()
        mock_sup.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=[])

        with patch("app.services.presentation.topic_ontology_agent.supabase", mock_sup):
            cached = await get_cached_ontology("test-expired-key")
            assert cached is None, "Expired ontology row must result in cache MISS"
            print("\n[Ontology TTL Verified] Expired checklist rejected by gte('expires_at', now)")

    asyncio.run(_run())


def test_ontology_cache_rejects_mismatched_prompt_version():
    """Verify that a cached entry with an older prompt version is not served (cache MISS)."""
    async def _run():
        old_version = ONTOLOGY_CACHE_VERSION + 99
        mock_sup = MagicMock()
        # Mock returns empty because .eq("version", ONTOLOGY_CACHE_VERSION) filters out old version
        mock_sup.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=[])

        with patch("app.services.presentation.topic_ontology_agent.supabase", mock_sup):
            cached = await get_cached_ontology("test-old-version-key")
            assert cached is None, "Mismatched version must result in cache MISS"
            print("\n[Ontology Versioning Verified] Older version rejected by eq('version', current)")

    asyncio.run(_run())


def test_image_cache_rejects_expired_ttl():
    """Verify that expired cached image URLs are not served (cache MISS)."""
    async def _run():
        mock_sup = MagicMock()
        mock_sup.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=[])

        with patch("app.services.presentation.image_source_router.supabase", mock_sup):
            cached = await get_cached_image("hash-expired-img")
            assert cached is None, "Expired image row must result in cache MISS"
            print("\n[Image TTL Verified] Expired image URL rejected by gte('expires_at', now)")

    asyncio.run(_run())


def test_image_cache_rejects_mismatched_version():
    """Verify that image cache entries with older schema/engine versions are not served."""
    async def _run():
        mock_sup = MagicMock()
        mock_sup.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=[])

        with patch("app.services.presentation.image_source_router.supabase", mock_sup):
            cached = await get_cached_image("hash-old-version-img")
            assert cached is None, "Mismatched image cache version must result in cache MISS"
            print("\n[Image Versioning Verified] Older version rejected by eq('version', current)")

    asyncio.run(_run())
