"""Audit helper (Family 2): systematically probe every route for auth + bad-input error handling.
Fires no-auth and authenticated-bad-input requests; captures status + body snippet.
Flags raw 500s on foreseeable failures and 200s that embed an error marker."""
import json, uuid
from pathlib import Path
import httpx

BACKEND = Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8010"
toks = json.load(open(BACKEND / "test_tokens.json"))
TA = toks["tokenA"]
NONEXISTENT = "00000000-0000-0000-0000-0000000000ff"

client = httpx.Client(base_url=BASE, timeout=40.0)

d = client.get("/openapi.json").json()
routes = []
for p, methods in d["paths"].items():
    for m in methods:
        if m in ("get", "post", "put", "patch", "delete"):
            routes.append((m.upper(), p))

# Routes to skip live-firing (auth endpoints themselves / trivial root/health)
SKIP = {("POST", "/auth/login"), ("POST", "/auth/signup"), ("GET", "/"), ("GET", "/api/health")}

def fill(path):
    # replace any {param} with a nonexistent uuid
    import re
    return re.sub(r"\{[^}]+\}", NONEXISTENT, path)

def body_for(method):
    return {} if method in ("POST", "PUT", "PATCH") else None

ERR_MARKERS = ("error", "failed", "failure", "traceback", "exception")

def has_hidden_error(status, text):
    if status != 200:
        return False
    low = text.lower()
    # crude: 200 body literally signaling an error/failed status
    return any(f'"{k}"' in low for k in ("error", "traceback")) or '"status":"failed"' in low or '"status": "failed"' in low

rows = []
def fire(method, path, headers, tag):
    url = fill(path)
    try:
        r = client.request(method, url, headers=headers, json=body_for(method))
        snippet = r.text[:160].replace("\n", " ")
        rows.append((tag, method, path, r.status_code, snippet))
        return r.status_code, r.text
    except Exception as e:
        rows.append((tag, method, path, "EXC", str(e)[:150]))
        return None, str(e)

H_AUTH = {"Authorization": f"Bearer {TA}", "Content-Type": "application/json"}
H_NONE = {"Content-Type": "application/json"}

for method, path in routes:
    if (method, path) in SKIP:
        continue
    # 1) no-auth
    fire(method, path, H_NONE, "NOAUTH")
    # 2) authed bad input / nonexistent resource
    fire(method, path, H_AUTH, "AUTH-BAD")

# ---- Analysis ----
print(f"{'TAG':<9}{'M':<7}{'PATH':<52}{'CODE':<6}BODY")
print("-" * 130)
for tag, m, p, code, snip in rows:
    print(f"{tag:<9}{m:<7}{p:<52}{str(code):<6}{snip}")

print("\n\n================ FLAGS ================")
print("\n-- NOAUTH not returning 401/403 (auth boundary leak or crash) --")
for tag, m, p, code, snip in rows:
    if tag == "NOAUTH" and code not in (401, 403):
        print(f"  {m} {p} -> {code}  {snip[:90]}")

print("\n-- Raw 500 (uncategorized server error on foreseeable failure) --")
for tag, m, p, code, snip in rows:
    if code == 500:
        print(f"  [{tag}] {m} {p} -> 500  {snip[:110]}")

print("\n-- 200 with embedded error marker (fake success) --")
for tag, m, p, code, snip in rows:
    if code == 200 and has_hidden_error(200, snip):
        print(f"  [{tag}] {m} {p} -> 200  {snip[:110]}")
