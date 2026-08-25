import uuid

import pytest

from app.api.submissions import get_geo_chain
from app.enrichment.base import GeoResult
from app.enrichment.chain import GeoFallbackChain
from app.main import app


async def _register_and_headers(client, email: str):
    reg = await client.post(
        "/auth/register", json={"tenant_name": f"Tenant-{email}", "email": email, "password": "supersecret123"}
    )
    token = reg.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_widget(client, headers, title="Widget"):
    resp = await client.post(
        "/widgets", json={"type": "signup_form", "title": title, "config": {"fields": ["email"]}}, headers=headers
    )
    return resp.json()


async def _submit(client, widget_id: str, email: str):
    resp = await client.post("/submissions", json={"widget_id": widget_id, "fields": {"email": email}})
    assert resp.status_code == 201
    return resp.json()


class _FixedCountryProvider:
    def __init__(self, country: str, city: str):
        self.name = "mock_fixed"
        self._country = country
        self._city = city

    async def lookup(self, ip_address: str):
        return GeoResult(country=self._country, city=self._city)


@pytest.mark.asyncio
async def test_dashboard_routes_require_auth(client):
    resp = await client.get("/dashboard/submissions")
    assert resp.status_code in (401, 403)

    resp2 = await client.get("/dashboard/stats")
    assert resp2.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_submissions_scoped_to_tenant_and_paginated(client):
    headers_a = await _register_and_headers(client, "dash-a1@acme.com")
    headers_b = await _register_and_headers(client, "dash-b1@globex.com")

    widget_a = await _create_widget(client, headers_a)
    widget_b = await _create_widget(client, headers_b)

    await _submit(client, widget_a["id"], "one@x.com")
    await _submit(client, widget_a["id"], "two@x.com")
    await _submit(client, widget_a["id"], "three@x.com")
    await _submit(client, widget_b["id"], "other-tenant@y.com")

    resp = await client.get("/dashboard/submissions", headers=headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3
    # Tenant B's submission must never appear here.
    assert all(item["widget_id"] == widget_a["id"] for item in body["items"])

    # Pagination actually limits.
    resp_paginated = await client.get("/dashboard/submissions?limit=2&offset=0", headers=headers_a)
    body_paginated = resp_paginated.json()
    assert len(body_paginated["items"]) == 2
    assert body_paginated["total"] == 3  # total reflects the full set, not just this page


@pytest.mark.asyncio
async def test_list_submissions_filter_by_widget_id(client):
    headers = await _register_and_headers(client, "dash-filter@acme.com")
    widget_1 = await _create_widget(client, headers, title="Widget One")
    widget_2 = await _create_widget(client, headers, title="Widget Two")

    await _submit(client, widget_1["id"], "a@x.com")
    await _submit(client, widget_1["id"], "b@x.com")
    await _submit(client, widget_2["id"], "c@x.com")

    resp = await client.get(f"/dashboard/submissions?widget_id={widget_1['id']}", headers=headers)
    body = resp.json()
    assert body["total"] == 2
    assert all(item["widget_id"] == widget_1["id"] for item in body["items"])


@pytest.mark.asyncio
async def test_stats_aggregation_totals_and_per_widget_breakdown(client):
    headers = await _register_and_headers(client, "dash-stats@acme.com")
    widget_1 = await _create_widget(client, headers, title="Newsletter")
    widget_2 = await _create_widget(client, headers, title="Contact")

    await _submit(client, widget_1["id"], "a@x.com")
    await _submit(client, widget_1["id"], "b@x.com")
    await _submit(client, widget_2["id"], "c@x.com")

    resp = await client.get("/dashboard/stats", headers=headers)
    assert resp.status_code == 200
    body = resp.json()

    assert body["total_submissions"] == 3

    by_widget = {row["widget_title"]: row["count"] for row in body["submissions_by_widget"]}
    assert by_widget["Newsletter"] == 2
    assert by_widget["Contact"] == 1

    # All 3 submissions happened today, so there should be exactly one day bucket.
    assert len(body["submissions_by_day"]) == 1
    assert body["submissions_by_day"][0]["count"] == 3


@pytest.mark.asyncio
async def test_stats_geo_breakdown_matches_enriched_data(client):
    async def override_chain():
        return GeoFallbackChain([_FixedCountryProvider("Pakistan", "Lahore")])

    app.dependency_overrides[get_geo_chain] = override_chain
    try:
        headers = await _register_and_headers(client, "dash-geo@acme.com")
        widget = await _create_widget(client, headers)
        await _submit(client, widget["id"], "a@x.com")
        await _submit(client, widget["id"], "b@x.com")
    finally:
        app.dependency_overrides.pop(get_geo_chain, None)

    resp = await client.get("/dashboard/stats", headers=headers)
    body = resp.json()
    by_country = {row["country"]: row["count"] for row in body["submissions_by_country"]}
    assert by_country["Pakistan"] == 2


@pytest.mark.asyncio
async def test_stats_are_isolated_per_tenant(client):
    headers_a = await _register_and_headers(client, "dash-iso-a@acme.com")
    headers_b = await _register_and_headers(client, "dash-iso-b@globex.com")

    widget_a = await _create_widget(client, headers_a)
    widget_b = await _create_widget(client, headers_b)

    await _submit(client, widget_a["id"], "a1@x.com")
    await _submit(client, widget_a["id"], "a2@x.com")
    await _submit(client, widget_b["id"], "b1@y.com")

    stats_a = (await client.get("/dashboard/stats", headers=headers_a)).json()
    stats_b = (await client.get("/dashboard/stats", headers=headers_b)).json()

    assert stats_a["total_submissions"] == 2
    assert stats_b["total_submissions"] == 1
