#!/usr/bin/env python3
"""
LOCAL DEVELOPMENT TOOL ONLY
===============================================================
Deletes old test accounts and creates two pre-verified ones.

Hardcoded target accounts (throwaway local test credentials):
  testing1234@gmail.com / 12345test
  testing5678@gmail.com / 12345test

Old accounts cleaned up:
  test-a@teachgenie.local
  test-b@teachgenie.local
  test-account-a@teachgenie.test
  test-account-b@teachgenie.test

Reads SUPABASE_URL + SUPABASE_KEY from backend/.env (service-role key).
===============================================================
"""

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Load .env
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent
for candidate in [BACKEND_DIR / ".env", BACKEND_DIR.parent / ".env"]:
    if candidate.exists():
        from dotenv import load_dotenv
        load_dotenv(candidate)
        break

import os
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in backend/.env")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config — hardcoded, these are throwaway test accounts
# ---------------------------------------------------------------------------
OLD_EMAILS = [
    "test-a@teachgenie.local",
    "test-b@teachgenie.local",
    "test-account-a@teachgenie.test",
    "test-account-b@teachgenie.test",
]

NEW_ACCOUNTS = [
    {"email": "testing1234@gmail.com", "password": "12345test"},
    {"email": "testing5678@gmail.com", "password": "12345test"},
]


def find_user_id_by_email(client, email: str) -> str | None:
    try:
        page = 1
        while True:
            users = client.auth.admin.list_users(page=page, per_page=1000)
            if not users:
                break
            for u in users:
                if getattr(u, "email", None) == email:
                    return u.id
            if len(users) < 1000:
                break
            page += 1
    except Exception as exc:
        print(f"  list_users error: {exc}")
    return None


def delete_old_accounts(client) -> None:
    print("\n=== Deleting old test accounts ===")
    for email in OLD_EMAILS:
        uid = find_user_id_by_email(client, email)
        if uid is None:
            print(f"  {email}: not found — skipping")
            continue
        try:
            client.auth.admin.delete_user(uid)
            print(f"  {email}: deleted (was {uid})")
        except Exception as exc:
            print(f"  {email}: delete failed — {exc}")


def create_account(client, email: str, password: str) -> str | None:
    try:
        resp = client.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
        })
        uid = resp.user.id
        print(f"  Created  user_id: {uid}")
        return uid
    except Exception as exc:
        print(f"  Create failed: {exc}")
        return None


def verify_confirmed(client, uid: str) -> bool:
    try:
        user = client.auth.admin.get_user_by_id(uid).user
        ts = user.email_confirmed_at
        if ts:
            print(f"  email_confirmed_at: {ts}  OK")
            return True
        else:
            print("  ERROR: email_confirmed_at is NOT set")
            return False
    except Exception as exc:
        print(f"  Verify fetch failed: {exc}")
        return False


def test_signin(email: str, password: str) -> bool:
    # Use a fresh client so sign_in doesn't pollute the admin client's session state.
    from supabase import create_client as _create
    anon_key = os.environ.get("VITE_SUPABASE_ANON_KEY", SUPABASE_KEY)
    signin_client = _create(SUPABASE_URL, anon_key)
    try:
        session = signin_client.auth.sign_in_with_password({"email": email, "password": password})
        token = session.session.access_token if session.session else None
        if token:
            print(f"  Sign-in OK  access_token: {token[:40]}...")
            return True
        else:
            print("  Sign-in returned no session token")
            return False
    except Exception as exc:
        print(f"  Sign-in failed: {exc}")
        return False


def main() -> None:
    from supabase import create_client
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    delete_old_accounts(client)

    results = []
    for acct in NEW_ACCOUNTS:
        email, password = acct["email"], acct["password"]
        print(f"\n=== Creating {email} ===")

        # If account already exists from a prior partial run, delete it first
        existing = find_user_id_by_email(client, email)
        if existing:
            print(f"  Already exists ({existing}) — deleting to recreate cleanly")
            try:
                client.auth.admin.delete_user(existing)
            except Exception as exc:
                print(f"  Could not delete existing: {exc}")

        uid = create_account(client, email, password)
        if uid is None:
            results.append((email, password, False))
            continue

        confirmed = verify_confirmed(client, uid)
        signed_in = test_signin(email, password)
        results.append((email, password, confirmed and signed_in))

    print("\n" + "=" * 50)
    print("FINAL CREDENTIALS")
    print("=" * 50)
    for i, (email, password, ok) in enumerate(results, 1):
        status = "WORKING" if ok else "FAILED"
        print(f"Account {i} [{status}]: {email} / {password}")
    print("=" * 50)


if __name__ == "__main__":
    main()
