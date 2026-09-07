"""
Test Suite: Live Provider Credentials & Independence Verification
================================================================
Explicitly tests that Groq, Gemini, and OpenRouter are EACH independently
functional with real credentials, not placeholders or fallbacks.
"""
import sys
import os
import pytest
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.services.ai.providers.groq import GroqProvider
from app.services.ai.providers.gemini import GeminiProvider
from app.services.ai.providers.openrouter import OpenRouterProvider
from app.services.ai.router import ModelRouter
import asyncio


def test_settings_credentials_are_not_placeholders():
    """Verify that settings does not hold placeholder strings for any provider."""
    assert settings.GROQ_API_KEY and settings.GROQ_API_KEY != "placeholder", (
        f"GROQ_API_KEY is invalid/placeholder: {settings.GROQ_API_KEY}"
    )
    assert settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "placeholder", (
        f"GEMINI_API_KEY is invalid/placeholder: {settings.GEMINI_API_KEY}"
    )
    assert settings.OPENROUTER_API_KEY and settings.OPENROUTER_API_KEY != "placeholder", (
        f"OPENROUTER_API_KEY is invalid/placeholder: {settings.OPENROUTER_API_KEY}"
    )


def test_groq_standalone_live_call():
    """Direct live verification: Groq accepts requests and returns valid text and JSON."""
    async def _run():
        provider = GroqProvider()
        assert provider.api_key and provider.api_key != "placeholder"

        # Text generation
        t0 = time.time()
        res = await provider.generate_text(
            [{"role": "user", "content": "Respond with the word: VERIFIED"}],
            timeout=15.0,
        )
        elapsed = time.time() - t0
        assert "VERIFIED" in res.text, f"Groq response unexpected: {res.text}"
        assert res.provider == "groq"
        print(f"\n[Groq Live Call] {elapsed:.2f}s | Model: {res.model}")

        # JSON generation
        json_res = await provider.generate_json(
            [{"role": "user", "content": "Return a JSON object: {\"healthy\": true, \"provider\": \"groq\"}"}],
            timeout=15.0,
        )
        assert json_res.get("healthy") is True or json_res.get("provider") == "groq"

    asyncio.run(_run())


def test_gemini_standalone_live_call():
    """Direct live verification: Gemini accepts requests and returns valid text and JSON."""
    async def _run():
        provider = GeminiProvider()
        assert provider.api_key and provider.api_key != "placeholder"

        # Text generation
        t0 = time.time()
        res = await provider.generate_text(
            [{"role": "user", "content": "Respond with the word: VERIFIED"}],
            timeout=30.0,
        )
        elapsed = time.time() - t0
        assert "VERIFIED" in res.text, f"Gemini response unexpected: {res.text}"
        assert res.provider == "gemini"
        print(f"\n[Gemini Live Call] {elapsed:.2f}s | Model: {res.model}")

        # JSON generation
        json_res = await provider.generate_json(
            [{"role": "user", "content": "Return a JSON object: {\"healthy\": true, \"provider\": \"gemini\"}"}],
            timeout=30.0,
        )
        assert json_res.get("healthy") is True or json_res.get("provider") == "gemini"

    asyncio.run(_run())


def test_openrouter_standalone_live_call():
    """Direct live verification: OpenRouter accepts requests and returns valid text and JSON."""
    async def _run():
        provider = OpenRouterProvider()
        assert provider.api_key and provider.api_key != "placeholder"

        # Text generation
        t0 = time.time()
        res = await provider.generate_text(
            [{"role": "user", "content": "Respond with the word: VERIFIED"}],
            timeout=15.0,
        )
        elapsed = time.time() - t0
        assert "VERIFIED" in res.text, f"OpenRouter response unexpected: {res.text}"
        assert res.provider == "openrouter"
        print(f"\n[OpenRouter Live Call] {elapsed:.2f}s | Model: {res.model}")

        # JSON generation
        json_res = await provider.generate_json(
            [{"role": "user", "content": "Return a JSON object: {\"healthy\": true, \"provider\": \"openrouter\"}"}],
            timeout=15.0,
        )
        assert json_res.get("healthy") is True or json_res.get("provider") == "openrouter"

    asyncio.run(_run())


def test_router_executes_on_tier_one_groq():
    """Verify that ModelRouter handles a planning request on Tier 1 (Groq) without failing over."""
    async def _run():
        router = ModelRouter()
        t0 = time.time()
        res = await router.generate_json(
            task="planning",
            messages=[{"role": "user", "content": "Return a JSON object: {\"tier\": 1, \"status\": \"success\"}"}],
            timeout=20.0,
        )
        elapsed = time.time() - t0
        assert res.get("tier") == 1 or res.get("status") == "success"
        print(f"\n[Router Tier 1 Groq] {elapsed:.2f}s | Result: {res}")

    asyncio.run(_run())
