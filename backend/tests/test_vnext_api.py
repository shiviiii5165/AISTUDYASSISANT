import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.dependencies import get_current_user


# Mock current authenticated user
class MockUser:
    id = "test_teacher_uuid"
    email = "teacher@teachgenie.test"


from app.core.config import settings

@pytest.fixture(autouse=True)
def override_user(monkeypatch):
    monkeypatch.setattr(settings, "LESSON_VNEXT_ENABLED", True)
    app.dependency_overrides[get_current_user] = lambda: MockUser()
    yield
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_vnext_api_full_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. POST /api/lesson-planner/v2/plan
        plan_payload = {
            "topic": "Dynamic Programming",
            "grade": "B.Tech",
            "subject": "Algorithms",
            "duration_minutes": 60,
            "language": "english",
            "mode": "teacher_classroom"
        }
        res_plan = await client.post("/api/lesson-planner/v2/plan", json=plan_payload)
        assert res_plan.status_code == 200, res_plan.text
        plan_data = res_plan.json()
        assert plan_data["topic"] == "Dynamic Programming"
        assert plan_data["mode"] == "teacher_classroom"
        assert plan_data["domain"] == "computer_science"
        assert len(plan_data["stages"]) >= 3
        plan_id = plan_data["id"]
        first_stage_id = plan_data["stages"][0]["id"]

        # 2. GET /api/lesson-planner/v2/{plan_id}/stages
        res_stages = await client.get(f"/api/lesson-planner/v2/{plan_id}/stages")
        assert res_stages.status_code == 200
        stages_data = res_stages.json()
        assert len(stages_data) == len(plan_data["stages"])

        # 3. GET /api/lesson-planner/v2/{plan_id}/stages/{stage_id}/resources
        res_res = await client.get(f"/api/lesson-planner/v2/{plan_id}/stages/{first_stage_id}/resources")
        assert res_res.status_code == 200
        resources = res_res.json()
        assert isinstance(resources, list)

        # 4. POST /api/lesson-planner/v2/{plan_id}/locks
        lock_payload = {
            "stage_id": first_stage_id,
            "lock_type": "stage",
            "target_identifier": first_stage_id,
            "is_locked": True,
            "notes": "Teacher locked intro hook"
        }
        res_lock = await client.post(f"/api/lesson-planner/v2/{plan_id}/locks", json=lock_payload)
        assert res_lock.status_code == 200
        assert res_lock.json()["message"] == "Lock updated successfully"

        # 5. POST /api/lesson-planner/v2/{plan_id}/evidence (>20% misconception test)
        evidence_payload = {
            "evidence": [
                {"student_id": f"s_{i}", "concept_id": "concept_1", "correctness": True}
                for i in range(6)
            ] + [
                {
                    "student_id": f"s_{i}",
                    "concept_id": "concept_1",
                    "correctness": False,
                    "misconception_candidate": "Greedy Choice Fallacy"
                }
                for i in range(6, 10)
            ],
            "auto_apply": False
        }
        res_ev = await client.post(f"/api/lesson-planner/v2/{plan_id}/evidence", json=evidence_payload)
        assert res_ev.status_code == 200
        ev_data = res_ev.json()
        diff = ev_data.get("diff", ev_data)
        assert len(diff["stages_added"]) == 1
        assert "Greedy Choice Fallacy" in diff["stages_added"][0]["title"]
        assert diff["requires_teacher_approval"] is True

        # 6. POST /api/lesson-planner/v2/{plan_id}/recompile (Teacher ACCEPTs)
        decision_payload = {
            "diff": diff,
            "decision": "ACCEPT"
        }
        res_recompile = await client.post(f"/api/lesson-planner/v2/{plan_id}/recompile", json=decision_payload)
        assert res_recompile.status_code == 200
        recompiled = res_recompile.json()
        assert recompiled["version"] == 2
        assert any("Greedy Choice Fallacy" in s["title"] for s in recompiled["stages"])

        # 7. GET /api/lesson-planner/v2/{plan_id}/why
        res_why = await client.get(f"/api/lesson-planner/v2/{plan_id}/why?stage_id={first_stage_id}")
        assert res_why.status_code == 200
        why_data = res_why.json()
        assert "why_this_stage" in why_data
        assert "why_now" in why_data
        assert "why_this_duration" in why_data
