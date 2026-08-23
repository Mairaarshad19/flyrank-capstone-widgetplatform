import pytest


async def _register_and_get_token(client, tenant_name: str, email: str) -> str:
    resp = await client.post(
        "/auth/register",
        json={"tenant_name": tenant_name, "email": email, "password": "supersecret123"},
    )
    assert resp.status_code == 201
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_create_and_get_widget(client):
    token = await _register_and_get_token(client, "Acme", "a@acme.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post(
        "/widgets",
        json={"type": "signup_form", "title": "Newsletter", "config": {"fields": ["email"]}},
        headers=headers,
    )
    assert create_resp.status_code == 201
    widget = create_resp.json()
    assert widget["title"] == "Newsletter"
    assert widget["version"] == 1
    assert widget["embed_snippet"].startswith("<script")

    get_resp = await client.get(f"/widgets/{widget['id']}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == widget["id"]


@pytest.mark.asyncio
async def test_update_widget_bumps_version_on_config_change(client):
    token = await _register_and_get_token(client, "Acme", "v@acme.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = (
        await client.post("/widgets", json={"type": "cta", "title": "Promo"}, headers=headers)
    ).json()
    assert created["version"] == 1

    updated = (
        await client.patch(
            f"/widgets/{created['id']}", json={"config": {"button_text": "Buy now"}}, headers=headers
        )
    ).json()
    assert updated["version"] == 2

    # A title-only change should NOT bump the version — only config changes do.
    updated_again = (
        await client.patch(f"/widgets/{created['id']}", json={"title": "Promo v2"}, headers=headers)
    ).json()
    assert updated_again["version"] == 2


@pytest.mark.asyncio
async def test_delete_widget(client):
    token = await _register_and_get_token(client, "Acme", "d@acme.com")
    headers = {"Authorization": f"Bearer {token}"}
    created = (await client.post("/widgets", json={"type": "popover", "title": "Bye"}, headers=headers)).json()

    delete_resp = await client.delete(f"/widgets/{created['id']}", headers=headers)
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/widgets/{created['id']}", headers=headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_widget_routes_require_auth(client):
    resp = await client.get("/widgets")
    assert resp.status_code in (401, 403)

    resp2 = await client.post("/widgets", json={"type": "cta", "title": "x"})
    assert resp2.status_code in (401, 403)


@pytest.mark.asyncio
async def test_cross_tenant_widget_access_returns_404_not_403(client):
    """The single most important test in this capstone: tenant B must not be
    able to read, list, update, or delete tenant A's widget — and the response
    must be 404 (not found), never 403 (forbidden, which would confirm the
    resource exists)."""
    token_a = await _register_and_get_token(client, "Acme", "isoA@acme.com")
    token_b = await _register_and_get_token(client, "Globex", "isoB@globex.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    created = (
        await client.post(
            "/widgets", json={"type": "cta", "title": "Tenant A Secret Widget"}, headers=headers_a
        )
    ).json()
    widget_id = created["id"]

    # Tenant B cannot read it
    get_resp = await client.get(f"/widgets/{widget_id}", headers=headers_b)
    assert get_resp.status_code == 404

    # Tenant B cannot update it
    patch_resp = await client.patch(f"/widgets/{widget_id}", json={"title": "hijacked"}, headers=headers_b)
    assert patch_resp.status_code == 404

    # Tenant B cannot delete it
    delete_resp = await client.delete(f"/widgets/{widget_id}", headers=headers_b)
    assert delete_resp.status_code == 404

    # Tenant B's own widget list must not contain tenant A's widget
    list_resp = await client.get("/widgets", headers=headers_b)
    assert all(w["id"] != widget_id for w in list_resp.json())

    # Tenant A can still read their own widget after all of tenant B's attempts
    still_there = await client.get(f"/widgets/{widget_id}", headers=headers_a)
    assert still_there.status_code == 200
