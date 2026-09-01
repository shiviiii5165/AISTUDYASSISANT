"""Audit (Family 1): upload a text-less PDF and check whether it is marked 'ready' with 0 chunks."""
import io, json, time, os
from pathlib import Path
import httpx
from pypdf import PdfWriter
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND.parent / ".env")
from supabase import create_client
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

BASE = "http://127.0.0.1:8010"
TA = json.load(open(BACKEND / "test_tokens.json"))["tokenA"]

# Build a valid PDF with a single BLANK page (no extractable text)
w = PdfWriter()
w.add_blank_page(width=612, height=792)
buf = io.BytesIO()
w.write(buf)
pdf_bytes = buf.getvalue()
print(f"blank PDF size: {len(pdf_bytes)} bytes")

c = httpx.Client(base_url=BASE, timeout=60)
up = c.post("/pdfs/upload", headers={"Authorization": f"Bearer {TA}"},
            files={"file": ("blank.pdf", pdf_bytes, "application/pdf")},
            data={"subject": "ZeroChunkTest"})
print(f"upload -> {up.status_code} {up.text[:200]}")
if up.status_code != 200:
    raise SystemExit("upload failed")
pdf_id = up.json()["pdf_id"]
print(f"pdf_id={pdf_id}")

final = None
for _ in range(12):
    time.sleep(3)
    sr = c.get(f"/pdfs/{pdf_id}/status", headers={"Authorization": f"Bearer {TA}"})
    st = sr.json().get("status")
    print(f"  status={st}")
    if st in ("ready", "error"):
        final = st
        break

# Count chunks actually stored
rows = sb.table("document_chunks").select("id", count="exact").eq("pdf_id", pdf_id).execute()
chunk_count = rows.count if rows.count is not None else len(rows.data)
print("\n================ RESULT ================")
print(f"final status : {final}")
print(f"chunk count  : {chunk_count}")
if final == "ready" and chunk_count == 0:
    print(">>> STATUS LIE CONFIRMED: PDF marked 'ready' with ZERO chunks stored (unsearchable).")
else:
    print(">>> No lie: status/chunks consistent.")

# cleanup
try:
    sb.table("document_chunks").delete().eq("pdf_id", pdf_id).execute()
    sb.table("pdfs").delete().eq("id", pdf_id).execute()
    print("(cleaned up test rows)")
except Exception as e:
    print(f"(cleanup note: {e})")
