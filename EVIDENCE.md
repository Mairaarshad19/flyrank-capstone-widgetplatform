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
_(Phase 2)_

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
