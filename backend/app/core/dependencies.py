from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
import os
import jwt

from app.db.supabase_client import supabase
from app.core.config import settings
from app.core.logging import logger
from app.core.user_roles import UserRoleRepository, VALID_SYSTEM_ROLES

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


def _is_dev_environment() -> bool:
    """Returns True ONLY when explicitly in a recognized development or testing mode.
    Missing, empty, or unknown environment configurations FAIL CLOSED (return False).
    """
    env = (getattr(settings, "ENVIRONMENT", "") or os.environ.get("ENVIRONMENT", "")).lower().strip()
    if not env or env not in ("development", "test", "local") or env == "production":
        return False
    return True


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> AuthenticatedUser:
    """
    Authenticates user from Bearer JWT.
    High-performance multi-tier strategy:
    1. Check dev persona tokens ONLY in development/test environments (strictly blocked in production).
    2. Ultra-fast local cryptographic JWT verification using SUPABASE_JWT_SECRET (HS256, 0.05ms, no network latency).
    3. Fallback to Supabase remote auth lookup if local secret is not configured.
    Never accepts unverified JWT payloads without cryptographic signature verification.
    NEVER derives privileged roles from user-editable metadata.
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
            authoritative_role = UserRoleRepository.get_user_role(u["id"]) or u["role"]
            return AuthenticatedUser(
                id=u["id"],
                email=u["email"],
                role=authoritative_role,
                full_name=u["full_name"],
                app_metadata={"role": authoritative_role},
                user_metadata={"full_name": u["full_name"], "role": authoritative_role}
            )

    # 2. Ultra-Fast Local Cryptographic JWT Verification (using SUPABASE_JWT_SECRET HS256)
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
                # Security rule: NEVER derive roles from client-editable user_metadata
                raw_role = payload.get("role") or app_meta.get("role") or "student"
                role = raw_role if raw_role in VALID_SYSTEM_ROLES else "student"

                # Check authoritative database role assignment (in-memory cached)
                authoritative_role = UserRoleRepository.get_user_role(user_id)
                if authoritative_role:
                    role = authoritative_role

                return AuthenticatedUser(
                    id=user_id,
                    email=payload.get("email", ""),
                    role=role,
                    full_name=payload.get("user_metadata", {}).get("full_name", ""),
                    app_metadata=app_meta,
                    user_metadata=payload.get("user_metadata", {}) or {}
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
            logger.debug(f"[Auth] Local JWT decode exception: {e}; attempting remote Supabase lookup")

    # 3. Fallback to Supabase Auth Client verification if local verification did not resolve
    if supabase is not None:
        try:
            res = supabase.auth.get_user(token)
            if res and res.user:
                u = res.user
                app_meta = getattr(u, "app_metadata", {}) or {}
                raw_role = app_meta.get("role") or "student"
                role = raw_role if raw_role in VALID_SYSTEM_ROLES else "student"

                authoritative_role = UserRoleRepository.get_user_role(u.id)
                if authoritative_role:
                    role = authoritative_role

                return AuthenticatedUser(
                    id=u.id,
                    email=getattr(u, "email", "") or "",
                    role=role,
                    full_name=getattr(u, "user_metadata", {}).get("full_name") or "",
                    app_metadata=app_meta,
                    user_metadata=getattr(u, "user_metadata", {}) or {}
                )
        except Exception as e:
            logger.debug(f"[Auth] Supabase remote validation failed: {e}")

    # Cryptographic verification failed; fail closed
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(allowed_roles: List[str]):
    """
    Enforces server-side role-based access control.
    Strictly verifies authoritative role against allowed_roles list.
    """
    def role_checker(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        user_role = current_user.role

        if "super_admin" in allowed_roles and user_role == "super_admin":
            return current_user

        if user_role not in allowed_roles:
            logger.warning(
                f"[Security] Access denied: User {current_user.id} with role '{user_role}' "
                f"attempted to access endpoint requiring {allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: role '{user_role}' is not authorized. Required: {allowed_roles}",
            )
        return current_user
    return role_checker


def get_current_student(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    """Convenience dependency for endpoints accessible to students or administrators."""
    if current_user.role not in ("student", "super_admin", "school_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student portal access required",
        )
    return current_user


def get_current_parent(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    """Convenience dependency for parent portal endpoints."""
    if current_user.role not in ("parent", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Parent portal access required",
        )
    return current_user


def get_current_teacher(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    """Convenience dependency for teacher portal endpoints."""
    if current_user.role not in ("teacher", "super_admin", "school_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher portal access required",
        )
    return current_user


def get_current_admin(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    """Convenience dependency for administrative operations."""
    if current_user.role not in ("super_admin", "school_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative authorization required",
        )
    return current_user


# Backward compatibility alias
get_current_admin_user = get_current_admin


# Role-specific convenience guards
require_student = require_role(["student"])
require_parent = require_role(["parent"])
require_teacher = require_role(["teacher"])
require_school_admin = require_role(["school_admin"])
require_content_creator = require_role(["content_creator"])
require_admin = require_role(["admin", "super_admin"])
get_current_admin_user = require_admin
