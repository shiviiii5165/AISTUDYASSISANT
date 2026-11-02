"""Offline integration tests for /api/v1 through the real FastAPI app and auth layer."""
import base64
from fractions import Fraction
import hashlib
import os
import time
import uuid

os.environ["SUPABASE_OFFLINE_MODE"] = "true"
os.environ["TUTOR_LLM_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import AuthenticatedUser, get_current_user
from app.db import supabase_client
from app.main import app
from app.modules import context, rate_limit, store
from app.modules.curriculum.items import all_items, get_item, items_for
from app.modules.curriculum.ncert_seed import CONCEPTS, CONCEPTS_BY_ID
from app.modules.error_to_mastery import engine
from app.modules.error_to_mastery.classifier import classify_error, deterministic_rate
from app.modules.learning_core.math_verifier import Verdict, verify_derivation
from app.modules.privacy import mfa, service as privacy
from app.modules.rag_tutor import modes, safety, service as tutor
from app.modules.rag_tutor.modes import Mode

A, B = str(uuid.uuid4()), str(uuid.uuid4())
TEACHER, OTHER_TEACHER, PARENT, OTHER_PARENT, CREATOR = (str(uuid.uuid4()) for _ in range(5))
ROLES = {A: "student", B: "student", TEACHER: "teacher", OTHER_TEACHER: "teacher",
         PARENT: "parent", OTHER_PARENT: "parent", CREATOR: "content_creator"}
CLASSES = {A: 10, B: 10}


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setattr(supabase_client, "supabase", None)
    monkeypatch.setattr("app.core.user_roles.UserRoleRepository.get_user_role", lambda uid: ROLES.get(uid))
    monkeypatch.setattr(context, "student_class", lambda uid: CLASSES.get(uid, 10))
    CLASSES.update({A: 10, B: 10})
    store.clear_memory()
    rate_limit.clear()
    tutor._cache.clear()
    yield
    app.dependency_overrides.clear()


def client_for(user_id):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=user_id, email="u@test.example", role=ROLES[user_id])
    return TestClient(app)


def consent(student_id, purpose="learning_analytics"):
    store.insert("guardian_consents", {"student_id": student_id, "guardian_id": None, "purpose": purpose,
                                       "method": "otp", "granted_at": store.now_iso(), "withdrawn_at": None})


def ask(client, message, **kwargs):
    response = client.post("/api/v1/tutor/ask", json={"message": message, **kwargs})
    assert response.status_code == 200, response.text
    return response.json()


# ---- Content -------------------------------------------------------------

def test_bank_size_and_no_answer_exposure():
    assert len(all_items()) >= 1000
    view = all_items()[0].public_view()
    assert "answer" not in view and "traps" not in view


def test_seed_is_valid_with_acyclic_prerequisites():
    from scripts.seed_ncert_mvp import validate
    assert validate() == []
    visiting, done = set(), set()

    def visit(node):
        assert node not in visiting
        if node not in done:
            visiting.add(node)
            for parent in CONCEPTS_BY_ID[node].prerequisites:
                visit(parent)
            visiting.remove(node)
            done.add(node)
    for concept in CONCEPTS:
        visit(concept.concept_id)


def test_algebra_worked_examples_verify():
    for concept in CONCEPTS:
        if concept.subject == "Mathematics":
            assert verify_derivation(concept.worked_steps).verdict is Verdict.VERIFIED, concept.concept_id


# ---- Sprint 1 pipeline ---------------------------------------------------

def test_consent_blocks_learning_endpoints():
    c = client_for(A)
    r = c.post("/api/v1/diagnostics/start", json={"subject": "Mathematics"})
    assert r.status_code == 403 and r.json()["detail"]["code"] == "consent_required"


def test_cat_runs_to_stop_rule_and_awards_once():
    consent(A)
    c = client_for(A)
    started = c.post("/api/v1/diagnostics/start", json={"subject": "Mathematics"}).json()
    assert "answer" not in started["item"]
    step = started
    count = 0
    while not step["complete"]:
        item = get_item(step["item"]["item_id"])
        step = c.post(f"/api/v1/diagnostics/{started['session_id']}/answer",
                      json={"item_id": item.item_id, "response": item.answer}).json()
        count += 1
    assert 8 <= count <= 15
    assert step["theta"] > 0.5
    assert len(store.select("xp_events", student_id=A, rule_id="RULE_XP_01")) == 1


def _answer(c, sid, item_id, response, **extra):
    return c.post(f"/api/v1/practice/{sid}/submit", json={
        "item_id": item_id, "response": response, "idempotency_key": uuid.uuid4().hex, **extra})


def _drive_to_tier3(c, concept_id="m8_linear_one"):
    started = c.post("/api/v1/practice/start", json={"concept_id": concept_id}).json()
    sid, step = started["session_id"], started["next"]
    result = None
    for _ in range(3):
        item = get_item(step["item"]["item_id"])
        result = _answer(c, sid, item.item_id, item.answer).json()
        step = result["next"]
    return sid, result


def test_three_unhinted_passes_reach_tier3_and_xp_once():
    consent(A)
    c = client_for(A)
    _, result = _drive_to_tier3(c)
    assert result["tier"] == 3 and result["unlocks_children"]
    assert [x["rule_id"] for x in result["xp_awarded"]] == ["RULE_XP_03"]
    assert store.get_one("review_schedule", student_id=A, skill_id="m8_linear_one")


def test_submit_idempotent_replay_and_rejects_foreign_item():
    consent(A)
    c = client_for(A)
    started = c.post("/api/v1/practice/start", json={"concept_id": "m8_linear_one"}).json()
    sid = started["session_id"]
    item = get_item(started["next"]["item"]["item_id"])
    body = {"item_id": item.item_id, "response": item.answer, "idempotency_key": "replay-key-1"}
    first = c.post(f"/api/v1/practice/{sid}/submit", json=body).json()
    second = c.post(f"/api/v1/practice/{sid}/submit", json=body).json()
    assert second["replayed"] and second["p_mastery"] == first["p_mastery"]
    assert len(store.select("practice_attempts_v1", student_id=A)) == 1
    assert _answer(c, sid, "m10_quadratic.L0.001", "1").status_code == 409


def test_wheel_spin_switches_to_simulation_and_tokens_logged():
    consent(A)
    c = client_for(A)
    started = c.post("/api/v1/practice/start", json={"concept_id": "m8_linear_one"}).json()
    sid, step = started["session_id"], started["next"]
    for _ in range(3):
        result = _answer(c, sid, step["item"]["item_id"], "99999", confidence="Sure").json()
        step = result["next"]
    assert result["entrenched_misconception"]
    assert step["action"] == "simulation" and step["activity"] == "AlgebraStepBuilder"
    assert len(store.select("error_tokens", student_id=A, status="active")) == 3


def test_e02_maps_gap_and_opens_recovery_quest():
    consent(A)
    c = client_for(A)
    started = c.post("/api/v1/practice/start", json={"concept_id": "m10_quadratic"}).json()
    assert started["prescription"]["remediation_path"][0] == "m8_linear_one"
    item = get_item(started["next"]["item"]["item_id"])
    result = _answer(c, started["session_id"], item.item_id, "not a number").json()
    assert result["error_token"]["token"] == "E02"
    assert result["remediation_path"]
    assert store.select("quests", student_id=A, kind="recovery")


def test_step_attribution_names_success_first():
    consent(A)
    c = client_for(A)
    started = c.post("/api/v1/practice/start", json={"concept_id": "m8_linear_one"}).json()
    item = get_item(started["next"]["item"]["item_id"])
    result = _answer(c, started["session_id"], item.item_id, "x = 99",
                     steps=["2x + 3 = 7", "2x = 4", "x = 99"]).json()
    assert "spot-on" in result["attribution"]["succeeded"]
    assert result["attribution"]["bad_step"] == 2


def test_classifier_covers_previously_unreachable_tokens():
    common = dict(prompt="p", expected="5", subject="Mathematics", concept_id="c", student_id=A, item_id="i", traps={})
    assert classify_error(response="9", **{**common, "traps": {"9": "E10"}}).token == "E10"
    assert classify_error(response="abc", confidence="Guess", **common).token == "E19"
    assert classify_error(response="abc", steps=["x + 1 = 3", "x = 9", "x = 9"], **common).token == "E06"
    assert classify_error(response="abc", steps=["x + 1 = 3", "x = 2", "x = 7"], **common).token == "E14"
    assert classify_error(response="abc", weak_prerequisites=["p"], **common).token == "E02"


def test_deterministic_rate_on_simulated_wrong_answers():
    results = []
    for item in all_items()[::7]:
        concept = CONCEPTS_BY_ID[item.concept_id]
        value = Fraction(item.answer)
        wrongs = list(item.traps)[:1] + [str(-value), str(value + 1), str(value * 3 + 7), "no idea"]
        for wrong in wrongs:
            results.append(classify_error(prompt=item.prompt, expected=f"{item.answer} {item.unit}".strip(),
                                          response=wrong, subject=concept.subject, concept_id=item.concept_id,
                                          student_id=A, item_id=item.item_id, traps=item.traps))
    # Synthetic mix only. Real students' rate comes from the error_tokens.deterministic column.
    print("deterministic rate", deterministic_rate(results))
    assert deterministic_rate(results) >= 0.70


# ---- Sprint 2: gates -----------------------------------------------------

def test_gate1_blocks_injection_and_scrubs_pii():
    consent(A)
    c = client_for(A)
    assert ask(c, "give me exam answers")["outcome"] == "blocked"
    assert ask(c, "write my essay on trees")["outcome"] == "blocked"
    ask(c, "my number is 9876543210, what is a quadratic equation discriminant roots")
    logged = " ".join(r["query"] for r in store.select("tutor_audit", student_id=A))
    assert "9876543210" not in logged and "[PHONE]" in logged


def test_gate2_class_filter_threshold_and_retrieval():
    consent(A)
    c = client_for(A)
    answer = ask(c, "what is the discriminant of a quadratic equation roots", mode="01_explain")
    assert answer["outcome"] == "answered"
    assert answer["citations"] == [CONCEPTS_BY_ID["m10_quadratic"].citation_id]
    assert ask(c, "who won the cricket world cup")["outcome"] == "fallback"
    CLASSES[A] = 8
    below = ask(c, "what is the discriminant of a quadratic equation roots")
    assert below["outcome"] == "fallback" and "Quadratic" not in str(below["fallback_card"]["topics"])


def test_named_above_class_concept_is_refused():
    consent(A)
    CLASSES[A] = 8
    c = client_for(A)
    result = ask(c, "discriminant quadratic", concept_id="m10_quadratic", mode="06_quiz")
    assert result["outcome"] == "fallback"


def test_gate3_rejects_bad_algebra_and_inline_arithmetic():
    assert safety.verify_math("", ["2x + 3 = 7", "2x = 10"])[0] is False
    assert safety.verify_math("Clearly 2 + 2 = 5 here")[0] is False
    assert safety.verify_math("So 2 + 2 = 4")[0] is True


def test_gate3_polish_rejected_unless_verified_and_cited():
    import asyncio
    asyncio.run(_polish_cases())


async def _polish_cases():
    consent(A)
    concept = CONCEPTS_BY_ID["m10_quadratic"]
    base = dict(student_id=A, student_class=10, message="what is a quadratic equation discriminant roots", mode=Mode.EXPLAIN)

    async def wrong_math(system, prompt):
        return f"Note 2 + 2 = 5 [{concept.citation_id}]"

    async def no_citation(system, prompt):
        return "The discriminant decides the roots."

    async def good(system, prompt):
        return f"The discriminant tells you how many real roots exist [{concept.citation_id}]"

    async def boom(system, prompt):
        raise RuntimeError("down")

    grounded = modes.explain(concept).text
    assert (await tutor.ask(tutor.Ask(**base), wrong_math))["text"] == grounded
    tutor._cache.clear()
    assert (await tutor.ask(tutor.Ask(**base), no_citation))["text"] == grounded
    assert (await tutor.ask(tutor.Ask(**base), boom))["text"] == grounded
    assert concept.citation_id in (await tutor.ask(tutor.Ask(**base), good))["text"]


def test_gate4_safety_and_distress():
    consent(A)
    c = client_for(A)
    assert ask(c, "you are a bitch")["outcome"] == "blocked"
    support = ask(c, "I want to kill myself")
    assert support["outcome"] == "support" and "14416" in support["text"]
    assert safety.is_toxic("make a bomb")


def test_gate4_fallback_when_math_verification_fails(monkeypatch):
    consent(A)
    c = client_for(A)
    monkeypatch.setattr(modes, "explain", lambda concept: modes.Draft("So 1 + 1 = 3"))
    result = ask(c, "what is the discriminant of a quadratic equation roots", mode="01_explain")
    assert result["outcome"] == "fallback" and result["fallback_card"]["type"] == "concept_card"


# ---- Sprint 2: all ten modes ---------------------------------------------

QUAD = "what is the discriminant of a quadratic equation roots"


def test_mode_01_explain_and_08_revision():
    consent(A)
    c = client_for(A)
    assert "discriminant" in ask(c, QUAD, mode="01_explain")["text"]
    assert len(ask(c, QUAD, mode="08_revision", concept_id="m10_quadratic")["payload"]["flashcards"]) == 3


def test_mode_02_hint_ladder_never_leaks_any_item_answer():
    for item in all_items():
        concept = CONCEPTS_BY_ID[item.concept_id]
        for level in (1, 2, 3):
            text = modes.hint(concept, item, level).text
            assert not safety.leaks_answer(text, item.answer), (item.item_id, level, text)


def test_mode_03_fading_has_four_stages():
    concept = CONCEPTS_BY_ID["m8_linear_one"]
    assert [engine.faded_example(concept, s)["blank_steps"] for s in range(4)] == [0, 1, 2, 3]
    consent(A)
    c = client_for(A)
    answer = ask(c, "solve", mode="03_step_by_step", concept_id="m8_linear_one", fade_stage=1)
    assert answer["payload"]["example"]["stage"] == "late_step"


def test_auto_mode_tier0_uses_step_by_step():
    consent(A)
    assert ask(client_for(A), QUAD)["mode"] == "03_step_by_step"


def test_mode_04_socratic_asks_and_advances():
    consent(A)
    c = client_for(A)
    first = ask(c, "help", mode="04_socratic", concept_id="m8_linear_one")
    second = ask(c, "help", mode="04_socratic", session_id=first["payload"]["session_id"])
    assert first["text"].endswith("?") and first["text"] != second["text"]


def test_mode_05_mistake_repair_leads_with_success():
    consent(A)
    result = ask(client_for(A), "fix", mode="05_mistake_repair", concept_id="m8_linear_one",
                 attribution={"succeeded": "Step 1 was spot-on.", "fix": "Fix step 2."})
    assert result["text"].startswith("Step 1 was spot-on.")


def test_mode_06_quiz_flags_entrenched_wrong_answer():
    consent(A)
    c = client_for(A)
    q = ask(c, "quiz me", mode="06_quiz", concept_id="m8_linear_one")
    assert "answer" not in q["payload"]["item"]
    graded = ask(c, "answer", mode="06_quiz", session_id=q["payload"]["session_id"], answer="99999", confidence="Sure")
    assert graded["payload"]["entrenched_misconception"] is True
    assert store.select("error_tokens", student_id=A, rule="HIGH_CONFIDENCE_WRONG")


def test_mode_07_teach_back_rubric_and_xp_threshold():
    consent(A)
    c = client_for(A)
    weak = ask(c, "it is about equations and other things that i kind of remember from class today", mode="07_teach_back", concept_id="m8_linear_one")
    assert weak["payload"]["score"] < 2 and not store.select("xp_events", student_id=A, rule_id="RULE_XP_06")
    good = ("You keep both sides balanced because each operation must apply to both sides, "
            "so you can isolate the variable. For example 2x = 6 gives x = 3.")
    passed = ask(c, good, mode="07_teach_back", concept_id="m8_linear_one")
    assert passed["payload"]["score"] == 3
    assert store.get_one("xp_events", student_id=A, rule_id="RULE_XP_06")["amount"] == 25
    copied = " ".join(CONCEPTS_BY_ID["m8_linear_one"].card().values())
    assert modes.teach_back_rubric(CONCEPTS_BY_ID["m8_linear_one"], copied)["score"] == 0


def test_mode_09_exam_simulation_grades_server_side():
    consent(A)
    c = client_for(A)
    paper = ask(c, "exam", mode="09_exam_simulation", concept_id="m8_linear_one")
    items = paper["payload"]["items"]
    assert len(items) == 10 and paper["payload"]["hints"] is False
    answers = {i["item_id"]: get_item(i["item_id"]).answer for i in items}
    graded = ask(c, "done", mode="09_exam_simulation", session_id=paper["payload"]["session_id"], answers=answers)
    assert graded["payload"]["score"] == graded["payload"]["total"]


def test_mode_10_challenge_uses_hardest_unhinted():
    consent(A)
    result = ask(client_for(A), "challenge", mode="10_challenge_transfer", concept_id="m8_linear_one")
    assert result["payload"]["unhinted"]
    assert ".L2." in result["payload"]["item"]["item_id"]


def test_ai_daily_limit():
    consent(A)
    c = client_for(A)
    for _ in range(30):
        assert c.post("/api/v1/tutor/ask", json={"message": "hello there"}).status_code == 200
    assert c.post("/api/v1/tutor/ask", json={"message": "hello there"}).status_code == 429


# ---- Sprint 3: consent, privacy, MFA ------------------------------------

def test_otp_consent_flow_and_lockout():
    c = client_for(A)
    r = c.post("/api/v1/consent/request-otp", json={"guardian_contact": "+919876543210"}).json()
    bad = "000000" if r["dev_otp"] != "000000" else "111111"
    assert c.post("/api/v1/consent/verify-otp", json={"request_id": r["request_id"], "otp": bad}).status_code == 400
    assert client_for(B).post("/api/v1/consent/verify-otp", json={"request_id": r["request_id"], "otp": r["dev_otp"]}).status_code == 404
    c = client_for(A)
    assert c.post("/api/v1/consent/verify-otp", json={"request_id": r["request_id"], "otp": r["dev_otp"]}).status_code == 200
    assert c.get("/api/v1/consent/status").json()["learning_analytics"] is True
    assert c.post("/api/v1/consent/verify-otp", json={"request_id": r["request_id"], "otp": r["dev_otp"]}).status_code == 410
    assert store.select("consent_otps", student_id=A)[0]["otp_hash"] != r["dev_otp"]


def test_otp_fails_closed_in_production_without_gateway(monkeypatch):
    monkeypatch.setattr(privacy, "_is_dev", lambda: False)
    monkeypatch.setenv("OTP_HASH_SECRET", "x")
    monkeypatch.delenv("OTP_WEBHOOK_URL", raising=False)
    with pytest.raises(privacy.ConsentError) as err:
        privacy.request_otp(A, "+919876543210", "learning_analytics")
    assert err.value.code == "otp_delivery_not_configured"


def test_withdrawing_consent_blocks_again():
    consent(A)
    c = client_for(A)
    assert c.get("/api/v1/shield").status_code == 200
    c.post("/api/v1/consent/withdraw", json={"purpose": "learning_analytics"})
    assert c.get("/api/v1/shield").status_code == 403


def test_export_json_pdf_and_idor():
    consent(A)
    c = client_for(A)
    _drive_to_tier3(c)
    data = c.get("/api/v1/privacy/export").json()
    assert data["tables"]["learner_bkt_state"][0]["student_id"] == A
    pdf = c.get("/api/v1/privacy/export?format=pdf")
    assert pdf.content.startswith(b"%PDF")
    assert client_for(B).get(f"/api/v1/privacy/export?student_id={A}").status_code == 404
    assert client_for(OTHER_PARENT).get(f"/api/v1/privacy/export?student_id={A}").status_code == 404


def test_erasure_removes_data_requires_confirmation_and_blocks_others():
    consent(A)
    c = client_for(A)
    _drive_to_tier3(c)
    assert client_for(B).request("DELETE", "/api/v1/privacy/erase", json={"confirm": "ERASE", "student_id": A}).status_code == 404
    c = client_for(A)
    assert c.request("DELETE", "/api/v1/privacy/erase", json={"confirm": "no"}).status_code == 422
    result = c.request("DELETE", "/api/v1/privacy/erase", json={"confirm": "ERASE"}).json()
    assert result["status"] == "completed" and result["records_deleted"] > 0
    assert not store.select("practice_attempts_v1", student_id=A)
    assert not store.select("learner_bkt_state", student_id=A)


def test_guardian_can_export_only_verified_child():
    consent(A)
    store.insert("parent_student_links", {"parent_id": PARENT, "student_id": A, "verification_status": "pending"})
    assert client_for(PARENT).get(f"/api/v1/privacy/export?student_id={A}").status_code == 404
    store.update("parent_student_links", {"parent_id": PARENT}, {"verification_status": "verified"})
    assert client_for(PARENT).get(f"/api/v1/privacy/export?student_id={A}").status_code == 200


def test_totp_rfc6238_vector_and_replay():
    secret = base64.b32encode(b"12345678901234567890").decode()
    assert mfa.totp(secret, 59 // 30)[-6:] == "287082"
    counter = mfa.check_totp(secret, "287082", 0, now=59)
    assert counter == 1
    assert mfa.check_totp(secret, "287082", counter, now=59) is None


def test_mfa_required_for_teacher_then_allowed():
    c = client_for(TEACHER)
    blocked = c.get("/api/v1/dashboard/teacher")
    assert blocked.status_code == 403 and blocked.json()["detail"]["code"] == "mfa_required"
    secret = c.post("/api/v1/auth/mfa/enroll").json()["secret"]
    code = mfa.totp(secret, int(time.time() // 30))
    token = c.post("/api/v1/auth/mfa/verify", json={"code": code}).json()["mfa_token"]
    assert c.get("/api/v1/dashboard/teacher", headers={"X-MFA-Token": token}).status_code == 200
    other = client_for(OTHER_TEACHER)
    assert other.get("/api/v1/dashboard/teacher", headers={"X-MFA-Token": token}).status_code == 403


def test_pkce_s256():
    verifier = "a" * 50
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert mfa.verify_pkce(verifier, challenge)
    assert not mfa.verify_pkce("b" * 50, challenge)
    assert not mfa.verify_pkce("short", challenge)


# ---- Sprint 3: quests, guilds, leagues ----------------------------------

def test_daily_quest_three_reviews_one_repair():
    consent(A)
    for concept_id in ("m8_linear_one", "m9_polynomials", "m9_linear_two", "s9_motion"):
        store.insert("review_schedule", {"student_id": A, "skill_id": concept_id, "stability_days": 4, "step": 0,
                                         "due_at": "2020-01-01T00:00:00+00:00", "last_reviewed_at": None})
    store.insert("error_tokens", {"student_id": A, "concept_id": "s10_ohms", "token": "E06", "status": "active", "created_at": store.now_iso()})
    tasks = client_for(A).get("/api/v1/quests/daily").json()["tasks"]
    assert [t["type"] for t in tasks] == ["review"] * 3 + ["error_repair"]


def test_boss_battle_requires_two_concepts_and_grades():
    consent(A)
    c = client_for(A)
    assert c.post("/api/v1/quests/boss/start", json={"concept_ids": ["m8_linear_one", "nope"]}).status_code == 409
    boss = c.post("/api/v1/quests/boss/start", json={"concept_ids": ["m8_linear_one", "m10_quadratic"]}).json()
    answers = {i["item_id"]: get_item(i["item_id"]).answer for i in boss["items"]}
    won = c.post(f"/api/v1/quests/boss/{boss['quest_id']}/submit", json={"answers": answers}).json()
    assert won["boss_mastered"]
    assert client_for(B).post(f"/api/v1/quests/boss/{boss['quest_id']}/submit", json={"answers": {}}).status_code == 403
    consent(B)
    assert client_for(B).post(f"/api/v1/quests/boss/{boss['quest_id']}/submit", json={"answers": {}}).status_code == 404


def test_shield_counts_four_of_seven():
    from datetime import date, timedelta
    from app.modules.gamification_v1.quests import record_activity, weekly_shield
    monday = date(2026, 11, 2)
    for offset in (0, 2, 4):
        record_activity(A, monday + timedelta(days=offset))
    assert not weekly_shield(A, monday + timedelta(days=4))["shield_earned"]
    record_activity(A, monday + timedelta(days=5))
    state = weekly_shield(A, monday + timedelta(days=5))
    assert state["shield_earned"] and state["active_days"] == 4


def test_guild_cap_and_minimum_contribution():
    from app.modules.gamification_v1 import quests
    guild = quests.create_guild(A, "Team", 10)
    members = [A]
    for _ in range(3):
        sid = str(uuid.uuid4())
        quests.join_guild(sid, guild["join_code"], 10)
        members.append(sid)
    with pytest.raises(engine.Conflict):
        quests.join_guild(str(uuid.uuid4()), guild["join_code"], 10)
    with pytest.raises(engine.Conflict):
        quests.join_guild(str(uuid.uuid4()), quests.create_guild(str(uuid.uuid4()), "T2", 10)["join_code"], 7)

    def repairs(sid, count):
        for _ in range(count):
            store.insert("error_tokens", {"student_id": sid, "concept_id": "c", "token": "E06", "status": "resolved",
                                          "created_at": store.now_iso(), "resolved_at": store.now_iso()})
    repairs(members[0], 17)
    repairs(members[1], 1)
    repairs(members[2], 1)
    repairs(members[3], 1)
    state = quests.guild_quest(A)
    assert state["total"] >= state["target"] and not state["complete"]  # Free-riding blocked.
    for sid in members[1:]:
        repairs(sid, 3)
    assert quests.guild_quest(A)["complete"]


def test_leagues_blocked_below_class_9_and_pseudonymous():
    consent(A)
    consent(B)
    CLASSES[A] = 8
    c = client_for(A)
    assert c.post("/api/v1/leagues/opt-in").status_code == 403
    assert c.get("/api/v1/leagues/board").status_code == 403
    CLASSES[A] = 10
    assert c.get("/api/v1/leagues/board").status_code == 409
    c.post("/api/v1/leagues/opt-in")
    b = client_for(B)
    b.post("/api/v1/leagues/opt-in")
    board = b.get("/api/v1/leagues/board")
    assert A not in board.text and len(board.json()["board"]) == 2
    c = client_for(A)
    c.post("/api/v1/leagues/opt-out")
    assert len(client_for(B).get("/api/v1/leagues/board").json()["board"]) == 1


# ---- Sprint 3: dashboards and IDOR --------------------------------------

def _classroom(teacher=TEACHER, students=(A,)):
    room = store.insert("classrooms", {"school_id": "s", "teacher_id": teacher, "name": "10A", "grade_level": "10"})
    for sid in students:
        store.insert("classroom_enrollments", {"classroom_id": room["id"], "student_id": sid, "status": "enrolled"})
    return room["id"]


def _teacher_client(teacher=TEACHER):
    c = client_for(teacher)
    c.headers["X-MFA-Token"] = _mint(teacher)
    return c


def _mint(user_id):
    import jwt
    return jwt.encode({"sub": user_id, "exp": int(time.time()) + 600, "typ": "mfa"}, mfa._token_key(), algorithm="HS256")


def test_student_dashboard_plan_split_choices_intention():
    consent(A)
    c = client_for(A)
    data = c.get("/api/v1/dashboard/student").json()
    assert data["plan"]["split_percent"] == {"spaced_error_repair": 30, "core_progression": 50, "interleaved_transfer": 20}
    assert sum(data["plan"]["minutes"].values()) == 30
    assert 1 <= len(data["plan"]["choices"]) <= 3
    saved = c.post("/api/v1/dashboard/student/intention", json={"when": "after dinner at 7 PM", "action": "do 15m Math"}).json()
    assert saved["statement"] == "When after dinner at 7 PM, I will do 15m Math"


def test_parent_card_needs_verified_link_and_consent():
    consent(A)
    _drive_to_tier3(client_for(A))
    store.insert("parent_student_links", {"parent_id": PARENT, "student_id": A, "verification_status": "verified"})
    data = client_for(PARENT).get("/api/v1/dashboard/parent").json()
    assert data["cards"] == [] and data["awaiting_consent"] == [A]
    consent(A, "parent_reports")
    card = client_for(PARENT).get("/api/v1/dashboard/parent").json()["cards"][0]
    assert any("independently" in line for line in card["summary"])
    assert client_for(OTHER_PARENT).get("/api/v1/dashboard/parent").json()["cards"] == []
    assert client_for(A).get("/api/v1/dashboard/parent").status_code == 403


def test_teacher_heatmap_assign_csv_and_cross_tenant():
    consent(A)
    consent(A, "school_sharing")
    room = _classroom(students=(A, B))
    store.insert("error_tokens", {"student_id": A, "concept_id": "m8_linear_one", "token": "E07", "status": "active", "created_at": store.now_iso()})
    store.insert("error_tokens", {"student_id": B, "concept_id": "m8_linear_one", "token": "E07", "status": "active", "created_at": store.now_iso()})
    store.insert("learner_bkt_state", {"student_id": A, "skill_id": "m8_linear_one", "p_l": .5, "tier": 1})
    c = _teacher_client()
    heat = c.get(f"/api/v1/dashboard/teacher/{room}/heatmap").json()
    assert heat["token_totals"]["E07"] == 1 and heat["hidden_without_consent"] == 1
    assert c.post(f"/api/v1/dashboard/teacher/{room}/assign", json={"concept_id": "m8_linear_one"}).json()["assigned_count"] == 1
    assert A in c.get(f"/api/v1/dashboard/teacher/{room}/export.csv").text
    other = _teacher_client(OTHER_TEACHER)
    for call in (other.get(f"/api/v1/dashboard/teacher/{room}/heatmap"),
                 other.post(f"/api/v1/dashboard/teacher/{room}/assign", json={"concept_id": "m8_linear_one"}),
                 other.get(f"/api/v1/dashboard/teacher/{room}/export.csv")):
        assert call.status_code == 404
    assert client_for(A).get(f"/api/v1/dashboard/teacher/{room}/heatmap").status_code == 403


def test_csv_formula_injection_neutralized():
    from app.modules.reporting.dashboards import _csv_safe
    assert _csv_safe("=HYPERLINK(1)") == "'=HYPERLINK(1)"
    assert _csv_safe(0.5) == 0.5


def test_creator_links_analytics_and_isolation():
    c = client_for(CREATOR)
    link = c.post("/api/v1/creator/links", json={"concept_id": "m10_quadratic", "campaign": "quad-1"}).json()
    assert "utm_campaign=quad-1" in link["url"]
    anon = TestClient(app)
    app.dependency_overrides.clear()
    assert anon.post("/api/v1/creator/track", json={"code": link["code"], "event": "click"}).json()["recorded"]
    assert anon.post("/api/v1/creator/track", json={"code": "nope", "event": "click"}).json()["recorded"] is False
    data = client_for(CREATOR).get("/api/v1/dashboard/creator").json()
    assert data["links"][0]["counts"]["click"] == 1
    assert client_for(A).get("/api/v1/dashboard/creator").status_code == 403


def test_cross_student_session_idor_matrix():
    consent(A)
    consent(B)
    a = client_for(A)
    practice = a.post("/api/v1/practice/start", json={"concept_id": "m8_linear_one"}).json()
    diag = a.post("/api/v1/diagnostics/start", json={"subject": "Mathematics"}).json()
    tutor_session = ask(a, "quiz", mode="06_quiz", concept_id="m8_linear_one")["payload"]["session_id"]
    item = get_item(practice["next"]["item"]["item_id"])
    b = client_for(B)
    assert _answer(b, practice["session_id"], item.item_id, item.answer).status_code == 404
    assert b.post(f"/api/v1/practice/{practice['session_id']}/intervention-complete").status_code == 404
    assert b.post(f"/api/v1/diagnostics/{diag['session_id']}/answer", json={"item_id": diag["item"]["item_id"], "response": "1"}).status_code == 404
    assert b.post("/api/v1/tutor/ask", json={"message": "x", "session_id": tutor_session}).status_code == 404


def test_all_v1_routes_require_authentication():
    app.dependency_overrides.clear()
    client = TestClient(app)
    public = {"/api/v1/auth/pkce/verify", "/api/v1/creator/track"}
    for route in v1_routes():
        if route.path in public:
            continue
        url = route.path.replace("{session_id}", "x").replace("{quest_id}", "x").replace("{classroom_id}", "x")
        method = next(iter(route.methods))
        assert client.request(method, url, json={}).status_code == 401, route.path


def v1_routes():
    return [r for r in app.routes if getattr(r, "path", "").startswith("/api/v1/")]
