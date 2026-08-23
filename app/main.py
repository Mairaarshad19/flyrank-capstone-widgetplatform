"""
Application entrypoint.

Production concerns handled here, deliberately, from day one:

1. Lifespan context: log startup/shutdown explicitly. When you add background
   workers/queues later, they start and stop here too — one place controls the
   process's lifecycle instead of scattering it across modules.
2. A global exception handler: any unhandled exception returns a clean JSON
   500 with a request ID, and is logged with the full traceback server-side.
   The client NEVER sees a raw Python traceback. This is what "never a bare
   500 with no context" looks like in practice.
3. Every request gets a request_id (from header if provided, else generated),
   attached to the response and to every log line for that request, so a
   single failed request can be traced end-to-end in the logs.
"""
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.logging import configure_logging
from app.core.rate_limit import limiter

configure_logging()
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_startup", extra={"env": settings.ENV, "app": settings.APP_NAME})
    yield
    logger.info("app_shutdown")


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# Explicit allow-list, never "*" — this same policy also governs the public
# submission endpoint (Phase 4), which must never accept an arbitrary origin.
# Full preflight (OPTIONS) handling is exercised end-to-end once POST
# /submissions exists; this GET path just needs the CORS headers present.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# --- Rate limiting (per-IP; per-widget lives inside app/api/submissions.py) ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# --- Reject oversized bodies before they're even parsed. Checked via
# Content-Length rather than reading the full stream, since the point is to
# reject cheaply, before spending any work on a payload we're going to
# discard anyway. ---
MAX_SUBMISSION_BODY_BYTES = 20_000  # generous for a lead-capture form


@app.middleware("http")
async def limit_submission_body_size(request: Request, call_next):
    if request.url.path == "/submissions" and request.method == "POST":
        content_length = request.headers.get("content-length")
        if content_length is not None and int(content_length) > MAX_SUBMISSION_BODY_BYTES:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "error": "payload_too_large",
                    "message": f"Request body exceeds {MAX_SUBMISSION_BODY_BYTES} bytes.",
                },
            )
    return await call_next(request)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.monotonic()
    try:
        response: Response = await call_next(request)
    except Exception:
        # Belt-and-braces: the exception handler below normally catches this,
        # but if something escapes it, we still log with context before FastAPI
        # turns it into its own 500.
        logger.exception(
            "unhandled_request_exception",
            extra={"request_id": request_id, "path": request.url.path},
        )
        raise
    duration_ms = round((time.monotonic() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = request.headers.get("X-Request-ID", "unknown")
    logger.exception(
        "unhandled_exception",
        extra={"request_id": request_id, "path": request.url.path},
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "Something went wrong on our end. This has been logged.",
            "request_id": request_id,
        },
    )


# Routers are registered here as they're built out (Phase 2+):
from app.api.auth import router as auth_router  # noqa: E402
from app.api.health import router as health_router  # noqa: E402
from app.api.public import router as public_router  # noqa: E402
from app.api.submissions import router as submissions_router  # noqa: E402
from app.api.widgets import router as widgets_router  # noqa: E402

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(widgets_router)
app.include_router(public_router)
app.include_router(submissions_router)
