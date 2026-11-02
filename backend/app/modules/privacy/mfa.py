"""TOTP MFA (RFC 6238) and PKCE (RFC 7636) verification, using only cryptographic stdlib.

Secrets are AES-GCM encrypted at rest. After a valid code the client receives a short-lived
signed token and sends it in X-MFA-Token; `require_mfa` rejects teacher and admin calls
without one.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from urllib.parse import quote

import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import Depends, Header, HTTPException

from app.core.config import settings
from app.core.dependencies import AuthenticatedUser, get_current_user
from app.modules import store

MFA_ROLES = ("teacher", "school_admin", "admin", "super_admin")
TOKEN_TTL_SECONDS = 8 * 3600
STEP_SECONDS = 30
_ISSUER = "Learn Genie"


def _dev() -> bool:
    return (settings.ENVIRONMENT or "").lower().strip() in ("development", "test", "local")


def _master_secret() -> bytes:
    value = os.environ.get("MFA_MASTER_KEY")
    if not value:
        if _dev():
            value = "local-development-only"
        else:
            raise HTTPException(503, "MFA is not configured on this server")
    return hashlib.sha256(value.encode()).digest()


def _encrypt(plain: str) -> str:
    nonce = secrets.token_bytes(12)
    return base64.b64encode(nonce + AESGCM(_master_secret()).encrypt(nonce, plain.encode(), None)).decode()


def _decrypt(blob: str) -> str:
    raw = base64.b64decode(blob)
    return AESGCM(_master_secret()).decrypt(raw[:12], raw[12:], None).decode()


def totp(secret_b32: str, counter: int) -> str:
    key = base64.b32decode(secret_b32)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return f"{code % 1_000_000:06d}"


def check_totp(secret_b32: str, code: str, last_counter: int, now: float | None = None) -> int | None:
    """Return the matched counter (for replay blocking), allowing one step of clock drift."""
    current = int((time.time() if now is None else now) // STEP_SECONDS)
    for counter in (current - 1, current, current + 1):
        if counter > last_counter and hmac.compare_digest(totp(secret_b32, counter), code):
            return counter
    return None


def enroll(user_id: str, email: str) -> dict[str, str]:
    existing = store.get_one("mfa_factors", user_id=user_id)
    if existing and existing["confirmed"]:
        raise HTTPException(409, "MFA is already enabled")
    secret = base64.b32encode(secrets.token_bytes(20)).decode()
    store.upsert("mfa_factors", {"user_id": user_id, "secret_encrypted": _encrypt(secret),
                                 "confirmed": False, "last_counter": 0}, ("user_id",))
    uri = (f"otpauth://totp/{quote(_ISSUER)}:{quote(email or user_id)}"
           f"?secret={secret}&issuer={quote(_ISSUER)}&digits=6&period={STEP_SECONDS}")
    return {"secret": secret, "otpauth_uri": uri}


def _token_key() -> bytes:
    return hashlib.sha256(_master_secret() + b"mfa-token").digest()


def verify(user_id: str, code: str) -> dict[str, object]:
    factor = store.get_one("mfa_factors", user_id=user_id)
    if factor is None:
        raise HTTPException(404, "Enroll in MFA first")
    if not store_allow_attempt(user_id):
        raise HTTPException(429, "Too many attempts; try again shortly")
    counter = check_totp(_decrypt(factor["secret_encrypted"]), code, factor["last_counter"])
    if counter is None:
        raise HTTPException(400, "That code is not valid")
    store.update("mfa_factors", {"user_id": user_id}, {"confirmed": True, "last_counter": counter})
    expires = int(time.time()) + TOKEN_TTL_SECONDS
    token = jwt.encode({"sub": user_id, "exp": expires, "typ": "mfa"}, _token_key(), algorithm="HS256")
    return {"mfa_token": token, "expires_in": TOKEN_TTL_SECONDS}


def store_allow_attempt(user_id: str) -> bool:
    from app.modules.rate_limit import allow

    return allow(f"mfa:{user_id}", 5, 300)


def has_valid_token(user_id: str, token: str | None) -> bool:
    if not token:
        return False
    try:
        claims = jwt.decode(token, _token_key(), algorithms=["HS256"])
    except jwt.PyJWTError:
        return False
    return claims.get("sub") == user_id and claims.get("typ") == "mfa"


def require_mfa(
    user: AuthenticatedUser = Depends(get_current_user),
    x_mfa_token: str | None = Header(default=None),
) -> AuthenticatedUser:
    if user.role in MFA_ROLES and not has_valid_token(user.id, x_mfa_token):
        raise HTTPException(403, detail={"code": "mfa_required"})
    return user


def verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    """S256 only; the plain method offers no protection."""
    if not 43 <= len(code_verifier) <= 128:
        return False
    digest = hashlib.sha256(code_verifier.encode()).digest()
    computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return hmac.compare_digest(computed, code_challenge)
