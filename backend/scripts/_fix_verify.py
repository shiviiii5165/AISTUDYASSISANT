"""Live verification of Fix 1 (PDF zero-chunks) and Fix 2 (DELETE lessons)."""
import io, json, time, os, uuid
from pathlib import Path
import httpx
from pypdf import PdfWriter
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND.parent / ".env")
from supabase import create_client
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

BASE = "http://127.0.0.1:8010"
toks = json.load(open(BACKEND / "test_tokens.json"))
TA, UA = toks["tokenA"], toks["userA"]
H = {"Authorization": f"Bearer {TA}"}
c = httpx.Client(base_url=BASE, timeout=60)

print("=" * 60); print("FIX 1 — blank/text-less PDF must become status=error"); print("=" * 60)
w = PdfWriter(); w.add_blank_page(width=612, height=792)
buf = io.BytesIO(); w.write(buf); pdf_bytes = buf.getvalue()
up = c.post("/pdfs/upload", headers=H,
            files={"file": ("blank.pdf", pdf_bytes, "application/pdf")},
            data={"subject": "Fix1Verify"})
print(f"upload -> {up.status_code} {up.text}")
pdf_id = up.json()["pdf_id"]
final = None
for _ in range(12):
    time.sleep(3)
    sr = c.get(f"/pdfs/{pdf_id}/status", headers=H)
    print(f"  poll /pdfs/{pdf_id}/status -> {sr.status_code} {sr.text}")
    st = sr.json().get("status")
    if st in ("ready", "error"):
        final = st; break
row = sb.table("pdfs").select("status, error_message").eq("id", pdf_id).maybe_single().execute()
chunks = sb.table("document_chunks").select("id", count="exact").eq("pdf_id", pdf_id).execute()
print(f"\nDB row: status={row.data.get('status')!r} error_message={row.data.get('error_message')!r}")
print(f"chunk count: {chunks.count}")
print("RESULT:", "PASS — honest error, not a ready lie" if final == "error" and (chunks.count or 0) == 0
      else "FAIL")
sb.table("document_chunks").delete().eq("pdf_id", pdf_id).execute()
sb.table("pdfs").delete().eq("id", pdf_id).execute()
print("(cleaned up)")

print("\n" + "=" * 60); print("FIX 2 — DELETE /api/lessons/{id} honest outcomes"); print("=" * 60)
# Case A: nonexistent lesson id
nx = "00000000-0000-0000-0000-0000000000fe"
rA = c.request("DELETE", f"/api/lessons/{nx}", headers=H)
print(f"[nonexistent] DELETE /api/lessons/{nx} -> {rA.status_code} {rA.text}")

# Case B: seed a real owned lesson, delete it, confirm gone
lid = str(uuid.uuid4())
sb.table("video_lessons").insert({
    "id": lid, "user_id": UA, "topic": "Fix2 Verify Lesson", "level": "B.Tech",
    "duration": "1", "language": "english", "status": "ready",
    "scene_count": 1, "total_duration_seconds": 60, "lesson_json": {},
}).execute()
print(f"[seeded] lesson id={lid}")
rB = c.request("DELETE", f"/api/lessons/{lid}", headers=H)
print(f"[owned]  DELETE /api/lessons/{lid} -> {rB.status_code} {rB.text}")
gB = c.get(f"/api/lessons/{lid}", headers=H)
print(f"[owned]  GET after delete /api/lessons/{lid} -> {gB.status_code} {gB.text[:80]}")
rB2 = c.request("DELETE", f"/api/lessons/{lid}", headers=H)
print(f"[owned]  DELETE again (idempotent-honest) -> {rB2.status_code} {rB2.text}")

# confirm DB really gone
chk = sb.table("video_lessons").select("id").eq("id", lid).execute()
print(f"DB rows for lesson after delete: {len(chk.data)}")
ok = (rA.status_code == 404 and rB.status_code == 200 and gB.status_code == 404 and len(chk.data) == 0)
print("RESULT:", "PASS" if ok else "FAIL")
