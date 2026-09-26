"""
LearnByGenie — Brand Migration & Surface Integrity Test Suite
============================================================
Verifies that all active user-facing application surfaces, metadata,
generators, and client configurations have been migrated to LearnByGenie,
while ensuring backward-compatible storage, environment, and cryptographic
fallbacks remain operational.
"""

import os
import re
import json
import pytest
from app.core.config import settings
from app.main import app


def test_brand_constant_is_learnbygenie():
    """Verify that frontend branding authority defines canonical LearnByGenie."""
    branding_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "frontend", "src", "config", "branding.ts"
    )
    assert os.path.exists(branding_file), f"Branding authority file missing at: {branding_file}"
    with open(branding_file, "r", encoding="utf-8") as f:
        content = f.read()

    assert "name: 'LearnByGenie'" in content
    assert "shortName: 'LearnByGenie'" in content
    assert "aiName: 'LearnByGenie AI'" in content
    assert "liveQuizName: 'LearnByGenie Live Quiz'" in content
    assert "lessonPlannerName: 'LearnByGenie Lesson Planner'" in content
    assert "notesName: 'LearnByGenie Notes'" in content
    assert "tutorName: 'LearnByGenie Tutor'" in content
    assert "pptName: 'LearnByGenie PPT'" in content


def test_fastapi_openapi_branding():
    """Verify that FastAPI application and OpenAPI metadata are branded LearnByGenie."""
    assert app.title == "LearnByGenie API"
    assert "LearnByGenie" in app.description


def test_frontend_metadata_branding():
    """Verify index.html and webmanifest metadata."""
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    index_html = os.path.join(root_dir, "frontend", "index.html")
    manifest_json = os.path.join(root_dir, "frontend", "public", "site.webmanifest")

    with open(index_html, "r", encoding="utf-8") as f:
        html = f.read()
    assert "<title>LearnByGenie" in html
    assert 'content="LearnByGenie' in html
    assert 'TeachGenie - AI Doubt Solver' not in html

    with open(manifest_json, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["name"] == "LearnByGenie"
    assert manifest["short_name"] == "LearnByGenie"


def test_legacy_storage_migration():
    """Verify that storageMigration helper exists and implements dual-read."""
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    storage_migration_ts = os.path.join(root_dir, "frontend", "src", "lib", "storageMigration.ts")
    assert os.path.exists(storage_migration_ts)

    with open(storage_migration_ts, "r", encoding="utf-8") as f:
        content = f.read()
    assert "getMigratedStorageItem" in content
    assert "setMigratedStorageItem" in content
    assert "storage.getItem(newKey)" in content
    assert "storage.getItem(legacyKey)" in content


def test_legacy_env_fallback():
    """Verify that backend configuration supports LEARNBYGENIE_* with fallback to TEACHGENIE_*."""
    assert hasattr(settings, "PROJECT_NAME")
    assert settings.PROJECT_NAME == "LearnByGenie API"
    assert hasattr(settings, "TEACHGENIE_MODE")
    assert hasattr(settings, "LEARNBYGENIE_MODE")


def test_ppt_branding():
    """Verify presentation rendering footers use LearnByGenie."""
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ppt_renderer_path = os.path.join(root_dir, "backend", "app", "services", "ppt_renderer.py")

    with open(ppt_renderer_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Powered by LearnByGenie AI" in content
    assert "Generated with LearnByGenie AI" in content
    assert "Powered by TeachGenie AI" not in content
    assert "Generated with TeachGenie AI" not in content


def test_live_quiz_branding():
    """Verify that Live Quiz join & participant pages display LearnByGenie."""
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    join_page = os.path.join(root_dir, "frontend", "src", "pages", "JoinLiveQuizPage.tsx")

    with open(join_page, "r", encoding="utf-8") as f:
        content = f.read()

    assert "LearnByGenie Real-Time Live Classroom Assessment Engine" in content
    assert "TeachGenie Real-Time Live Classroom Assessment Engine" not in content


def test_no_user_facing_teachgenie_brand():
    """
    Scans active frontend and API surfaces to ensure zero visible TeachGenie references remain,
    allowing explicit exceptions only for legacy compatibility, deployed URLs, and immutable history.
    """
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    scan_targets = [
        os.path.join(root_dir, "frontend", "src", "pages"),
        os.path.join(root_dir, "frontend", "src", "components"),
        os.path.join(root_dir, "backend", "app", "api"),
    ]

    ALLOWED_LEGACY_TOKENS = {
        "teachgenie_cookie_consent",
        "teachgenie_sound_muted",
        "teachgenie_live_participant_",
        "teachgenie_dev_auth",
        "teachgenie:practice-weak-topic",
        "contact@teachgenie.online",
        "https://teachgenie.online",
        "teachgenie.online",
        "X-TeachGenie-",
        "legacyName: 'TeachGenie'",
        "legacyName",
    }

    prohibited_matches = []
    pattern = re.compile(r'\bTeachGenie\b', re.IGNORECASE)

    for target in scan_targets:
        for r, _, files in os.walk(target):
            for file in files:
                if file.endswith((".tsx", ".ts", ".py")):
                    fpath = os.path.join(r, file)
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for line_no, line in enumerate(f, 1):
                            if any(token in line for token in ALLOWED_LEGACY_TOKENS):
                                continue
                            if pattern.search(line):
                                prohibited_matches.append((fpath, line_no, line.strip()))

    assert len(prohibited_matches) == 0, f"Found prohibited user-facing legacy brand references: {prohibited_matches[:5]}"
