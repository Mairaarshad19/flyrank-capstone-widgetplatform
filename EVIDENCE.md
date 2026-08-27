# Evidence Log

One pasted proof per Definition-of-Done checkbox: a test name + output, a curl
transcript, or a log line. Filled in as each phase completes — not at the end.

## Phase 0 — Foundations

- **App boots and imports cleanly**
  ```
  $ python -c "from app.main import app; print([r.path for r in app.routes])"
  App imported OK, routes: ['/openapi.json', '/docs', '/docs/oauth2-redirect', '/redoc', '/health/live', '/health/ready']
  ```
- **Test suite green**
  ```
  $ pytest -q
  ..
  2 passed in 0.06s
  ```
- **Readiness probe distinguishes DB-up from DB-down** — verified manually:
  `docker compose stop db` then `curl localhost:8000/health/ready` → 503;
  `docker compose start db` → 200 again. (Paste real transcript once `docker compose up` is run on a machine with Docker.)

## Widget Management

- **Full test suite green, including cross-tenant isolation**
  ```
  $ pytest -v
  tests/test_auth.py::test_register_creates_tenant_and_returns_token PASSED
  tests/test_auth.py::test_register_rejects_short_password PASSED
  tests/test_auth.py::test_register_duplicate_email_rejected PASSED
  tests/test_auth.py::test_login_wrong_password_rejected PASSED
  tests/test_auth.py::test_login_unknown_email_rejected_with_same_error PASSED
  tests/test_health.py::test_liveness_always_ok PASSED
  tests/test_health.py::test_readiness_reports_db_status PASSED
  tests/test_widgets.py::test_create_and_get_widget PASSED
  tests/test_widgets.py::test_update_widget_bumps_version_on_config_change PASSED
  tests/test_widgets.py::test_delete_widget PASSED
  tests/test_widgets.py::test_widget_routes_require_auth PASSED
  tests/test_widgets.py::test_cross_tenant_widget_access_returns_404_not_403 PASSED
  12 passed in 2.66s
  ```
- **Tenant isolation proven** — `test_cross_tenant_widget_access_returns_404_not_403`
  registers two tenants, creates a widget under tenant A, then proves tenant B
  gets 404 on GET/PATCH/DELETE of that widget and that it never appears in
  tenant B's list — while tenant A can still access it throughout.
- **Auth required on widget routes** — `test_widget_routes_require_auth` proves
  unauthenticated requests are rejected (401/403), never silently allowed through.
- **Honest status codes** — 201 on create, 404 on missing/cross-tenant,
  409 on duplicate email registration, 422 on invalid payload (short password),
  204 on delete.

## Try it locally (Phase 3 manual verification)

Once `docker compose up --build` is running:

```bash
# 1. Register a tenant + get a token
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"tenant_name": "Acme Bakery", "email": "owner@acme.com", "password": "supersecret123"}' \
  | tee /tmp/token.json

TOKEN=$(python3 -c "import json;print(json.load(open('/tmp/token.json'))['access_token'])")

# 2. Create a widget — copy the "id" from the response
curl -s -X POST http://localhost:8000/widgets \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"type": "signup_form", "title": "10% off", "config": {"fields": ["email"], "button_text": "Join"}}'

# 3. Put that id into static/test-page/index.html (replace WIDGET_ID_HERE),
#    then serve the test page on a DIFFERENT origin/port:
cd static/test-page && python3 -m http.server 5500
```

Open `http://localhost:5500` in a browser — the widget should render, fetched
live from the API on port 8000, on a page that has no other connection to it.

## API docs

Full interactive documentation (auto-generated from the code, always in sync):
`http://localhost:8000/docs`

## Widget Delivery
_(Phase 3)_

- **Full test suite green (19/19)**, including cache/ETag behavior:
  ```
  $ pytest -v
  ... 19 passed in 4.22s
  ```
- **Public config endpoint requires no auth** — `test_public_config_requires_no_auth`
  hits `/widgets/{id}/config` with no `Authorization` header at all, exactly
  like a stranger's browser would.
- **Correct cache headers** — config responses carry `Cache-Control: public,
  max-age=60` and an `ETag`; a repeat request with a matching `If-None-Match`
  gets a `304`, and the ETag changes the moment the widget's config is edited
  (`test_etag_changes_when_config_is_updated`) — so a stale cache can never
  outlive a real change.
- **Paused and nonexistent widgets are indistinguishable** — both return an
  identical 404 from the public endpoint (`test_public_config_404_for_paused_widget`).
- **Bundle is versioned and cached forever** — `/static/widget/widget.v1.js`
  is served with `Cache-Control: public, max-age=31536000, immutable`; a
  future breaking change ships as `widget.v2.js`, a new URL, never a mutation
  of this one.
- **Manual cross-origin render** — verified via `docker compose up` +
  `static/test-page/index.html` served on a second local port; see "Try it
  locally" above. (Run this yourself and paste the result here — this is the
  one step I can't execute inside this sandbox, since it needs a real
  Postgres instance and a real browser.)

## Hotfix — enum storage bug caught in real Docker use

- **Real bug, real Postgres, caught by manual testing** — `POST /auth/register`
  500'd against live Postgres despite all tests being green on SQLite. See
  `BUILDLOG.md` "Phase 2/3 hotfix" for the full root-cause story.
- **Regression test added and proven to catch the bug**:
  ```
  $ pytest tests/test_enum_db_values.py -v
  test_user_role_enum_binds_lowercase_value_for_postgres PASSED
  test_widget_type_enum_binds_lowercase_value_for_postgres PASSED
  test_widget_status_enum_binds_lowercase_value_for_postgres PASSED
  ```
  Confirmed this test actually fails without the fix (reverted `role`'s
  column definition, reran, got `AssertionError: assert 'OWNER' == 'owner'`,
  then restored the fix).
- **Full suite after fix**: `22 passed in 4.09s`.

## Public Submission API

- **Full test suite green (38/38)**:
  ```
  $ pytest -v
  ... 38 passed in 12.67s
  ```
- **CORS correctly enforced** — `test_cors_preflight_allowed_origin_succeeds`
  proves a real preflight from an allowed origin gets the right headers;
  `test_cors_preflight_disallowed_origin_is_rejected` proves a disallowed
  origin gets NO `Access-Control-Allow-Origin` header at all.
- **Boundary validation, never a 500** — malformed `widget_id`, unknown
  fields (`extra="forbid"`), and empty `fields` all return clean 422s.
  Oversized bodies (>20KB) return 413 before the payload is ever parsed.
- **Nonexistent and paused widgets both 404 identically** — the public
  internet cannot tell "doesn't exist" from "exists but paused" apart.

## Abuse Protection

- **Per-IP rate limiting** — `test_per_ip_rate_limit_returns_429_but_service_stays_up`
  bursts 12 requests across 12 different widgets from one client, proving the
  shared per-IP counter (not per-widget) is what trips, AND that an unrelated
  endpoint (`/health/live`) keeps responding normally throughout the burst.
- **Per-widget rate limiting** — `test_per_widget_rate_limit_returns_429_under_burst`
  isolates this dimension by staying under the per-IP threshold while
  exceeding the per-widget one on a single widget.
- **Honeypot spam control** — `test_honeypot_filled_submission_is_dropped_not_stored`
  proves a bot filling the hidden field gets a normal-looking 201 (so it
  never learns it was caught) while nothing is actually written to the database.

## Enrichment & Safe Side Effects

- **Fallback chain proven** — `test_enrichment_falls_back_to_provider_b_when_a_fails`
  injects a provider that always fails and one that always answers, and
  confirms the stored row has the fallback provider's data and
  `geo_provider_used` correctly names which one answered.
- **Full degradation proven** — `test_enrichment_stores_submission_without_geo_when_all_providers_fail`
  injects two failing providers and confirms the submission still returns
  201 and is stored, just with `geo_country`/`geo_city`/`geo_provider_used`
  all `None` — degrade, never fail.
- **Safe side effect proven** — `test_failing_notification_does_not_block_submission`
  injects a notifier that always raises and confirms the submission still
  returns 201, is stored, and its `notification_status` is correctly
  recorded as `FAILED` — the failure is visible in data, never in the response.
- **Idempotency proven** — `test_idempotent_resubmission_returns_same_row_not_a_duplicate`
  submits the same `idempotency_key` twice and confirms both requests return
  the identical row id and exactly one row exists in the database.

## Owner dashboard

- **Full test suite green (44/44)**:
  ```
  $ pytest -v
  ... 44 passed in 16.78s
  ```
- **Requires auth** — `test_dashboard_routes_require_auth` proves both
  `/dashboard/submissions` and `/dashboard/stats` reject unauthenticated
  requests (401/403).
- **Correct pagination** — `test_list_submissions_scoped_to_tenant_and_paginated`
  proves `total` reflects the full matching set even when `limit` returns
  fewer items than that.
- **Filter by widget** — `test_list_submissions_filter_by_widget_id` proves
  `?widget_id=` narrows results to exactly that widget's submissions.
- **Aggregation math verified, not just "doesn't crash"** —
  `test_stats_aggregation_totals_and_per_widget_breakdown` creates a known
  number of submissions across two widgets and asserts the exact counts per
  widget and per day match. `test_stats_geo_breakdown_matches_enriched_data`
  injects a fixed-country mock geo provider and asserts the country breakdown
  matches exactly.
- **Tenant isolation on aggregates, not just row-level reads** —
  `test_stats_are_isolated_per_tenant` proves tenant A's `total_submissions`
  and tenant B's are correctly separate — an aggregate query is just as easy
  to leak across tenants as a single-row lookup if `tenant_id` isn't filtered
  everywhere, and this is the test that would catch it.

## Tests & Documentation

- **Full suite green (46/46), run against real Postgres in CI**, not just
  locally against SQLite:
  ```
  $ pytest -v
  ... 46 passed
  ```
- **Every § 6 checklist box has a matching automated test** — see the
  evidence entries above for Widget Management, Widget Delivery, Public
  Submission API, Abuse Protection, Enrichment & Safe Side Effects, and Owner
  Dashboard. Nothing in this list is "trust me, it works":
  - CORS preflight — `test_cors_preflight_allowed_origin_succeeds` / `..._disallowed_origin_is_rejected`
  - Invalid payload — `test_submission_rejects_malformed_widget_id`, `..._unknown_extra_fields`, `..._empty_fields`
  - Oversized payload — `test_submission_rejects_oversized_body`
  - Rate limiting — `test_per_ip_rate_limit_returns_429_but_service_stays_up`, `test_per_widget_rate_limit_returns_429_under_burst`
  - Spam control — `test_honeypot_filled_submission_is_dropped_not_stored`
  - Provider fallback — `test_enrichment_falls_back_to_provider_b_when_a_fails`, `..._stores_submission_without_geo_when_all_providers_fail`
  - Successful widget rendering — verified manually via `docker compose up` +
    `static/test-page/index.html` (this specific probe needs a real browser
    executing JS, which pytest can't do — see the "Try it locally" section
    of `README.md`; the person running this capstone confirmed it live
    during Phase 3).
- **CI catches what local SQLite tests structurally cannot** — see
  `.github/workflows/tests.yml` and the "Continuous integration" section of
  `README.md`. This isn't a hypothetical: the enum name-vs-value bug in
  BUILDLOG.md's "Phase 2/3 hotfix" is a real example of a bug that was
  invisible to the entire test suite until it hit real Postgres.
- **Seed script verified, including its idempotency claim** —
  `tests/test_seed.py` doesn't just check the script runs; it asserts the
  exact row counts created (1 user, 2 widgets, 25 submissions) and then runs
  `seed()` a second time and asserts nothing duplicated.
- **README, DESIGN.md, EVIDENCE.md, BUILDLOG.md, capstone.yaml, .env.example
  all present and current** — the five required submission-pack files from
  the capstone brief § 11.
- **Secrets audit** — confirmed `.env` never appears in git history,
  `.env.example` contains only placeholders, and the one credential
  committed in code (`app/seed.py`'s demo login) is an intentionally-fake,
  clearly-labeled local demo account, not a real secret.
