import uuid

import pytest


async def _create_active_widget(client):
    reg = await client.post(
        "/auth/register",
        json={"tenant_name": "Acme", "email": "pub@acme.com", "password": "supersecret123"},
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    created = (
        await client.post(
            "/widgets",
            json={"type": "signup_form", "title": "Newsletter", "config": {"fields": ["email"], "button_text": "Join"}},
            headers=headers,
        )
    ).json()
    return created, headers


@pytest.mark.asyncio
async def test_public_config_returns_active_widget_with_cache_headers(client):
    widget, _ = await _create_active_widget(client)
    resp = await client.get(f"/widgets/{widget['id']}/config")
    assert resp.status_code == 200
    assert resp.headers["cache-control"] == "public, max-age=60"
    assert "etag" in resp.headers
    body = resp.json()
    assert body["config"]["fields"] == ["email"]


@pytest.mark.asyncio
async def test_public_config_requires_no_auth(client):
    widget, _ = await _create_active_widget(client)
    # Deliberately no Authorization header — this is what a stranger's browser sends.
    resp = await client.get(f"/widgets/{widget['id']}/config")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_public_config_404_for_paused_widget(client):
    widget, headers = await _create_active_widget(client)
    await client.patch(f"/widgets/{widget['id']}", json={"status": "paused"}, headers=headers)
    resp = await client.get(f"/widgets/{widget['id']}/config")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_public_config_404_for_nonexistent_widget(client):
    resp = await client.get(f"/widgets/{uuid.uuid4()}/config")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_public_config_returns_304_when_etag_matches(client):
    widget, _ = await _create_active_widget(client)
    first = await client.get(f"/widgets/{widget['id']}/config")
    etag = first.headers["etag"]

    second = await client.get(f"/widgets/{widget['id']}/config", headers={"If-None-Match": etag})
    assert second.status_code == 304


@pytest.mark.asyncio
async def test_etag_changes_when_config_is_updated(client):
    widget, headers = await _create_active_widget(client)
    first = await client.get(f"/widgets/{widget['id']}/config")
    etag_before = first.headers["etag"]

    await client.patch(f"/widgets/{widget['id']}", json={"config": {"fields": ["email", "name"]}}, headers=headers)

    second = await client.get(f"/widgets/{widget['id']}/config")
    assert second.headers["etag"] != etag_before
    assert second.json()["config"]["fields"] == ["email", "name"]


@pytest.mark.asyncio
async def test_widget_bundle_served_with_long_immutable_cache(client):
    resp = await client.get("/static/widget/widget.v1.js")
    assert resp.status_code == 200
    assert "max-age=31536000" in resp.headers["cache-control"]
    assert "immutable" in resp.headers["cache-control"]
    assert "javascript" in resp.headers["content-type"]
    assert "flyrank-widget" in resp.text
