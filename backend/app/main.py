from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api import auth, pdfs, chat, notes, predict
from app.core.config import settings

app = FastAPI(title="TeachGenie API", version="1.0.0")

# Parse allowed origins from settings
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    from app.db.supabase_client import supabase
    return {
        "message": "Welcome to TeachGenie API", 
        "supabase": "connected" if supabase else "failed",
        "gemini": "configured" if settings.GEMINI_API_KEY else "missing"
    }

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(pdfs.router, prefix="/pdfs", tags=["pdfs"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(notes.router, prefix="/api/notes", tags=["notes"])
app.include_router(predict.router, prefix="/api/predict", tags=["predict"])
from app.api import billing
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])

