"""
Two different questions, two different endpoints:

- /health/live  -> "is the process running at all?" Always 200 if the app is up.
  A load balancer/orchestrator uses this to decide whether to restart the container.
- /health/ready -> "can this instance actually serve traffic right now?" Checks
  the database round-trip. If the DB is down, this returns 503 so a load
  balancer stops routing traffic here instead of forwarding requests that will
  fail anyway.

Collapsing these into one "/health" is a common beginner mistake: it either
restarts a healthy-but-DB-starved container in a crash loop, or it keeps
sending traffic to an instance that can't do anything useful.
"""
from fastapi import APIRouter, Response, status

from app.db.session import check_db_connection

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness() -> dict:
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness(response: Response) -> dict:
    db_ok = await check_db_connection()
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "database": "unreachable"}
    return {"status": "ready", "database": "ok"}
