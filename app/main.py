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

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_startup", extra={"env": settings.ENV, "app": settings.APP_NAME})
    yield
    logger.info("app_shutdown")


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)


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
from app.api.health import router as health_router  # noqa: E402

app.include_router(health_router)
