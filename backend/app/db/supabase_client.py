from app.core.config import settings

try:
    from supabase import create_client, Client
    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
except Exception as e:
    print(f"[SupabaseClient] Notice: Supabase client initialization bypassed or mock mode: {e}")
    supabase = None
