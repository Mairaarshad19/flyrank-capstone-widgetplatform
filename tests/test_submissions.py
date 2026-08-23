import json
import uuid

import pytest

from app.api.submissions import get_geo_chain, get_notifier
from app.enrichment.base import GeoResult
from app.enrichment.chain import GeoFallbackChain
from app.main import app
from app.models.submission import NotificationStatus, Submission


async def _create_active_widget(client):
    reg = await client.post(
        "/auth/register",
        json={"tenant_name": "Acme", "email": f"sub-{uuid.uuid4().hex[:8]}@acme.com", "password": "supersecret123"},
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    created = (
        await client.post(
            "/widgets",
            json={"type": "signup_form", "title": "Newsletter", "config": {"fields": ["email"]}},
            headers=headers,
        )
    ).json()
    return created, headers


# ---------------------------------------------------------------------------
# 4a — CORS + boundary validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cors_preflight_allowed_origin_succeeds(client):
    resp = await client.options(
        "/submissions",
        headers={
            "Origin": "http://localhost:5500",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5500"


@pytest.mark.asyncio
async def test_cors_preflight_disallowed_origin_is_rejected(client):
    resp = await client.options(
        "/submissions",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in resp.headers


@pytest.mark.asyncio
async def test_submission_rejects_malformed_widget_id(client):
    resp = await client.post("/submissions", json={"widget_id": "not-a-uuid", "fields": {"email": "x@y.com"}})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submission_rejects_unknown_extra_fields(client):
    widget, _ = await _create_active_widget(client)
    resp = await client.post(
        "/submissions", json={"widget_id": widget["id"], "fields": {"email": "a@b.com"}, "unexpected": "x"}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submission_rejects_empty_fields(client):
    widget, _ = await _create_active_widget(client)
    resp = await client.post("/submissions", json={"widget_id": widget["id"], "fields": {}})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submission_rejects_oversized_body(client):
    widget, _ = await _create_active_widget(client)
    huge_value = "x" * 25_000
    body = json.dumps({"widget_id": widget["id"], "fields": {"note": huge_value}}).encode()
    resp = await client.post("/submissions", content=body, headers={"Content-Type": "application/json"})
    assert resp.status_code == 413


@pytest.mark.asyncio
async def test_submission_404_for_nonexistent_widget(client):
    resp = await client.post("/submissions", json={"widget_id": str(uuid.uuid4()), "fields": {"email": "a@b.com"}})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_submission_404_for_paused_widget(client):
    widget, headers = await _create_active_widget(client)
    await client.patch(f"/widgets/{widget['id']}", json={"status": "paused"}, headers=headers)
    resp = await client.post("/submissions", json={"widget_id": widget["id"], "fields": {"email": "a@b.com"}})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_valid_submission_succeeds(client):
    widget, _ = await _create_active_widget(client)
    resp = await client.post("/submissions", json={"widget_id": widget["id"], "fields": {"email": "a@b.com"}})
    assert resp.status_code == 201
    assert "id" in resp.json()


# ---------------------------------------------------------------------------
# 4b — Abuse protection: rate limiting + honeypot
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_per_ip_rate_limit_returns_429_but_service_stays_up(client):
    """Test env sets SUBMISSION_RATE_LIMIT_PER_IP=10/minute. Use many DIFFERENT
    widgets so the per-widget limiter (5/minute) doesn't confound this test —
    each widget's own counter stays low; only the shared per-IP counter climbs."""
    payload_widgets = [(await _create_active_widget(client))[0] for _ in range(12)]

    statuses = []
    for widget in payload_widgets:
        resp = await client.post("/submissions", json={"widget_id": widget["id"], "fields": {"email": "a@b.com"}})
        statuses.append(resp.status_code)

    assert 429 in statuses
    assert statuses.count(201) >= 1

    # The burst never took the service down — an unrelated endpoint still works.
    health_resp = await client.get("/health/live")
    assert health_resp.status_code == 200


@pytest.mark.asyncio
async def test_per_widget_rate_limit_returns_429_under_burst(client):
    """Test env sets SUBMISSION_RATE_LIMIT_PER_WIDGET=5/minute. Only 8 total
    requests here, well under the per-IP limit of 10/minute, so this isolates
    the per-widget dimension specifically."""
    widget, _ = await _create_active_widget(client)
    payload = {"widget_id": widget["id"], "fields": {"email": "a@b.com"}}

    statuses = [(await client.post("/submissions", json=payload)).status_code for _ in range(8)]

    assert 429 in statuses
    assert statuses.count(201) >= 1


@pytest.mark.asyncio
async def test_honeypot_filled_submission_is_dropped_not_stored(client, db_session):
    from sqlalchemy import select

    widget, _ = await _create_active_widget(client)
    resp = await client.post(
        "/submissions",
        json={"widget_id": widget["id"], "fields": {"email": "bot@spam.com"}, "honeypot": "I am a bot"},
    )
    # Looks like success to the bot...
    assert resp.status_code == 201

    # ...but nothing was actually stored.
    result = await db_session.execute(select(Submission).where(Submission.widget_id == uuid.UUID(widget["id"])))
    assert result.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# 4c — Enrichment fallback chain
# ---------------------------------------------------------------------------


class _AlwaysFailsProvider:
    name = "mock_always_fails"

    async def lookup(self, ip_address: str):
        return None


class _AlwaysAnswersProvider:
    name = "mock_always_answers"

    async def lookup(self, ip_address: str):
        return GeoResult(country="Wonderland", city="Rabbit Hole")


@pytest.mark.asyncio
async def test_enrichment_falls_back_to_provider_b_when_a_fails(client, db_session):
    from sqlalchemy import select

    async def override_chain():
        return GeoFallbackChain([_AlwaysFailsProvider(), _AlwaysAnswersProvider()])

    app.dependency_overrides[get_geo_chain] = override_chain
    try:
        widget, _ = await _create_active_widget(client)
        resp = await client.post("/submissions", json={"widget_id": widget["id"], "fields": {"email": "a@b.com"}})
        assert resp.status_code == 201
        submission_id = resp.json()["id"]
    finally:
        app.dependency_overrides.pop(get_geo_chain, None)

    result = await db_session.execute(select(Submission).where(Submission.id == uuid.UUID(submission_id)))
    submission = result.scalar_one()
    assert submission.geo_country == "Wonderland"
    assert submission.geo_city == "Rabbit Hole"
    assert submission.geo_provider_used == "mock_always_answers"


@pytest.mark.asyncio
async def test_enrichment_stores_submission_without_geo_when_all_providers_fail(client, db_session):
    from sqlalchemy import select

    async def override_chain():
        return GeoFallbackChain([_AlwaysFailsProvider(), _AlwaysFailsProvider()])

    app.dependency_overrides[get_geo_chain] = override_chain
    try:
        widget, _ = await _create_active_widget(client)
        resp = await client.post("/submissions", json={"widget_id": widget["id"], "fields": {"email": "a@b.com"}})
        assert resp.status_code == 201  # degrades, never fails
        submission_id = resp.json()["id"]
    finally:
        app.dependency_overrides.pop(get_geo_chain, None)

    result = await db_session.execute(select(Submission).where(Submission.id == uuid.UUID(submission_id)))
    submission = result.scalar_one()
    assert submission.geo_country is None
    assert submission.geo_city is None
    assert submission.geo_provider_used is None


# ---------------------------------------------------------------------------
# 4d — Safe side effects
# ---------------------------------------------------------------------------


class _AlwaysFailsNotifier:
    async def notify_new_submission(self, **kwargs):
        raise RuntimeError("simulated notification outage")


@pytest.mark.asyncio
async def test_failing_notification_does_not_block_submission(client, db_session):
    from sqlalchemy import select

    async def override_notifier():
        return _AlwaysFailsNotifier()

    app.dependency_overrides[get_notifier] = override_notifier
    try:
        widget, _ = await _create_active_widget(client)
        resp = await client.post("/submissions", json={"widget_id": widget["id"], "fields": {"email": "a@b.com"}})
        assert resp.status_code == 201  # the submission still succeeds
        submission_id = resp.json()["id"]
    finally:
        app.dependency_overrides.pop(get_notifier, None)

    result = await db_session.execute(select(Submission).where(Submission.id == uuid.UUID(submission_id)))
    submission = result.scalar_one()
    assert submission.notification_status == NotificationStatus.FAILED


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_idempotent_resubmission_returns_same_row_not_a_duplicate(client, db_session):
    from sqlalchemy import func, select

    widget, _ = await _create_active_widget(client)
    key = "test-idempotency-key-123"
    payload = {"widget_id": widget["id"], "fields": {"email": "a@b.com"}, "idempotency_key": key}

    first = await client.post("/submissions", json=payload)
    second = await client.post("/submissions", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    count_result = await db_session.execute(
        select(func.count()).select_from(Submission).where(Submission.widget_id == uuid.UUID(widget["id"]))
    )
    assert count_result.scalar_one() == 1
