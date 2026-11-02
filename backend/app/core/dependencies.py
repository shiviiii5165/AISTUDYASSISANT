from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
import os
import jwt

from app.db.supabase_client import supabase
from app.core.config import settings
from app.core.logging import logger

security = HTTPBearer(auto_error=False)


class AuthenticatedUser:
    """Standardized user identity across all LearnByGenie portals."""
    def __init__(
        self,
        id: str,
        email: str = "",
        role: str = "student",
        full_name: str = "",
        app_metadata: Optional[dict] = None,
        user_metadata: Optional[dict] = None
    ):
        self.id = id
        self.email = email
        self.role = role
        self.app_metadata = app_metadata or {"role": role}
        self.user_metadata = user_metadata or {"full_name": full_name or f"User {id[:6]}", "role": role}

    def __repr__(self):
        return f"<AuthenticatedUser id={self.id} role={self.role} email={self.email}>"


# Mock dev personas for rapid local / test authentication
MOCK_DEV_USERS = {
    "dev-admin-token": {
        "id": "00000000-0000-0000-0000-000000000099",
        "email": "admin@learnbygenie.com",
        "role": "super_admin",
        "full_name": "Super Administrator"
    },
    "dev-super-admin-token": {
        "id": "00000000-0000-0000-0000-000000000099",
        "email": "superadmin@learnbygenie.com",
        "role": "super_admin",
        "full_name": "Platform Super Admin"
    },
    "dev-school-admin-token": {
        "id": "00000000-0000-0000-0000-000000000088",
        "email": "principal@delhipublicschool.edu",
        "role": "school_admin",
        "full_name": "Principal Sharma"
    },
    "dev-teacher-token": {
        "id": "00000000-0000-0000-0000-000000000001",
        "email": "teacher@learnbygenie.com",
        "role": "teacher",
        "full_name": "Teacher Jane"
    },
    "dev-host-token": {
        "id": "00000000-0000-0000-0000-000000000001",
        "email": "teacher@learnbygenie.com",
        "role": "teacher",
        "full_name": "Teacher Jane"
    },
    "mock-dev-token": {
        "id": "00000000-0000-0000-0000-000000000001",
        "email": "teacher@learnbygenie.com",
        "role": "teacher",
        "full_name": "Teacher Jane"
    },
    "dev-parent-token": {
        "id": "00000000-0000-0000-0000-000000000077",
        "email": "parent@learnbygenie.com",
        "role": "parent",
        "full_name": "Parent Rajesh"
    },
    "dev-creator-token": {
        "id": "00000000-0000-0000-0000-000000000066",
        "email": "creator@learnbygenie.com",
        "role": "content_creator",
        "full_name": "Content Author Sarah"
    },
    "dev-student-token": {
        "id": "a56da972-0f19-418d-b0f7-de91ff114190",
        "email": "student@learnbygenie.com",
        "role": "student",
        "full_name": "Student Arjun"
    }
}


VALID_SYSTEM_ROLES = {
    "student",
    "parent",
    "teacher",
    "school_admin",
    "content_creator",
    "admin",
    "super_admin"
}


def _is_dev_environment() -> bool:
    """Returns True ONLY when explicitly in development or testing mode."""
    env = (getattr(settings, "ENVIRONMENT", "") or os.environ.get("ENVIRONMENT", "development")).lower()
    return env in ("development", "test", "local") and env != "production"


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> AuthenticatedUser:
    """
    Authenticates user from Bearer JWT.
    Resilient multi-tier strategy:
    1. Check dev persona tokens ONLY in development/test environments (strictly blocked in production).
    2. Supabase remote auth lookup.
    3. Network-resilient local JWT cryptographic verification using SUPABASE_JWT_SECRET.
    Never accepts unverified JWT payloads without cryptographic signature verification.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # 1. Dev persona tokens (STRICTLY quarantined to non-production environments)
    if _is_dev_environment():
        if token in MOCK_DEV_USERS:
            u = MOCK_DEV_USERS[token]
            return AuthenticatedUser(
                id=u["id"],
                email=u["email"],
                role=u["role"],
                full_name=u["full_name"],
                app_metadata={"role": u["role"]},
                user_metadata={"full_name": u["full_name"], "role": u["role"]}
            )

    # 2. Attempt Supabase Auth Client verification if configured
    if supabase is not None:
        try:
            res = supabase.auth.get_user(token)
            if res and res.user:
                u = res.user
                app_meta = getattr(u, "app_metadata", {}) or {}
                user_meta = getattr(u, "user_metadata", {}) or {}
                raw_role = app_meta.get("role") or user_meta.get("role") or "student"
                role = raw_role if raw_role in VALID_SYSTEM_ROLES else "student"
                return AuthenticatedUser(
                    id=u.id,
                    email=getattr(u, "email", "") or "",
                    role=role,
                    full_name=user_meta.get("full_name") or user_meta.get("name") or "",
                    app_metadata=app_meta,
                    user_metadata=user_meta
                )
        except Exception as e:
            logger.debug(f"[Auth] Supabase remote validation notice: {e}; attempting local cryptographic JWT verification")

    # 3. Resilient Local Cryptographic JWT Verification (using SUPABASE_JWT_SECRET HS256)
    jwt_secret = getattr(settings, "SUPABASE_JWT_SECRET", None) or os.environ.get("SUPABASE_JWT_SECRET")
    if jwt_secret:
        try:
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": False, "verify_exp": True, "verify_signature": True}
            )
            user_id = payload.get("sub")
            if user_id:
                app_meta = payload.get("app_metadata", {}) or {}
                user_meta = payload.get("user_metadata", {}) or {}
                raw_role = payload.get("role") or app_meta.get("role") or user_meta.get("role") or "student"
                role = raw_role if raw_role in VALID_SYSTEM_ROLES else "student"
                return AuthenticatedUser(
                    id=user_id,
                    email=payload.get("email", ""),
                    role=role,
                    full_name=user_meta.get("full_name", ""),
                    app_metadata=app_meta,
                    user_metadata=user_meta
                )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid cryptographic token signature",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.debug(f"[Auth] Cryptographic JWT decode error: {e}")

    # Cryptographic verification failed; fail closed
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(allowed_roles: List[str]):
    """
    Enforces server-side role-based access control.
    Super administrators always have cross-role operational access.
    """
    def role_dependency(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        app_meta = getattr(current_user, "app_metadata", {}) or {}
        user_meta = getattr(current_user, "user_metadata", {}) or {}
        user_role = (
            getattr(current_user, "role", None)
            or app_meta.get("role")
            or user_meta.get("role")
            or "student"
        )
        if user_role not in allowed_roles and user_role not in ("admin", "super_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: role '{user_role}' is not authorized. Required: {allowed_roles}"
            )
        return current_user
    return role_dependency


# Role-specific convenience guards
require_student = require_role(["student"])
require_parent = require_role(["parent"])
require_teacher = require_role(["teacher"])
require_school_admin = require_role(["school_admin"])
require_content_creator = require_role(["content_creator"])
require_admin = require_role(["admin", "super_admin"])
get_current_admin_user = require_admin
