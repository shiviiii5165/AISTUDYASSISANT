"""Audit helper: sign in test accounts, write test_tokens.json. Read-only wrt app."""
import os, json, sys
from pathlib import Path
BACKEND = Path(__file__).resolve().parent.parent
from dotenv import load_dotenv
load_dotenv(BACKEND / ".env")
from supabase import create_client

URL = os.environ["SUPABASE_URL"].rstrip("/")
ANON = os.environ.get("VITE_SUPABASE_ANON_KEY") or os.environ["SUPABASE_KEY"]
SERVICE = os.environ["SUPABASE_KEY"]

ACCTS = [("testing1234@gmail.com", "12345test"), ("testing5678@gmail.com", "12345test")]

def ensure_and_signin(email, pw):
    c = create_client(URL, ANON)
    try:
        s = c.auth.sign_in_with_password({"email": email, "password": pw})
        return s.session.access_token, s.user.id
    except Exception as e:
        print(f"  signin failed for {email}: {e}; trying admin-create")
        admin = create_client(URL, SERVICE)
        try:
            admin.auth.admin.create_user({"email": email, "password": pw, "email_confirm": True})
        except Exception as e2:
            print(f"  create failed: {e2}")
        s = c.auth.sign_in_with_password({"email": email, "password": pw})
        return s.session.access_token, s.user.id

ta, ua = ensure_and_signin(*ACCTS[0])
tb, ub = ensure_and_signin(*ACCTS[1])
out = {"tokenA": ta, "userA": ua, "tokenB": tb, "userB": ub}
(BACKEND / "test_tokens.json").write_text(json.dumps(out, indent=2))
print("WROTE test_tokens.json")
print(f"userA={ua} tokenA={ta[:30]}...")
print(f"userB={ub} tokenB={tb[:30]}...")
