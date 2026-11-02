from app.core.config import settings
from app.core.logging import logger
import socket
from urllib.parse import urlparse
import os

supabase = None

def _is_host_resolvable(url: str) -> bool:
    """Checks whether the Supabase domain is reachable in DNS before initializing client."""
    try:
        host = urlparse(url).hostname
        if not host or host in ("localhost", "127.0.0.1", "your-project-id.supabase.co"):
            return False
        # Fast DNS resolution probe
        socket.getaddrinfo(host, 443, socket.AF_UNSPEC, socket.SOCK_STREAM)
        return True
    except Exception:
        return False

# Explicit offline mode override for testing and development
if os.environ.get("SUPABASE_OFFLINE_MODE", "").lower() in ("true", "1"):
    logger.info("[SupabaseClient] SUPABASE_OFFLINE_MODE enabled; using synchronized local storage")
    supabase = None
elif settings.SUPABASE_URL and settings.SUPABASE_KEY and _is_host_resolvable(settings.SUPABASE_URL):
    try:
        from supabase import create_client, Client
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        logger.info("[SupabaseClient] Successfully connected to remote Supabase instance")
    except Exception as e:
        logger.warning(f"[SupabaseClient] Initialization notice: {e}; falling back to local storage")
        supabase = None
else:
    logger.info(
        f"[SupabaseClient] Remote Supabase host ({urlparse(settings.SUPABASE_URL).hostname or 'none'}) "
        f"is unresolvable or inactive; platform running in resilient local storage mode"
    )
    supabase = None
