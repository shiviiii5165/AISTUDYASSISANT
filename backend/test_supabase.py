import os
from dotenv import load_dotenv
load_dotenv()

from app.db.supabase_client import supabase

try:
    print("Testing pdfs bucket...")
    res1 = supabase.storage.from_("pdfs").upload("test/dummy.txt", b"hello")
    print("PDFs Upload:", res1)
except Exception as e:
    print("PDFs Upload Error:", e)

try:
    print("Testing handwritten-notes bucket...")
    res2 = supabase.storage.from_("handwritten-notes").upload("test/dummy.txt", b"hello")
    print("Notes Upload:", res2)
except Exception as e:
    print("Notes Upload Error:", e)
