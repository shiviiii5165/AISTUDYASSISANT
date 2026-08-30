"""
Cross-tenant chunk-isolation verification.

Verifies the two get_all_chunks / get_top_chunks data-isolation fixes end-to-end
against a running API + live Supabase:

  - /api/predict/exam-questions   (fix #2b — get_top_chunks RPC, migration 007)
  - /chat/ask in a non-Quick-Answer mode (fix #2a — vector_store.get_all_chunks)

For each, it confirms the owner still gets their own content (positive path) and
that a second user is blocked from the same pdf_id (isolation path).

Exit code 0 = all assertions passed. Non-zero = a fix regressed or setup is
missing. Safe to wire into CI once the two test accounts exist.

Config is read from backend/.env. NO credential value is ever printed.

Required in backend/.env:
  TEACHGENIE_API_BASE      Base URL of the running API (default http://localhost:8000)
  TEST_USER_A_JWT          A valid Supabase access token (JWT) for test user A
  TEST_USER_B_JWT          A valid Supabase access token (JWT) for test user B
  TEST_PDF_ID_OWNED_BY_A   id of a PDF uploaded & fully processed under user A
"""

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load backend/.env explicitly (this file lives in backend/scripts/).
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)

# A non-Quick-Answer mode forces the global path through get_all_chunks (fix #2a).
GLOBAL_MODE = "No Fact Miss"
# LLM-backed endpoints can be slow; give them room without hanging forever.
HTTP_TIMEOUT = 120.0


def _fail_setup(missing: list[str]) -> None:
    """Explain exactly what to create, then exit non-zero (setup, not a regression)."""
    print("SETUP REQUIRED - cannot run the isolation checks yet.\n")
    print(f"backend/.env (at {ENV_PATH}) is missing: {', '.join(missing)}\n")
    print("This test needs TWO real Supabase auth users and one processed PDF:")
    print("  1. Create two auth users in Supabase (Dashboard -> Authentication -> Add user),")
    print("     e.g. tester-a@example.com and tester-b@example.com.")
    print("  2. Obtain a current access token (JWT) for each — sign in via the app or")
    print("     POST /auth/login with each user's credentials, copy session.access_token.")
    print("     Note: JWTs expire; regenerate if the script later returns 401.")
    print("  3. As user A, upload a PDF via POST /pdfs/upload and wait until its status is")
    print("     'ready' (chunks embedded). Note its pdf_id.")
    print("  4. Add these lines to backend/.env (values only, never commit real tokens):")
    print("       TEACHGENIE_API_BASE=https://<your-api-host>   # or http://localhost:8000")
    print("       TEST_USER_A_JWT=<user A access token>")
    print("       TEST_USER_B_JWT=<user B access token>")
    print("       TEST_PDF_ID_OWNED_BY_A=<pdf_id owned by user A>")
    sys.exit(2)


def _load_config() -> dict:
    cfg = {
        "base": os.environ.get("TEACHGENIE_API_BASE", "http://localhost:8000").rstrip("/"),
        "jwt_a": os.environ.get("TEST_USER_A_JWT"),
        "jwt_b": os.environ.get("TEST_USER_B_JWT"),
        "pdf_id": os.environ.get("TEST_PDF_ID_OWNED_BY_A"),
    }
    missing = [
        name for name, key in (
            ("TEST_USER_A_JWT", "jwt_a"),
            ("TEST_USER_B_JWT", "jwt_b"),
            ("TEST_PDF_ID_OWNED_BY_A", "pdf_id"),
        )
        if not cfg[key]
    ]
    if missing:
        _fail_setup(missing)
    # Confirm presence only — never echo the values themselves.
    print(f"Config loaded from backend/.env (API base: {cfg['base']})")
    print("Credentials present: TEST_USER_A_JWT=yes, TEST_USER_B_JWT=yes, TEST_PDF_ID_OWNED_BY_A=yes\n")
    return cfg


def _auth(jwt: str) -> dict:
    return {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}


# ─── Individual checks ───────────────────────────────────────────────────────
# Each returns (passed: bool, detail: str). No token or pdf_id is included in detail.

def check_predict_owner(client: httpx.Client, cfg: dict) -> tuple[bool, str]:
    r = client.post(
        f"{cfg['base']}/api/predict/exam-questions",
        headers=_auth(cfg["jwt_a"]),
        json={"pdfId": cfg["pdf_id"], "examType": "CBSE"},
    )
    if r.status_code != 200:
        return False, f"expected 200, got {r.status_code} (body: {r.text[:200]})"
    try:
        preds = r.json().get("predictions")
    except Exception as e:
        return False, f"200 but response was not JSON: {e}"
    if not isinstance(preds, list) or len(preds) == 0:
        return False, "200 but 'predictions' was missing/empty — owner should see real predictions"
    return True, f"200 with {len(preds)} predictions"


def check_predict_isolation(client: httpx.Client, cfg: dict) -> tuple[bool, str]:
    r = client.post(
        f"{cfg['base']}/api/predict/exam-questions",
        headers=_auth(cfg["jwt_b"]),
        json={"pdfId": cfg["pdf_id"], "examType": "CBSE"},
    )
    if r.status_code == 200:
        return False, "user B got 200 for user A's pdf_id — CROSS-TENANT LEAK (migration 007 applied?)"
    if r.status_code != 404:
        return False, f"expected 404 (no rows for non-owner), got {r.status_code} (body: {r.text[:200]})"
    return True, "404 — non-owner correctly blocked"


def check_chat_owner(client: httpx.Client, cfg: dict) -> tuple[bool, str]:
    r = client.post(
        f"{cfg['base']}/chat/ask",
        headers=_auth(cfg["jwt_a"]),
        json={"pdf_id": cfg["pdf_id"], "question": "Summarize the key facts.",
              "mode": GLOBAL_MODE, "history": []},
    )
    if r.status_code != 200:
        return False, f"expected 200, got {r.status_code} (body: {r.text[:200]})"
    body = r.json()
    if not body.get("sources"):
        return False, "200 but no sources — owner should retrieve their own chunks in a global mode"
    return True, f"200 with {len(body['sources'])} source(s)"


def check_chat_isolation(client: httpx.Client, cfg: dict) -> tuple[bool, str]:
    r = client.post(
        f"{cfg['base']}/chat/ask",
        headers=_auth(cfg["jwt_b"]),
        json={"pdf_id": cfg["pdf_id"], "question": "Summarize the key facts.",
              "mode": GLOBAL_MODE, "history": []},
    )
    # After the fix, get_all_chunks returns [] for a non-owner, so the endpoint
    # answers 200 with the empty-content sentinel and NO sources. The isolation
    # property is: user B never receives user A's actual chunk content.
    if r.status_code != 200:
        # A 404/403 would also satisfy isolation, but flag the shape change.
        return True, f"non-owner blocked via status {r.status_code} (still isolated)"
    body = r.json()
    if body.get("sources"):
        return False, "user B received sources for user A's pdf — CROSS-TENANT LEAK in get_all_chunks"
    return True, "200 with empty sources — non-owner sees no content"


CHECKS = [
    ("predict / owner sees own predictions", check_predict_owner),
    ("predict / non-owner blocked (404)", check_predict_isolation),
    ("chat global-mode / owner sees own content", check_chat_owner),
    ("chat global-mode / non-owner blocked", check_chat_isolation),
]


def main() -> None:
    cfg = _load_config()
    failures = 0
    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        for label, fn in CHECKS:
            try:
                passed, detail = fn(client, cfg)
            except httpx.HTTPError as e:
                passed, detail = False, f"request error: {e}"
            status = "PASS" if passed else "FAIL"
            print(f"[{status}] {label}: {detail}")
            if not passed:
                failures += 1

    print()
    if failures:
        print(f"RESULT: {failures} of {len(CHECKS)} checks FAILED — isolation not verified.")
        sys.exit(1)
    print(f"RESULT: all {len(CHECKS)} checks passed — chunk isolation verified.")
    sys.exit(0)


if __name__ == "__main__":
    main()
