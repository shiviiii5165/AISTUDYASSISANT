import pytest
from app.core.config import settings
from app.services.lesson_planner.vnext.adaptive import AdaptiveLessonEngine
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_production_safe_feature_flag_defaults():
    """All 10 VNext capability flags must default to False in production config."""
    assert settings.LESSON_VNEXT_ENABLED is False
    assert settings.LESSON_RESOURCE_INTELLIGENCE_ENABLED is False
    assert settings.LESSON_YOUTUBE_SEGMENTS_ENABLED is False
    assert settings.LESSON_ACADEMIC_ENGINE_ENABLED is False
    assert settings.LESSON_CODING_RESOURCES_ENABLED is False
    assert settings.LESSON_ADAPTIVE_ENGINE_ENABLED is False
    assert settings.LESSON_AUTO_STUDENT_ADAPTATION_ENABLED is False
    assert settings.LESSON_CLASS_ADAPTATION_ENABLED is False
    assert settings.LESSON_CROSS_FEATURE_CONTEXT_ENABLED is False
    assert settings.LESSON_OUTCOME_RANKING_ENABLED is False


def test_vnext_disabled_returns_503_feature_not_enabled(monkeypatch):
    """
    When LESSON_VNEXT_ENABLED is False, all /api/lesson-planner/v2/* routes
    must return HTTP 503 with error_code = 'FEATURE_NOT_ENABLED' and metadata.
    Must NOT silently execute V1 semantics behind V2 API contract.
    """
    monkeypatch.setattr(settings, "LESSON_VNEXT_ENABLED", False)

    response = client.post(
        "/api/lesson-planner/v2/plan",
        json={"topic": "Binary Search Trees", "duration_minutes": 60}
    )
    assert response.status_code == 503
    data = response.json()
    assert data["detail"]["error_code"] == "FEATURE_NOT_ENABLED"
    assert "legacy_route" in data["detail"]


def test_legacy_v1_route_remains_active_when_vnext_disabled(monkeypatch):
    """Disabling VNext must not break or disable legacy V1 endpoints."""
    monkeypatch.setattr(settings, "LESSON_VNEXT_ENABLED", False)
    
    # Check legacy V1 health / options / endpoint presence
    response = client.post(
        "/api/lesson-planner/generate",
        json={"topic": "Binary Search Trees", "duration_minutes": 60}
    )
    # Legacy route should NOT return 503 FEATURE_NOT_ENABLED
    assert response.status_code != 503
