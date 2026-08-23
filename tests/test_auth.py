import pytest


@pytest.mark.asyncio
async def test_register_creates_tenant_and_returns_token(client):
    resp = await client.post(
        "/auth/register",
        json={"tenant_name": "Acme Inc", "email": "owner@acme.com", "password": "supersecret123"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body and body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_rejects_short_password(client):
    resp = await client.post(
        "/auth/register",
        json={"tenant_name": "Acme", "email": "short@acme.com", "password": "abc"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_duplicate_email_rejected(client):
    payload = {"tenant_name": "Acme", "email": "dupe@acme.com", "password": "supersecret123"}
    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/auth/register", json=payload)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_login_wrong_password_rejected(client):
    await client.post(
        "/auth/register",
        json={"tenant_name": "Beta", "email": "beta@example.com", "password": "correcthorsebattery"},
    )
    resp = await client.post("/auth/login", json={"email": "beta@example.com", "password": "wrongpassword"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_rejected_with_same_error(client):
    resp = await client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever123"})
    assert resp.status_code == 401
