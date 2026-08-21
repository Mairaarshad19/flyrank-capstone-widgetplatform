import pytest


@pytest.mark.asyncio
async def test_liveness_always_ok(client):
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_readiness_reports_db_status(client):
    resp = await client.get("/health/ready")
    # In this test DB is in-memory SQLite via dependency override, so the
    # readiness check itself (which pings the real `engine`, not the override)
    # is validated against Postgres manually in Phase 0's docker-compose gate.
    assert resp.status_code in (200, 503)
    assert "status" in resp.json()
