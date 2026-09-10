from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import traceback

from app.api import auth, pdfs, chat, notes, predict
from app.core.config import settings
from app.core.logging import logger

app = FastAPI(title="TeachGenie API", version="1.0.0")

# Parse allowed origins from settings
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if "*" not in origins else ["*"],
    # Scope the regex to our own deployed subdomains only. Do NOT match arbitrary
    # *.vercel.app / *.onrender.com subdomains, which are open public hosting and
    # would trust any attacker-controlled site on those platforms.
    allow_origin_regex=r"https://(prepmind|aistudyassisant)\.(vercel\.app|onrender\.com)|http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.core.security import setup_rate_limiting, SecurityHeadersMiddleware, RequestSizeLimitMiddleware
from slowapi.middleware import SlowAPIMiddleware

app.add_middleware(RequestSizeLimitMiddleware, max_size_bytes=10_000_000) # 10MB
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SlowAPIMiddleware)
setup_rate_limiting(app)


# Global exception handler — always returns CORS-safe JSON, never a raw crash.
# HTTPException and RequestValidationError are passed through to FastAPI's own
# handlers so deliberate 4xx/5xx codes (e.g. the Phase-3 503 gate) are
# preserved and not accidentally flattened into 500.
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None) or {},
        )
    if isinstance(exc, RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": exc.errors()})
    logger.error(f"UNHANDLED EXCEPTION on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."}
    )

@app.get("/")
def read_root():
    from app.db.supabase_client import supabase
    return {
        "message": "Welcome to TeachGenie API", 
        "supabase": "connected" if supabase else "failed",
        "gemini": "configured" if settings.GEMINI_API_KEY else "missing"
    }

@app.get("/api/health")
def health_check():
    """Lightweight liveness check — confirms the serverless function boots and env vars are loaded."""
    from app.db.supabase_client import supabase
    return {
        "status": "ok",
        "supabase": "connected" if supabase else "missing",
        "gemini_key": "set" if settings.GEMINI_API_KEY else "missing",
        "gemini_image_key": "set" if settings.GEMINI_IMAGE_API_KEY else "missing",
    }

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(pdfs.router, prefix="/pdfs", tags=["pdfs"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(notes.router, prefix="/api/notes", tags=["notes"])
app.include_router(predict.router, prefix="/api/predict", tags=["predict"])
from app.api import billing, decks, lessons, teach
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])
app.include_router(decks.router, prefix="/api/decks", tags=["decks"])
app.include_router(lessons.router, prefix="/api/lessons", tags=["lessons"])
app.include_router(teach.router, prefix="/api/teach", tags=["teach"])
from app.api import orchestrator as orchestrator_api
app.include_router(orchestrator_api.router, prefix="/api/orchestrator", tags=["orchestrator"])
from app.api import librarian as librarian_api
app.include_router(librarian_api.router, prefix="/api/librarian", tags=["librarian"])
from app.api import tutor as tutor_api
app.include_router(tutor_api.router, prefix="/api/tutor", tags=["tutor"])
from app.api import content_creator as content_creator_api
app.include_router(content_creator_api.router, prefix="/api/content-creator", tags=["content-creator"])
from app.api import lesson_planner
app.include_router(lesson_planner.router, prefix="/api/lesson-planner", tags=["lesson-planner"])
from app.api import quiz as quiz_api
app.include_router(quiz_api.router, prefix="/api/quiz", tags=["quiz"])
from app.api import live_quiz as live_quiz_api
app.include_router(live_quiz_api.router, prefix="/api/live-quizzes", tags=["live-quiz"])
from app.api import notes_generator
app.include_router(notes_generator.router, prefix="/api/notes-generator", tags=["notes-generator"])

