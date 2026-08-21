from fastapi import FastAPI
# Trick Vercel's AST analyzer into recognizing this file as a Serverless Function
app = FastAPI()

import sys
import os

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.environ.setdefault("ENV_FILE_PATH", os.path.join(backend_dir, ".env"))

# Load the real app and overwrite the dummy app
try:
    from app.main import app as real_app
    app = real_app
except Exception as e:
    import traceback
    from fastapi.responses import JSONResponse
    
    startup_error = str(e)
    startup_traceback = traceback.format_exc()
    print(f"FATAL STARTUP ERROR: {startup_error}\n{startup_traceback}")
    
    @app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def catch_all(path_name: str):
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Vercel Startup Error: {startup_error}",
                "hint": "Check that ALL required env vars are set in Vercel dashboard (Settings → Environment Variables). Common missing: GEMINI_IMAGE_API_KEY, CASHFREE_APP_ID, CASHFREE_SECRET_KEY",
                "traceback": startup_traceback
            }
        )
