import os
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

try:
    print("Buckets:")
    buckets = supabase.storage.list_buckets()
    print([b.name for b in buckets])
except Exception as e:
    print("Bucket error:", e)

try:
    print("Testing profiles table...")
    res = supabase.table("profiles").select("*").limit(1).execute()
    print("Profiles:", res.data)
except Exception as e:
    print("Profiles error:", e)
    
try:
    print("Testing pdfs table...")
    res = supabase.table("pdfs").select("*").limit(1).execute()
    print("PDFs:", res.data)
except Exception as e:
    print("PDFs error:", e)
