"""Offline tests: legacy gates, complete erasure, scheduler and multilingual retrieval."""
import asyncio
import re
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import AuthenticatedUser, get_current_user, require_role
from app.db import supabase_client
from app.main import app
from app.modules import store
from app.modules.privacy import mfa, service as privacy
from app.modules.rag_tutor.retrieval import get_index
from app.services.portals.repository import PortalsRepository

STUDENT, PARENT, TEACHER, ADMIN = (str(uuid.uuid4()) for _ in range(4))
ROLES = {STUDENT: "student", PARENT: "parent", TEACHER: "teacher", ADMIN: "super_admin"}


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setattr(supabase_client, "supabase", None)
    monkeypatch.setattr("app.services.portals.repository.supabase", None)
    monkeypatch.setattr("app.core.user_roles.UserRoleRepository.get_user_role", lambda uid: ROLES.get(uid))
    store.clear_memory()
    PortalsRepository.clear_memory_cache()
    yield
    app.dependency_overrides.clear()


def client_for(user_id):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id=user_id, email="u@test.example", role=ROLES[user_id])
    return TestClient(app)


def test_legacy_parent_link_waits_for_otp_consent_and_keeps_the_code():
    code = PortalsRepository.generate_student_invite_code(STUDENT)
    parent = client_for(PARENT)
    blocked = parent.post("/api/portals/parent/link-child", json={"invitation_code": code})
    assert blocked.status_code == 403 and blocked.json()["detail"]["code"] == "consent_required"
    store.insert("guardian_consents", {"student_id": STUDENT, "guardian_id": None, "purpose": "parent_reports",
                                       "method": "otp", "granted_at": store.now_iso(), "withdrawn_at": None})
    assert parent.post("/api/portals/parent/link-child", json={"invitation_code": code}).status_code == 200
    assert PortalsRepository.get_linked_student_ids(PARENT) == [STUDENT]


@pytest.mark.parametrize("method,path,user", [
    ("GET", "/api/portals/teacher/dashboard", TEACHER),
    ("POST", "/api/portals/teacher/classrooms", TEACHER),
    ("GET", "/api/portals/teacher/classrooms/x/roster", TEACHER),
    ("GET", "/api/portals/creator/items/pending", TEACHER),
    ("POST", "/api/portals/creator/items/x/approve", TEACHER),
    ("GET", "/api/portals/super-admin/overview", ADMIN),
    ("POST", "/api/portals/super-admin/user-role", ADMIN),
])
def test_legacy_staff_routes_require_mfa(method, path, user):
    response = client_for(user).request(method, path, json={})
    assert response.status_code == 403 and response.json()["detail"]["code"] == "mfa_required"


def test_me_roles_stays_open_so_staff_can_reach_enrollment():
    assert client_for(TEACHER).get("/api/portals/me/roles").status_code == 200


def test_every_legacy_staff_route_has_the_mfa_gate():
    from app.api import portals

    guarded = 0
    for route in portals.router.routes:
        if re.match(r"/(teacher|school-admin|super-admin|creator/items/)", route.path):
            assert any(d.dependency is mfa.require_mfa for d in route.dependencies), route.path
            guarded += 1
    assert guarded >= 8
    open_paths = {r.path for r in portals.router.routes if not any(d.dependency is mfa.require_mfa for d in r.dependencies)}
    assert not any(p.startswith(("/teacher", "/school-admin", "/super-admin")) for p in open_paths)


def test_erasure_purges_legacy_tables_and_leaves_anonymous_receipt():
    for table, column in privacy.PERSONAL_TABLES:
        store.insert(table, {column: STUDENT, "marker": table})
    session = store.insert("chat_sessions", {"user_id": STUDENT})
    store.insert("chat_messages", {"session_id": session["id"]})
    store.insert("quiz_attempts", {"user_id": "someone-else"})
    store.insert("guardian_consents", {"student_id": STUDENT, "guardian_id": PARENT, "purpose": "learning_analytics",
                                       "method": "otp", "granted_at": store.now_iso(), "withdrawn_at": None})
    result = client_for(STUDENT).request("DELETE", "/api/v1/privacy/erase", json={"confirm": "ERASE"}).json()
    assert result["status"] == "completed"
    for required in ("quiz_attempts", "quizzes", "socratic_tutor_sessions", "chat_sessions", "generated_notes",
                     "step_grader_attempts", "transfer_responses", "daily_usage", "roadmap_events"):
        assert required in {t for t, _ in privacy.PERSONAL_TABLES}
    for table, column in privacy.PERSONAL_TABLES:
        assert not store.select(table, **{column: STUDENT}), table
    assert not store.select("chat_messages", session_id=session["id"])
    assert store.select("quiz_attempts", user_id="someone-else")
    receipt = store.select("erasure_requests")[0]
    assert receipt["student_id"] != STUDENT and receipt["requested_by"] != STUDENT
    uuid.UUID(receipt["student_id"])
    consent = store.select("guardian_consents")[0]
    assert consent["student_id"] == receipt["student_id"] and consent["guardian_id"] is None
    assert STUDENT not in str(store.select("erasure_requests")) + str(store.select("guardian_consents"))


def test_failed_table_stays_partial_then_retry_completes(monkeypatch):
    real_delete = store.delete
    monkeypatch.setattr(store, "delete", lambda t, **f: (_ for _ in ()).throw(RuntimeError("down")) if t == "pdfs" else real_delete(t, **f))
    first = privacy.request_erasure(STUDENT, STUDENT)
    assert first["status"] == "partial" and first["failed_tables"] == ["pdfs"]
    monkeypatch.setattr(store, "delete", real_delete)
    assert privacy.run_pending_erasures() == 1
    assert store.select("erasure_requests")[0]["status"] == "completed"


def test_missing_optional_table_does_not_block_completion(monkeypatch):
    real_delete = store.delete
    monkeypatch.setattr(store, "delete", lambda t, **f: (_ for _ in ()).throw(RuntimeError("PGRST205")) if t == "daily_activity" else real_delete(t, **f))
    assert privacy.request_erasure(STUDENT, STUDENT)["status"] == "completed"


def test_scheduler_loop_retries_and_survives_errors(monkeypatch):
    calls = []

    def fake_run():
        calls.append(1)
        raise RuntimeError("database down")

    monkeypatch.setattr(privacy, "run_pending_erasures", fake_run)

    async def run():
        task = asyncio.create_task(privacy.erasure_retry_loop(interval_seconds=0.01))
        await asyncio.sleep(0.1)
        task.cancel()

    asyncio.run(run())
    assert len(calls) >= 2


def test_lifespan_starts_scheduler():
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200


@pytest.mark.parametrize("query,concept", [
    ("द्विघात समीकरण का विविक्तकर क्या है", "m10_quadratic"),
    ("dwighat samikaran ke mool kaise nikale", "m10_quadratic"),
    ("ohm ka niyam vibhav dhara pratirodh", "s10_ohms"),
    ("गति में वेग और विस्थापन", "s9_motion"),
    ("उत्तल दर्पण concave darpan", "s10_mirrors"),
    ("प्रकाश का अपवर्तन लेंस", "s10_lenses"),
    ("why does light bend in a lens", "s10_lenses"),
    ("how fast is a car moving", "s9_motion"),
])
def test_hindi_hinglish_and_paraphrases_reach_the_right_concept(query, concept):
    result = get_index().retrieve(query, 10)
    assert result.grounding, (query, result.best_score)
    assert result.grounding[0].concept_id == concept


@pytest.mark.parametrize("query", ["who won the cricket world cup", "what time is it in london", "क्रिकेट विश्व कप किसने जीता"])
def test_off_syllabus_queries_still_fall_back(query):
    assert get_index().retrieve(query, 10).grounding == []


def test_class_filter_applies_to_hindi_queries():
    assert get_index().retrieve("द्विघात समीकरण विविक्तकर", 8).grounding == []


def test_offline_profile_saves_but_production_never_fakes_it(monkeypatch):
    from fastapi import HTTPException
    import app.services.learner_context.repository as repo
    monkeypatch.setattr(repo, "supabase", None)
    monkeypatch.setenv("SUPABASE_OFFLINE_MODE", "true")
    assert repo.LearnerProfileRepository.create_or_upsert(STUDENT, {"preferred_language": "hi"})["profile_version"] == 1
    monkeypatch.setattr(repo, "_explicit_offline_mode", lambda: False)
    with pytest.raises(HTTPException) as err:
        repo.LearnerProfileRepository.create_or_upsert(PARENT, {})
    assert err.value.status_code == 503


def test_outbound_network_is_blocked_in_tests():
    import socket
    with pytest.raises(ConnectionRefusedError):
        socket.socket().connect(("8.8.8.8", 53))
