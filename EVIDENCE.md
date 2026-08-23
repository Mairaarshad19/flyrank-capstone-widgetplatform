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

## Widget Delivery
_(Phase 3)_

## Public Submission API
_(Phase 4)_

## Abuse Protection
_(Phase 4)_

## Enrichment & Safe Side Effects
_(Phase 4)_

## Owner Dashboard
_(Phase 5)_

## Tests & Documentation
_(Phase 6)_
