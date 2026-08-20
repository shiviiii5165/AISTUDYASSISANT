from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.db.supabase_client import supabase
from app.core.dependencies import get_current_user

router = APIRouter()

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
    return {"message": "User created successfully", "user": res.user}

@router.post("/login")
async def login(user: UserLogin):
    res = supabase.auth.sign_in_with_password({
        "email": user.email,
        "password": user.password
    })
    return {"session": res.session}

@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return {"user": current_user}
