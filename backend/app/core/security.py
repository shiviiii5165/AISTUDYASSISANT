from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI

# Initialize Rate Limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

def setup_rate_limiting(app: FastAPI):
    """Configures the slowapi rate limiter on the FastAPI app."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to inject strict security headers into every HTTP response.
    Protects against clickjacking, MIME-sniffing, and XSS.
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Optional: Content-Security-Policy can be added here, but typically managed at the Edge/Next.js for web apps.
        return response

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to reject requests that exceed a specified maximum size.
    """
    def __init__(self, app: FastAPI, max_size_bytes: int):
        super().__init__(app)
        self.max_size_bytes = max_size_bytes

    async def dispatch(self, request: Request, call_next):
        if request.headers.get("content-length"):
            try:
                content_length = int(request.headers["content-length"])
                if content_length > self.max_size_bytes:
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Payload Too Large"}
                    )
            except ValueError:
                pass
        return await call_next(request)

