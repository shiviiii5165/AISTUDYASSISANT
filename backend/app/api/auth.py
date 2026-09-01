from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.db.supabase_client import supabase
from app.core.dependencies import get_current_user

router = APIRouter()


def _public_user(user) -> dict:
    """Return only non-sensitive, client-relevant fields from a Supabase user."""
    if user is None:
        return None
    metadata = getattr(user, "user_metadata", None) or {}
    return {
        "id": getattr(user, "id", None),
        "email": getattr(user, "email", None),
        "full_name": metadata.get("full_name") or metadata.get("name"),
    }


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: str
    password: str

@router.post("/signup")
async def signup(user: UserCreate):
    res = supabase.auth.sign_up({
        "email": user.email,
        "password": user.password,
        "options": {
            "data": {
                "full_name": user.full_name
            }
        }
    })
    return {"message": "User created successfully", "user": _public_user(res.user)}

@router.post("/login")
async def login(user: UserLogin):
    res = supabase.auth.sign_in_with_password({
        "email": user.email,
        "password": user.password
    })
    session = res.session
    return {
        "session": {
            "access_token": getattr(session, "access_token", None),
            "refresh_token": getattr(session, "refresh_token", None),
            "expires_at": getattr(session, "expires_at", None),
            "token_type": getattr(session, "token_type", None),
            "user": _public_user(getattr(session, "user", None)),
        }
    }

@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return {"user": _public_user(current_user)}
