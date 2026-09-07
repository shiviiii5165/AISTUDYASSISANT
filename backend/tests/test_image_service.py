"""
Test: Image Service — Cache, Provider Health, Fallback Routing
================================================================
Validates:
  - In-memory LRU cache with TTL
  - Multi-credential health tracking
  - Provider health-based ordering
  - Fallback routing (provider failure → next provider)
  - Unsplash download tracking compliance
  - QueryGenerator slide-to-query mapping
  - ImageRanker candidate scoring
"""
import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

# ── Cache Tests ──────────────────────────────────────────────────────────

class TestImageCache:
    """Test the two-tier image cache (in-memory LRU + Supabase)."""

    def _make_cache(self):
        from app.services.image_service.cache import ImageCache
        return ImageCache(supabase_client=None)  # no Supabase in tests

    def _make_result(self, query="test", provider="pexels"):
        from app.services.image_service.models import ImageResult, Attribution
        return ImageResult(
            image_bytes=b"fake-image-bytes-" + query.encode(),
            provider=provider,
            url=f"https://example.com/{query}.jpg",
            query=query,
            attribution=Attribution(provider=provider),
        )

    @pytest.mark.anyio
    async def test_cache_miss_returns_none(self):
        cache = self._make_cache()
        result = await cache.get("nonexistent query")
        assert result is None

    @pytest.mark.anyio
    async def test_cache_put_and_get_roundtrip(self):
        cache = self._make_cache()
        original = self._make_result("machine learning")
        await cache.put("machine learning", original)

        cached = await cache.get("machine learning")
        assert cached is not None
        assert cached.image_bytes == original.image_bytes
        assert cached.provider == "pexels"
        assert cached.query == "machine learning"

    @pytest.mark.anyio
    async def test_cache_stats(self):
        cache = self._make_cache()
        await cache.put("query1", self._make_result("query1"))
        await cache.put("query2", self._make_result("query2"))

        stats = cache.get_stats()
        assert stats["memory_entries"] == 2
        assert stats["memory_valid"] == 2

    @pytest.mark.anyio
    async def test_cache_normalized_query_hash(self):
        """Queries that differ only by case/punctuation should share a cache entry."""
        cache = self._make_cache()
        result = self._make_result("test")
        await cache.put("Machine Learning!", result)

        # Same query with different casing / punctuation
        cached = await cache.get("machine learning")
        assert cached is not None

    @pytest.mark.anyio
    async def test_cache_lru_eviction(self):
        """Cache should evict oldest entries when over capacity."""
        from app.services.image_service.cache import ImageCache, MAX_MEMORY_ENTRIES
        cache = ImageCache(supabase_client=None)

        # Fill cache beyond capacity
        for i in range(MAX_MEMORY_ENTRIES + 10):
            await cache.put(f"query_{i}", self._make_result(f"query_{i}"))

        stats = cache.get_stats()
        assert stats["memory_entries"] <= MAX_MEMORY_ENTRIES


# ── Credential Health Tests ──────────────────────────────────────────────

class TestCredentialHealth:
    """Test per-credential health tracking."""

    def test_new_credential_is_available(self):
        from app.services.image_service.models import CredentialHealth
        cred = CredentialHealth(key="test-key", provider="pexels")
        assert cred.is_available is True
        assert cred.success_rate == 1.0  # optimistic default

    def test_success_updates_stats(self):
        from app.services.image_service.models import CredentialHealth
        cred = CredentialHealth(key="test-key", provider="pexels")
        cred.record_success()
        assert cred.total_requests == 1
        assert cred.total_successes == 1
        assert cred.consecutive_failures == 0

    def test_failure_updates_stats(self):
        from app.services.image_service.models import CredentialHealth
        cred = CredentialHealth(key="test-key", provider="pexels")
        cred.record_failure()
        assert cred.total_requests == 1
        assert cred.failure_count == 1
        assert cred.consecutive_failures == 1

    def test_cooldown_makes_unavailable(self):
        from app.services.image_service.models import CredentialHealth
        cred = CredentialHealth(key="test-key", provider="pexels")
        cred.set_cooldown(300)  # 5 minutes
        assert cred.is_available is False


# ── Provider Health Tests ────────────────────────────────────────────────

class TestProviderHealth:
    """Test provider-level health scoring."""

    def test_health_score_with_no_credentials(self):
        from app.services.image_service.models import ProviderHealth
        health = ProviderHealth(name="pexels")
        assert health.health_score == 0.0

    def test_health_score_with_healthy_credentials(self):
        from app.services.image_service.models import ProviderHealth, CredentialHealth
        creds = [
            CredentialHealth(key="k1", provider="pexels"),
            CredentialHealth(key="k2", provider="pexels"),
        ]
        health = ProviderHealth(
            name="pexels",
            credentials=creds,
            total_requests=10,
            total_successes=10,
        )
        score = health.health_score
        assert score > 0


# ── Provider Manager Tests ──────────────────────────────────────────────

class TestProviderManager:
    """Test health-based provider ordering."""

    def test_no_keys_returns_empty(self):
        from app.services.image_service.provider_manager import ProviderManager
        pm = ProviderManager(pexels_keys=[], pixabay_keys=[], unsplash_keys=[])
        assert len(pm.configured_adapters) == 0
        assert pm.get_ordered_providers() == []

    def test_configured_providers_returned(self):
        from app.services.image_service.provider_manager import ProviderManager
        pm = ProviderManager(
            pexels_keys=["key1"],
            pixabay_keys=["key2"],
            unsplash_keys=[],
        )
        configured = pm.configured_adapters
        assert len(configured) == 2
        names = {a.PROVIDER_NAME for a in configured}
        assert "pexels" in names
        assert "pixabay" in names

    def test_health_report_structure(self):
        from app.services.image_service.provider_manager import ProviderManager
        pm = ProviderManager(
            pexels_keys=["k1", "k2"],
            pixabay_keys=["k3"],
            unsplash_keys=[],
        )
        report = pm.get_health_report()
        assert "pexels" in report
        assert report["pexels"]["total_credentials"] == 2
        assert report["pixabay"]["total_credentials"] == 1
        assert report["unsplash"]["configured"] is False


# ── Query Generator Tests ───────────────────────────────────────────────

class TestQueryGenerator:
    """Test slide-to-query mapping."""

    def test_uses_image_query_when_present(self):
        from app.services.image_service.query_generator import QueryGenerator
        slide = {"image_query": "neural network brain visualization", "title": "AI Overview"}
        query = QueryGenerator.generate_query(slide)
        assert "neural" in query
        assert "network" in query

    def test_falls_back_to_key_message(self):
        from app.services.image_service.query_generator import QueryGenerator
        slide = {"key_message": "Waterfall model in software development lifecycle", "title": "SDLC"}
        query = QueryGenerator.generate_query(slide)
        assert "waterfall" in query or "software" in query or "development" in query

    def test_strips_non_photographic_terms_from_key_message(self):
        """When using key_message path (no image_query), non-photographic terms are stripped."""
        from app.services.image_service.query_generator import QueryGenerator
        slide = {
            "key_message": "Algorithm overview and introduction to methodology framework",
            "title": "Algorithms",
        }
        query = QueryGenerator.generate_query(slide)
        # key_message goes through _extract_photographic_terms which strips these
        assert "algorithm" not in query or "overview" not in query

    def test_falls_back_to_topic(self):
        from app.services.image_service.query_generator import QueryGenerator
        slide = {"title": "X", "body_bullets": []}
        query = QueryGenerator.generate_query(slide, topic="Machine Learning Fundamentals")
        assert len(query) > 3


# ── Image Ranker Tests ──────────────────────────────────────────────────

class TestImageRanker:
    """Test candidate image ranking."""

    def _make_candidate(self, desc="", w=1920, h=1080, provider="pexels"):
        from app.services.image_service.models import CandidateImage, Attribution
        return CandidateImage(
            url=f"https://example.com/{desc}.jpg",
            width=w,
            height=h,
            description=desc,
            provider=provider,
            attribution=Attribution(provider=provider),
        )

    def test_returns_none_for_empty_candidates(self):
        from app.services.image_service.ranker import ImageRanker
        result = ImageRanker.rank([], "test query")
        assert result is None

    def test_ranks_relevant_image_higher(self):
        from app.services.image_service.ranker import ImageRanker
        relevant = self._make_candidate("machine learning neural network brain", 1920, 1080)
        irrelevant = self._make_candidate("sunset beach vacation tropical", 1920, 1080)
        best = ImageRanker.rank([irrelevant, relevant], "machine learning neural network")
        assert best is not None
        assert "machine" in best.description or "neural" in best.description

    def test_prefers_landscape_for_landscape_target(self):
        from app.services.image_service.ranker import ImageRanker
        landscape = self._make_candidate("test photo", 1920, 1080)  # 16:9
        portrait = self._make_candidate("test photo", 1080, 1920)   # 9:16
        best = ImageRanker.rank([portrait, landscape], "test photo", "landscape")
        assert best is not None
        assert best.width > best.height

    def test_prefers_higher_resolution(self):
        from app.services.image_service.ranker import ImageRanker
        high_res = self._make_candidate("test photo landscape", 2400, 1600)
        low_res = self._make_candidate("test photo landscape", 400, 300)
        best = ImageRanker.rank([low_res, high_res], "test photo landscape", "landscape")
        assert best is not None
        assert best.width >= 1200


# ── Fallback Routing Tests ──────────────────────────────────────────────

class TestFallbackRouting:
    """Test that provider failures cause graceful fallthrough."""

    @pytest.mark.anyio
    async def test_falls_through_on_provider_failure(self):
        """When pexels fails, should try pixabay, then unsplash."""
        from app.services.image_service.cache import ImageCache
        from app.services.image_service.fallback_manager import FallbackManager
        from app.services.image_service.provider_manager import ProviderManager

        cache = ImageCache(supabase_client=None)
        pm = ProviderManager(
            pexels_keys=["fake-pexels-key"],
            pixabay_keys=["fake-pixabay-key"],
            unsplash_keys=[],
        )

        # Mock both adapters to fail
        pm.pexels.search = AsyncMock(return_value=[])
        pm.pixabay.search = AsyncMock(return_value=[])

        fm = FallbackManager(cache, pm)

        # Mock wikimedia to also return None
        fm._try_wikimedia = AsyncMock(return_value=None)

        result = await fm.resolve("test query")
        assert result is None
        # Both providers were tried
        pm.pexels.search.assert_called_once()
        pm.pixabay.search.assert_called_once()

    @pytest.mark.anyio
    async def test_cache_hit_skips_providers(self):
        """When cache has a result, no providers should be called."""
        from app.services.image_service.cache import ImageCache
        from app.services.image_service.fallback_manager import FallbackManager
        from app.services.image_service.provider_manager import ProviderManager
        from app.services.image_service.models import ImageResult, Attribution

        cache = ImageCache(supabase_client=None)
        pm = ProviderManager(
            pexels_keys=["fake-key"],
            pixabay_keys=[],
            unsplash_keys=[],
        )

        # Pre-populate cache
        cached_result = ImageResult(
            image_bytes=b"cached-bytes",
            provider="pexels",
            url="https://example.com/cached.jpg",
            query="test query",
            attribution=Attribution(provider="pexels"),
        )
        await cache.put("test query", cached_result)

        pm.pexels.search = AsyncMock(return_value=[])
        fm = FallbackManager(cache, pm)

        result = await fm.resolve("test query")
        assert result is not None
        assert result.image_bytes == b"cached-bytes"
        # Provider should NOT have been called
        pm.pexels.search.assert_not_called()
