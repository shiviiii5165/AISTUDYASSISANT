"""Audit helper (Family 3): probe each API key/token directly against its provider.
Reads the ROOT .env (the file the app actually loads per config.py)."""
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT / ".env")

def mask(v):
    return f"{v[:4]}...{v[-6:]}" if v and len(v) > 12 else "(short/empty)"

def get(name):
    return (os.environ.get(name) or "").strip()

results = []
def rec(pool, var, val, status, detail):
    results.append((pool, var, mask(val), status, detail))

TIMEOUT = 20.0

# ---- GEMINI ----
for var in ["GEMINI_API_KEY", "GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_IMAGE_API_KEY"]:
    v = get(var)
    if not v:
        rec("gemini", var, v, "ABSENT", "not set"); continue
    try:
        r = httpx.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={v}", timeout=TIMEOUT)
        rec("gemini", var, v, "LIVE" if r.status_code == 200 else f"DEAD({r.status_code})",
            f"HTTP {r.status_code} {r.text[:100].replace(chr(10),' ')}")
    except Exception as e:
        rec("gemini", var, v, "ERROR", str(e)[:100])

# ---- GROQ ----
for var in ["GROQ_API_KEY", "GROQ_API_KEY_1", "GROQ_API_KEY_2", "GROQ_API_KEY_3"]:
    v = get(var)
    if not v:
        rec("groq", var, v, "ABSENT", "not set"); continue
    try:
        r = httpx.get("https://api.groq.com/openai/v1/models",
                      headers={"Authorization": f"Bearer {v}"}, timeout=TIMEOUT)
        rec("groq", var, v, "LIVE" if r.status_code == 200 else f"DEAD({r.status_code})",
            f"HTTP {r.status_code} {r.text[:100].replace(chr(10),' ')}")
    except Exception as e:
        rec("groq", var, v, "ERROR", str(e)[:100])

# ---- OPENROUTER ----
for var in ["OPENROUTER_API_KEY", "OPENROUTER_API_KEY_1", "OPENROUTER_API_KEY_2", "OPENROUTER_API_KEY_3"]:
    v = get(var)
    if not v:
        rec("openrouter", var, v, "ABSENT", "not set"); continue
    try:
        r = httpx.get("https://openrouter.ai/api/v1/key",
                      headers={"Authorization": f"Bearer {v}"}, timeout=TIMEOUT)
        rec("openrouter", var, v, "LIVE" if r.status_code == 200 else f"DEAD({r.status_code})",
            f"HTTP {r.status_code} {r.text[:120].replace(chr(10),' ')}")
    except Exception as e:
        rec("openrouter", var, v, "ERROR", str(e)[:100])

# ---- CEREBRAS ----
for var in ["CEREBRAS_API_KEY", "CEREBRAS_API_KEY_1", "CEREBRAS_API_KEY_2", "CEREBRAS_API_KEY_3"]:
    v = get(var)
    if not v:
        rec("cerebras", var, v, "ABSENT", "not set"); continue
    try:
        r = httpx.get("https://api.cerebras.ai/v1/models",
                      headers={"Authorization": f"Bearer {v}"}, timeout=TIMEOUT)
        rec("cerebras", var, v, "LIVE" if r.status_code == 200 else f"DEAD({r.status_code})",
            f"HTTP {r.status_code} {r.text[:100].replace(chr(10),' ')}")
    except Exception as e:
        rec("cerebras", var, v, "ERROR", str(e)[:100])

# ---- CLOUDFLARE tokens ----
for var in ["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_API_TOKEN_1", "CLOUDFLARE_API_TOKEN_2", "CLOUDFLARE_API_TOKEN_3"]:
    v = get(var)
    if not v:
        rec("cloudflare", var, v, "ABSENT", "not set"); continue
    try:
        r = httpx.get("https://api.cloudflare.com/client/v4/user/tokens/verify",
                      headers={"Authorization": f"Bearer {v}"}, timeout=TIMEOUT)
        ok = r.status_code == 200 and r.json().get("result", {}).get("status") == "active"
        rec("cloudflare", var, v, "LIVE" if ok else f"DEAD({r.status_code})",
            f"HTTP {r.status_code} {r.text[:120].replace(chr(10),' ')}")
    except Exception as e:
        rec("cloudflare", var, v, "ERROR", str(e)[:100])

# ---- Print ----
print(f"{'POOL':<11}{'VAR':<24}{'MASKED':<18}{'STATUS':<12}DETAIL")
print("-" * 110)
for pool, var, m, status, detail in results:
    print(f"{pool:<11}{var:<24}{m:<18}{status:<12}{detail}")
