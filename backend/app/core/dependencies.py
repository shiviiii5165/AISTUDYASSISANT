from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.db.supabase_client import supabase

import os
from app.core.config import settings

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials

    # Developer bypass tokens (mock-dev-token, dev-admin-token) are strictly disabled
    # in cloud / canary / production environments. Allowed only when explicitly configured
    # in local development/test environments.
    is_cloud_or_prod = (
        getattr(settings, "TEACHGENIE_MODE", "PRODUCTION").upper() == "PRODUCTION"
        or os.environ.get("RENDER") is not None
        or os.environ.get("VERCEL") is not None
    )
    allow_dev_auth = os.environ.get("TEACHGENIE_ALLOW_DEV_AUTH", "").lower() in ("true", "1") and not is_cloud_or_prod

    if allow_dev_auth:
        if token == "dev-admin-token":
            class DevAdminUser:
                id = "00000000-0000-0000-0000-000000000099"
                email = "admin@teachgenie.com"
                app_metadata = {"role": "admin"}
                user_metadata = {"full_name": "Admin User", "role": "admin"}
            return DevAdminUser()
        if token in ("dev-host-token", "mock-dev-token"):
            class DevMockUser:
                id = "00000000-0000-0000-0000-000000000001"
                email = "teacher@teachgenie.com"
                app_metadata = {"role": "authenticated"}
                user_metadata = {"full_name": "Teacher Jane"}
            return DevMockUser()
    try:
        # Verify JWT with Supabase
        res = supabase.auth.get_user(token)
        if not res or not res.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return res.user
    except Exception as e:
        # Never expose raw exception details from auth failures
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_admin_user(current_user = Depends(get_current_user)):
    """Validates that the authenticated user holds an admin role."""
    # Assuming role is stored in app_metadata or user_metadata in Supabase
    app_meta = getattr(current_user, "app_metadata", {})
    user_meta = getattr(current_user, "user_metadata", {})
    
    role = app_meta.get("role") or user_meta.get("role")
    
    if role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Admin access required."
        )
    return current_user
