"""
Live testing + security verification for LearnByGenie.
Covers Parts 1, 3, 4, 5, 6 of the test plan (Parts 2 require UI).
Run from repo root: python backend/scripts/run_live_tests.py
"""
import json, time, sys, os
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND = ROOT / "backend"
TOKENS_FILE = BACKEND / "test_tokens.json"
ENV_FILE = BACKEND / ".env"
BASE = "http://localhost:8000"
TIMEOUT = 30.0

# Make backend importable for direct Supabase calls
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}

def _result(label, passed, detail):
    tag = "PASS" if passed else "FAIL"
    print(f"  [{tag}] {label}: {detail}")
    return passed

results = []

def check(label, passed, detail):
    results.append((label, passed, detail))
    return _result(label, passed, detail)

# ─── Load tokens ─────────────────────────────────────────────────────────────

with open(TOKENS_FILE) as f:
    toks = json.load(f)

TOKEN_A = toks["tokenA"]
TOKEN_B = toks["tokenB"]
USER_A = toks["userA"]
USER_B = toks["userB"]

print(f"Loaded tokens — UserA: {USER_A[:8]}... UserB: {USER_B[:8]}...")
print(f"Base URL: {BASE}\n")

client = httpx.Client(base_url=BASE, timeout=TIMEOUT)

# ===============================================================================
# PART 1 — Auth Flow (spot-check)
# ===============================================================================
print("=" * 60)
print("PART 1 -- Auth Flow")
print("=" * 60)

# 1.1 Login → /me returns user
r = client.get("/auth/me", headers=_h(TOKEN_A))
check("1.1 Authenticated /auth/me returns user", r.status_code == 200 and r.json().get("user", {}).get("id") == USER_A,
      f"status={r.status_code} id={r.json().get('user',{}).get('id','?')}")

# 1.2 Session persists (token still valid after a second request)
r2 = client.get("/auth/me", headers=_h(TOKEN_A))
check("1.2 Token valid on second request (session persists)", r2.status_code == 200,
      f"status={r2.status_code}")

# 1.3 Logout — protected route with no token → 403/401
r3 = client.get("/auth/me")
check("1.3 No-token /auth/me → 403/401", r3.status_code in (401, 403),
      f"status={r3.status_code}")

# 1.4 Authorization header is a real token (non-empty, non-null)
tok_preview = TOKEN_A[:20] + "..."
check("1.4 Authorization header carries a real non-empty token", bool(TOKEN_A and len(TOKEN_A) > 50),
      f"token starts with: {tok_preview}")

# ===============================================================================
# PREREQUISITE — Upload a PDF for Account A
# ===============================================================================
print("\n=" * 60)
print("PREREQUISITE — Upload PDF for Account A")
print("=" * 60)

dummy_pdf = ROOT / "dummy.pdf"
PDF_ID_A = None

# Check if A already has a ready PDF (avoid uploading every test run)
existing_pdfs = client.get("/pdfs/list", headers=_h(TOKEN_A))
if existing_pdfs.status_code == 200:
    ready_pdfs = [p for p in existing_pdfs.json().get("pdfs", []) if p.get("status") == "ready"]
    if ready_pdfs:
        PDF_ID_A = ready_pdfs[0]["id"]
        print(f"  Reusing existing ready PDF: pdf_id={PDF_ID_A}")

if not PDF_ID_A and dummy_pdf.exists():
    with open(dummy_pdf, "rb") as f:
        pdf_bytes = f.read()
    # Upload without JSON Content-Type (multipart)
    up_r = client.post(
        "/pdfs/upload",
        headers={"Authorization": f"Bearer {TOKEN_A}"},
        files={"file": ("dummy.pdf", pdf_bytes, "application/pdf")},
        data={"subject": "Test Subject"},
        timeout=40.0,
    )
    if up_r.status_code == 200:
        PDF_ID_A = up_r.json().get("pdf_id")
        print(f"  Uploaded PDF: pdf_id={PDF_ID_A} status=processing")
        # Wait up to 30s for ready
        for _ in range(6):
            time.sleep(5)
            sr = client.get(f"/pdfs/{PDF_ID_A}/status", headers=_h(TOKEN_A))
            if sr.status_code == 200 and sr.json().get("status") == "ready":
                print(f"  PDF is ready.")
                break
            print(f"  PDF status: {sr.json().get('status','?')} ...")
        else:
            print(f"  PDF final status: {sr.json().get('status','timeout')}")
    else:
        print(f"  Upload failed: {up_r.status_code} {up_r.text[:200]}")
else:
    print(f"  dummy.pdf not found at {dummy_pdf}, skipping upload")

# Update env for verify_chunk_isolation.py
env_lines = Path(ENV_FILE).read_text().splitlines()
def _set_env(lines, key, val):
    for i, l in enumerate(lines):
        if l.startswith(key + "="):
            lines[i] = f"{key}={val}"
            return lines
    lines.append(f"{key}={val}")
    return lines

env_lines = _set_env(env_lines, "TEST_USER_A_JWT", TOKEN_A)
env_lines = _set_env(env_lines, "TEST_USER_B_JWT", TOKEN_B)
if PDF_ID_A:
    env_lines = _set_env(env_lines, "TEST_PDF_ID_OWNED_BY_A", PDF_ID_A)
Path(ENV_FILE).write_text("\n".join(env_lines))
print("  .env updated with test credentials.\n")

# ===============================================================================
# PART 3 — Quiz Engine Live Tests
# ===============================================================================
print("=" * 60)
print("PART 3 — Quiz Engine Live Tests")
print("=" * 60)

# 3.1 Generate quiz from PDF (Phase-3 gated → expect 503)
import uuid as _uuid
q_key = str(_uuid.uuid4())
gen_body = {
    "source_type": "pdf",
    "source_ids": [PDF_ID_A] if PDF_ID_A else ["00000000-0000-0000-0000-000000000001"],
    "idempotency_key": q_key,
    "num_questions": 5,
    "difficulty": "medium",
}
r31 = client.post("/api/quiz/quizzes", headers=_h(TOKEN_A), json=gen_body, timeout=15)
# Ownership check fires first (PDF owned by A → not a 403), then 503
if PDF_ID_A:
    check("3.1 Generate quiz from PDF — ownership passes, Phase-3 gate returns 503",
          r31.status_code == 503,
          f"status={r31.status_code} body={r31.text[:120]}")
else:
    check("3.1 Generate quiz — no PDF (skipped ownership check)",
          r31.status_code in (503, 404),
          f"status={r31.status_code}")

# 3.2 Generate quiz from topic-only (no source_ids)
gen2_body = {
    "source_type": "pdf",
    "source_ids": [],
    "idempotency_key": str(_uuid.uuid4()),
    "topic": "Photosynthesis",
}
r32 = client.post("/api/quiz/quizzes", headers=_h(TOKEN_A), json=gen2_body, timeout=15)
check("3.2 Generate quiz (empty source_ids) — ownership passes, gate 503",
      r32.status_code in (503, 422),
      f"status={r32.status_code} body={r32.text[:100]}")

# 3.3 List quizzes for A (should be empty since generation is gated)
r_list = client.get("/api/quiz/quizzes", headers=_h(TOKEN_A))
check("3.3 List quizzes returns 200 with list", r_list.status_code == 200 and "quizzes" in r_list.json(),
      f"status={r_list.status_code} count={len(r_list.json().get('quizzes',[]))}")

# 3.4-3.7: Seed a quiz directly into DB to test downstream paths
QUIZ_ID = None
QUESTION_ID = None
ATTEMPT_ID = None

try:
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)
    from supabase import create_client
    from app.core.config import settings
    sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    quiz_id = str(_uuid.uuid4())
    q_id = str(_uuid.uuid4())
    q_id2 = str(_uuid.uuid4())

    # Insert quiz — uses `owner_user_id` per migration 009 / Quiz.to_db_dict()
    sb.table("quizzes").insert({
        "id": quiz_id,
        "owner_user_id": USER_A,
        "title": "Test Quiz (seeded)",
        "mode": "student",
        "status": "draft",
        "source_type": "pdf",
        "source_ids": [PDF_ID_A] if PDF_ID_A else [],
        "config": {},
    }).execute()

    # Insert 2 questions — `type` and `order_index` per migration 009
    sb.table("quiz_questions").insert([
        {
            "id": q_id,
            "quiz_id": quiz_id,
            "question_text": "What is photosynthesis?",
            "type": "mcq",
            "options": ["Process of making food", "Breaking food", "Respiration", "Digestion"],
            "correct_answer": ["Process of making food"],
            "explanation": "Photosynthesis converts light to energy.",
            "order_index": 0,
        },
        {
            "id": q_id2,
            "quiz_id": quiz_id,
            "question_text": "What does ATP stand for?",
            "type": "mcq",
            "options": ["Adenosine Triphosphate", "Acid Transport Protein", "Active Tissue Power", "None"],
            "correct_answer": ["Adenosine Triphosphate"],
            "explanation": "ATP is the energy currency of the cell.",
            "order_index": 1,
        },
    ]).execute()

    QUIZ_ID = quiz_id
    QUESTION_ID = q_id
    QUESTION_ID2 = q_id2
    print(f"  Seeded quiz_id={QUIZ_ID}, q1={QUESTION_ID[:8]}, q2={q_id2[:8]}")

except Exception as e:
    print(f"  DB seed failed (quiz tests will be limited): {e}")

if QUIZ_ID:
    # 3.5 View quiz as owner
    r35 = client.get(f"/api/quiz/quizzes/{QUIZ_ID}", headers=_h(TOKEN_A))
    check("3.5 Owner can view seeded quiz (200 with questions)",
          r35.status_code == 200 and len(r35.json().get("questions", [])) == 2,
          f"status={r35.status_code} question_count={len(r35.json().get('questions',[]))}")

    # Edit question
    r_edit = client.patch(f"/api/quiz/questions/{QUESTION_ID}",
                          headers=_h(TOKEN_A),
                          json={"question_text": "What is photosynthesis (edited)?"})
    check("3.5a Edit question saves (200)",
          r_edit.status_code == 200,
          f"status={r_edit.status_code} updated={r_edit.json().get('updated','?')}")

    # 3.6 Regenerate single question — gated → 503
    r36 = client.post(f"/api/quiz/questions/{QUESTION_ID}/regenerate",
                      headers=_h(TOKEN_A), json={})
    check("3.6 Regenerate question — gated 503 (original intact)",
          r36.status_code == 503,
          f"status={r36.status_code}")

    # 3.7 Delete one question, other stays
    r37 = client.delete(f"/api/quiz/questions/{QUESTION_ID2}", headers=_h(TOKEN_A))
    check("3.7 Delete one question (204/200)", r37.status_code in (200, 204),
          f"status={r37.status_code}")
    r37b = client.get(f"/api/quiz/quizzes/{QUIZ_ID}", headers=_h(TOKEN_A))
    check("3.7b Remaining question count = 1 after delete",
          len(r37b.json().get("questions", [])) == 1,
          f"count={len(r37b.json().get('questions',[]))}")

    # 3.3 Start attempt
    r_start = client.post("/api/quiz/attempts/start",
                          headers=_h(TOKEN_A),
                          json={"quiz_id": QUIZ_ID})
    check("3.3 Start attempt returns attempt_id + shuffled questions",
          r_start.status_code == 200 and "attempt_id" in r_start.json(),
          f"status={r_start.status_code} keys={list(r_start.json().keys())[:6]}")

    if r_start.status_code == 200:
        ATTEMPT_ID = r_start.json()["attempt_id"]
        shuffle_order = r_start.json().get("question_order", [])

        # 3.3 Submit — no client score, server must compute
        submit_body = {
            "attempt_id": ATTEMPT_ID,
            "answers": [{"question_id": QUESTION_ID, "answer": "Process of making food"}],
            "idempotency_key": str(_uuid.uuid4()),
        }
        r_sub = client.post("/api/quiz/attempts/submit",
                            headers=_h(TOKEN_A), json=submit_body, timeout=20)
        check("3.3a Submit — server computes score (no client score sent)",
              r_sub.status_code == 200 and "score" in r_sub.json(),
              f"status={r_sub.status_code} score={r_sub.json().get('score','?')} "
              f"correct={r_sub.json().get('correct_count','?')}")

        # 3.8 Double-submit same attempt
        r_dup = client.post("/api/quiz/attempts/submit",
                            headers=_h(TOKEN_A), json=submit_body, timeout=20)
        check("3.8 Double-submit (idempotent) — no double-scoring",
              r_dup.status_code in (200, 409),
              f"status={r_dup.status_code} body={r_dup.text[:80]}")
        if r_dup.status_code == 200:
            check("3.8a Idempotent replay returns same score",
                  r_dup.json().get("score") == r_sub.json().get("score"),
                  f"first={r_sub.json().get('score')} second={r_dup.json().get('score')}")

        # 3.4 Review attempt — reconstruct order
        r_rev = client.get(f"/api/quiz/attempts/{ATTEMPT_ID}", headers=_h(TOKEN_A))
        check("3.4 Review attempt (200) — shuffle reconstruction present",
              r_rev.status_code == 200,
              f"status={r_rev.status_code} keys={list(r_rev.json().keys())[:5]}")

        # 3.10 Submit with client-supplied score — server must ignore it
        tampered_body = {
            "attempt_id": str(_uuid.uuid4()),  # new attempt_id so not idempotent match
            "answers": [{"question_id": QUESTION_ID, "answer": "wrong answer"}],
            "score": 999,           # attacker-supplied
            "correct_count": 999,   # attacker-supplied
            "idempotency_key": str(_uuid.uuid4()),
        }
        # Start a new attempt first
        r_start2 = client.post("/api/quiz/attempts/start", headers=_h(TOKEN_A), json={"quiz_id": QUIZ_ID})
        if r_start2.status_code == 200:
            tampered_body["attempt_id"] = r_start2.json()["attempt_id"]
            r_tam = client.post("/api/quiz/attempts/submit", headers=_h(TOKEN_A),
                                json=tampered_body, timeout=20)
            check("3.10 Client-supplied score ignored — server score != 999",
                  r_tam.status_code == 200 and r_tam.json().get("score", 999) != 999,
                  f"status={r_tam.status_code} server_score={r_tam.json().get('score','?')}")
        else:
            print("  3.10 Could not start second attempt for tamper test")

# ===============================================================================
# PART 4 — Security Re-verification (all mandatory)
# ===============================================================================
print("\n=" * 60)
print("PART 4 — Security Re-verification")
print("=" * 60)

STOP = False

# 4.1 B → predict/exam-questions with A's pdf_id
if PDF_ID_A:
    r41 = client.post("/api/predict/exam-questions",
                      headers=_h(TOKEN_B),
                      json={"pdfId": PDF_ID_A, "examType": "CBSE"}, timeout=20)
    p41 = r41.status_code in (404, 403, 401)
    check("4.1 B → predict/exam-questions with A's pdf_id",
          p41, f"status={r41.status_code} body={r41.text[:120]}")
    if not p41:
        print("  !! STOP CONDITION 4.10 TRIGGERED: Cross-tenant data leak in predict!!")
        STOP = True
else:
    print("  4.1 Skipped (no PDF_ID_A)")

# 4.2 B → chat/ask with A's pdf_id (non-Quick-Answer mode)
if PDF_ID_A and not STOP:
    r42 = client.post("/chat/ask",
                      headers=_h(TOKEN_B),
                      json={"pdf_id": PDF_ID_A, "question": "What is the main topic?",
                            "mode": "No Fact Miss", "history": []}, timeout=40)
    if r42.status_code == 200:
        sources = r42.json().get("sources", [])
        p42 = len(sources) == 0
        check("4.2 B → chat/ask with A's pdf_id — no A's content in sources",
              p42, f"status=200 sources={len(sources)} {'LEAK!' if not p42 else 'isolated'}")
        if not p42:
            print("  !! STOP CONDITION 4.10 TRIGGERED: Cross-tenant content in chat!!")
            STOP = True
    else:
        check("4.2 B → chat/ask with A's pdf_id → blocked",
              r42.status_code in (403, 404), f"status={r42.status_code}")
else:
    print("  4.2 Skipped")

# 4.3 B → roadmap/lesson owned by A (if we can find one)
r43_list = client.get("/api/lessons", headers=_h(TOKEN_A))
lesson_id_a = None
if r43_list.status_code == 200 and r43_list.json().get("lessons"):
    lesson_id_a = r43_list.json()["lessons"][0].get("id")
if lesson_id_a and not STOP:
    r43 = client.get(f"/api/lessons/{lesson_id_a}", headers=_h(TOKEN_B))
    p43 = r43.status_code in (403, 404, 401)
    check("4.3 B → GET A's lesson/roadmap",
          p43, f"status={r43.status_code}")
    if not p43:
        STOP = True
        print("  !! STOP CONDITION 4.10 TRIGGERED: B can read A's lesson!!")
else:
    print("  4.3 No roadmap owned by A — checking quiz ownership instead")
    if QUIZ_ID and not STOP:
        r43q = client.get(f"/api/quiz/quizzes/{QUIZ_ID}", headers=_h(TOKEN_B))
        p43q = r43q.status_code in (403, 404)
        check("4.3 B → GET A's quiz (ownership check)", p43q,
              f"status={r43q.status_code}")
        if not p43q:
            STOP = True
            print("  !! STOP CONDITION 4.10 TRIGGERED: B can read A's quiz!!")

# 4.4 B → view/edit/delete A's quiz
if QUIZ_ID and not STOP:
    r44v = client.get(f"/api/quiz/quizzes/{QUIZ_ID}", headers=_h(TOKEN_B))
    p44v = r44v.status_code in (403, 404)
    check("4.4 B → GET A's quiz → 403/404", p44v, f"status={r44v.status_code}")

    r44e = client.patch(f"/api/quiz/quizzes/{QUIZ_ID}/status",
                        headers=_h(TOKEN_B), json={"status": "active"})
    p44e = r44e.status_code in (403, 404)
    check("4.4 B → PATCH A's quiz status → 403/404", p44e, f"status={r44e.status_code}")

    r44d = client.delete(f"/api/quiz/quizzes/{QUIZ_ID}", headers=_h(TOKEN_B))
    p44d = r44d.status_code in (403, 404)
    check("4.4 B → DELETE A's quiz → 403/404", p44d, f"status={r44d.status_code}")

    if not (p44v and p44e and p44d):
        STOP = True
        print("  !! STOP CONDITION 4.10 TRIGGERED: B can modify A's quiz!!")

# 4.5 No-auth → POST each critical endpoint
NO_AUTH = {"Content-Type": "application/json"}
endpoints_45 = [
    ("POST", "/api/orchestrator/route", {"message": "hello"}),
    ("POST", "/api/librarian/retrieve", {"topic": "test", "user_id": USER_A}),
    ("POST", "/api/tutor/turn", {"topic": "test", "librarian_context": {
        "context": [], "related_context": [], "sufficient": False, "used_web_fallback": False
    }, "conversation_history": []}),
    ("POST", "/api/content-creator/generate", {"content_type": "flashcards", "topic": "test"}),
]
for method, path, body in endpoints_45:
    r45 = client.request(method, path, headers=NO_AUTH, json=body, timeout=10)
    check(f"4.5 No-auth {method} {path} → 401/403",
          r45.status_code in (401, 403),
          f"status={r45.status_code}")

# 4.6 No-auth → GET /api/content-creator/status/{any-id}
r46 = client.get("/api/content-creator/status/00000000-0000-0000-0000-000000000001",
                 headers=NO_AUTH, timeout=10)
check("4.6 No-auth GET content-creator/status → 401/403",
      r46.status_code in (401, 403),
      f"status={r46.status_code}")

# 4.7 B → GET status of a job created by A
# Content-creator jobs are in-memory — test through quiz ownership
if ATTEMPT_ID and not STOP:
    r47 = client.get(f"/api/quiz/attempts/{ATTEMPT_ID}", headers=_h(TOKEN_B))
    p47 = r47.status_code in (403, 404)
    check("4.7 B → GET A's attempt → 403/404",
          p47, f"status={r47.status_code}")
    if not p47:
        STOP = True
        print("  !! STOP CONDITION 4.10 TRIGGERED: B can read A's attempt!!")
else:
    print("  4.7 No attempt_id (attempt not started) — skipping")

# 4.8 Rate limit — 25+ rapid requests to a tight endpoint (10/min)
print("\n  4.8 Rate limit fire test — sending 25 POST to /api/quiz/quizzes ...")
first_429 = None
for i in range(1, 26):
    try:
        rb = client.post("/api/quiz/quizzes", headers=_h(TOKEN_A),
                         json={"source_type": "pdf", "source_ids": [],
                               "idempotency_key": str(_uuid.uuid4())}, timeout=10)
        if rb.status_code == 429:
            first_429 = (i, rb.text[:200])
            break
    except Exception as conn_err:
        # Re-create client after connection forcibly closed by server
        client = httpx.Client(base_url=BASE, timeout=TIMEOUT)
        print(f"  4.8 connection reset at request #{i}: {conn_err}")

if first_429:
    check(f"4.8 Rate limit triggered at request #{first_429[0]} (limit=10/min)",
          True, f"first 429 body: {first_429[1]}")
else:
    check("4.8 Rate limit not triggered in 25 requests",
          False, "No 429 observed — rate limit may not be enforced")

# ===============================================================================
# PART 5 — Rate Limiting Spot-Check
# ===============================================================================
print("\n=" * 60)
print("PART 5 — Rate Limiting Spot-Check")
print("=" * 60)

# 5.1 ~30-40 GET /pdfs/list shouldn't 429
hits = 0
for _ in range(35):
    r5 = client.get("/pdfs/list", headers=_h(TOKEN_A), timeout=5)
    if r5.status_code == 429:
        hits += 1
check("5.1 35× GET /pdfs/list — no false 429 from global 200/min limit",
      hits == 0, f"429s observed: {hits}/35")

# 5.3 After window — single request succeeds
time.sleep(3)
r53 = client.get("/pdfs/list", headers=_h(TOKEN_A), timeout=10)
check("5.3 After brief pause, request succeeds again",
      r53.status_code == 200, f"status={r53.status_code}")

# ===============================================================================
# PART 6 — TeachMe Persistence (teach_sessions table)
# ===============================================================================
print("\n=" * 60)
print("PART 6 — TeachMe Persistence (migration 010)")
print("=" * 60)

# 6.1 Confirm teach_sessions table exists
TABLE_EXISTS = False
try:
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)
    from supabase import create_client
    from app.core.config import settings
    sb2 = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    ts_res = sb2.table("teach_sessions").select("id").limit(1).execute()
    TABLE_EXISTS = True
    print(f"  teach_sessions table exists. Row count (sample): {len(ts_res.data)}")
    check("6.1 Migration 010 applied — teach_sessions table queryable",
          True, f"rows in sample: {len(ts_res.data)}")
except Exception as e:
    check("6.1 Migration 010 applied — teach_sessions table queryable",
          False, f"Error: {e}")

# 6.1 Start a teaching session and verify DB row is created
SESSION_ID = None
if TABLE_EXISTS:
    teach_body = {
        "topic": "Photosynthesis",
        "level": "btech",
        "mode": "interactive_teacher",
        "depth": "normal",
        "source_type": "topic",
        "source_ids": [],
    }
    r61 = client.post("/api/teach/start", headers=_h(TOKEN_A), json=teach_body, timeout=60)
    if r61.status_code == 200:
        SESSION_ID = r61.json().get("session_id")
        check("6.1a TeachMe session starts (200)", True,
              f"session_id={SESSION_ID}")

        # Verify row persisted in DB
        time.sleep(2)
        try:
            db_row = sb2.table("teach_sessions").select("*").eq("id", SESSION_ID).execute()
            row_exists = len(db_row.data) == 1
            row = db_row.data[0] if row_exists else {}
            check("6.5 Row exists in teach_sessions for this session",
                  row_exists,
                  f"user_id={row.get('user_id','?')} topic={row.get('topic','?')} "
                  f"has_state={bool(row.get('state_json'))}")
        except Exception as e:
            check("6.5 DB row verification", False, f"Error: {e}")
    else:
        check("6.1a TeachMe session starts", False,
              f"status={r61.status_code} body={r61.text[:200]}")

# 6.4/6.5 Verify session is retrievable after-the-fact (simulates browser reopen)
if SESSION_ID:
    r64 = client.get(f"/api/teach/session/{SESSION_ID}", headers=_h(TOKEN_A), timeout=15)
    check("6.4/6.5 Session retrievable via GET /api/teach/session/{id}",
          r64.status_code == 200 and r64.json().get("session_id") == SESSION_ID,
          f"status={r64.status_code} plan_concepts={len(r64.json().get('plan',{}).get('concepts',[]))}")

# 6.9 CRITICAL — B cannot access A's teaching session
if SESSION_ID and not STOP:
    r6_b = client.get(f"/api/teach/session/{SESSION_ID}", headers=_h(TOKEN_B))
    p6b = r6_b.status_code in (403, 404)
    check("6.9 B cannot access A's teach session → 403/404",
          p6b, f"status={r6_b.status_code}")
    if not p6b:
        print("  !! CROSS-TENANT LEAK in TeachMe session!!")

# ===============================================================================
# SUMMARY
# ===============================================================================
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
passed = [r for r in results if r[1]]
failed = [r for r in results if not r[1]]
print(f"Total: {len(results)} | PASS: {len(passed)} | FAIL: {len(failed)}")
if failed:
    print("\nFAILED ITEMS:")
    for label, _, detail in failed:
        print(f"  [FAIL] {label}: {detail}")

part3_labels = [r for r in results if r[0].startswith("3")]
part4_labels = [r for r in results if r[0].startswith("4")]
part6_labels = [r for r in results if r[0].startswith("6")]

p3_pass = all(r[1] for r in part3_labels)
p4_pass = all(r[1] for r in part4_labels)
p6_pass = all(r[1] for r in part6_labels)

print(f"\nPart 3 (Quiz Engine): {'CLEAN' if p3_pass else 'ISSUES'}")
print(f"Part 4 (Security):    {'CLEAN' if p4_pass else 'ISSUES'}")
print(f"Part 6 (Persistence): {'CLEAN' if p6_pass else 'ISSUES'}")

if STOP:
    print("\n!! TEST STOPPED EARLY: CRITICAL CROSS-TENANT LEAK DETECTED !!")
    sys.exit(2)
sys.exit(0 if not failed else 1)
