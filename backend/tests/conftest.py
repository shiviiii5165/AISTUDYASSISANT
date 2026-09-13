"""
Shared Test Configuration
=========================
Provides rate-limit-aware fixtures and circuit-breaker reset logic
for presentation pipeline test suites that make real LLM API calls.
Protects live API keys from being overwritten with placeholders by mock/isolated test modules.
"""
import os
import sys
import time
import pytest
from dotenv import load_dotenv

# Ensure .env is loaded into os.environ before any test module can poison it with placeholders
_tests_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_tests_dir)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
_root_dir = os.path.dirname(_backend_dir)
_env_path = os.path.join(_root_dir, ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path, override=True)

# Preserve the real API keys loaded from .env
_PROTECTED_KEY_NAMES = [
    "GEMINI_API_KEY",
    "GEMINI_IMAGE_API_KEY",
    "GEMINI_API_KEYS",
    "GROQ_API_KEY",
    "GROQ_API_KEYS",
    "OPENROUTER_API_KEY",
    "OPENROUTER_API_KEYS",
    "CEREBRAS_API_KEY",
    "CEREBRAS_API_KEYS",
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "SUPABASE_JWT_SECRET",
    "CANARY_VAULT_MASTER_KEY",
    "CANARY_SERVICE_AUTH_SECRET",
    "CANARY_PSEUDONYMIZATION_SALT",
]
os.environ.setdefault("CANARY_VAULT_MASTER_KEY", "teachgenie_test_vault_master_key_2026_aes_gcm_pytest")
_REAL_ENV_KEYS = {k: os.environ[k] for k in _PROTECTED_KEY_NAMES if k in os.environ and os.environ[k] != "placeholder"}


def _restore_env_and_settings():
    """Ensure os.environ and app.core.config.settings hold real API keys, not placeholders."""
    for k, v in _REAL_ENV_KEYS.items():
        os.environ[k] = v
    try:
        from app.core.config import settings
        for k, v in _REAL_ENV_KEYS.items():
            if hasattr(settings, k) and getattr(settings, k) in ("", "placeholder"):
                setattr(settings, k, v)
    except Exception:
        pass


def _reset_breakers():
    """Helper to reset all circuit breakers to healthy state."""
    try:
        from app.services.ai.circuit_breaker import health_manager, ProviderState
        for provider_name in list(health_manager.breakers.keys()):
            breaker = health_manager.breakers[provider_name]
            breaker.failures = 0
            breaker.state = ProviderState.HEALTHY
    except Exception:
        pass  # Circuit breaker may not be initialized yet


# --- Circuit Breaker & Environment Reset ---
@pytest.fixture(autouse=True)
def reset_circuit_breakers_between_tests():
    """Reset all AI provider circuit breakers and ensure real credentials before and after each test."""
    _restore_env_and_settings()
    _reset_breakers()
    yield
    _restore_env_and_settings()
    _reset_breakers()


# --- Rate-Limit Spacing ---
_last_llm_test_time = 0.0


@pytest.fixture(autouse=True)
def rate_limit_spacing():
    """Insert a small delay between tests to avoid API rate limiting."""
    global _last_llm_test_time
    now = time.time()
    elapsed_since_last = now - _last_llm_test_time
    if _last_llm_test_time > 0 and elapsed_since_last < 0.5:
        time.sleep(0.5 - elapsed_since_last)
    yield
    _last_llm_test_time = time.time()


# --- Live Quiz Persistence Control ---
@pytest.fixture(autouse=True)
def live_quiz_persistence_controller(request):
    """
    Ensures in-memory unit tests don't pollute live Supabase with synthetic test IDs,
    while integration and failure tests execute with persistence enabled.
    """
    try:
        from app.services.live_quiz import repository as repo
        module_name = request.module.__name__ if request.module else ""
        is_synthetic_unit_test = any(name in module_name for name in [
            "test_live_quiz_suite",
            "test_live_quiz_session",
            "test_live_quiz_cross_tenant",
            "test_live_quiz_realtime",
            "test_live_quiz_reconnect",
            "test_live_quiz_versioning",
            "test_live_quiz_mastery",
            "test_live_quiz_intervention",
            "test_live_quiz_load",
            "test_live_quiz_rls",
        ])
        if is_synthetic_unit_test and "test_live_quiz_write_failure" not in module_name:
            repo.set_persistence_enabled(False)
        else:
            repo.set_persistence_enabled(True)
        yield
        repo.set_persistence_enabled(True)
    except Exception:
        yield
