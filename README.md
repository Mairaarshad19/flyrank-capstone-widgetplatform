# Widget & Lead-Capture Platform

[![Tests](https://github.com/Mairaarshad19/Embeddable-Widget-Lead-Capture-Platform/actions/workflows/tests.yml/badge.svg)](https://github.com/Mairaarshad19/Embeddable-Widget-Lead-Capture-Platform/actions/workflows/tests.yml)

> Status: All 7 build phases complete — 46/46 tests passing, run against real Postgres in CI on every push.

Let a customer define an embeddable widget, hand them one `<script>` tag, and
safely accept submissions from any website on the public internet — validated,
rate-limited, spam-filtered, enriched with geolocation, and never lost to a
downstream failure.

This isn't a toy CRUD app. It's built the way a real public-facing intake API
has to be built: it assumes hostile input, unreliable third-party dependencies,
and traffic spikes, and it's designed to keep working anyway.

## Why this exists

Every SaaS company with a signup form, a chat bubble, or a popup lead form
(Intercom, Mailchimp, HubSpot...) runs this exact system under the hood: a
script snippet → a cached config endpoint → a hardened public submission API →
an owner dashboard. This is that system, built from scratch.

## Engineering priorities (in order)

1. **Reliability** — the API keeps answering correctly under bad input, a dead
   dependency, or a traffic burst. A broken third-party geo provider or a
   failing email side effect never breaks a submission.
2. **Data integrity** — every write is a single committed transaction (see
   `app/db/session.py`); no submission is ever partially written or silently
   dropped.
3. **Traffic handling** — bounded connection pooling, per-IP and per-widget
   rate limiting, cache headers on public read paths.
4. **Proper schema** — every table versioned through Alembic migrations, not
   `create_all()`; tenant isolation enforced at the query layer, not the UI.
5. Only after those: features.

## Architecture

```
Widget Owner (authenticated)
  -> Widget Management API -> Widget DB (tenant-isolated) -> embed snippet

Customer Website (any origin)
  -> <script src="widget.js?id=123">
  -> GET /widgets/:id/config   (public, cached, CORS)
  -> render + submit

Website Visitor
  -> POST /submissions   (public, CORS)
     -> validation         bad payload?  -> 4xx, never 500
     -> rate limit + spam  flood?        -> 429, service stays up
     -> geo enrichment     A fails       -> B -> both fail -> store anyway
     -> store (committed)
     -> notify (email/webhook)  fails?   -> logged, submission still succeeds

Widget Owner (authenticated)
  -> Dashboard API <- submissions + stats
```

## Local setup

```bash
cp .env.example .env          # fill in JWT_SECRET — see comment in the file
docker compose up --build     # builds app, starts Postgres, runs migrations
```

App: http://localhost:8000
Interactive API docs: http://localhost:8000/docs
Liveness: http://localhost:8000/health/live
Readiness (checks real DB round-trip): http://localhost:8000/health/ready

**Seed realistic demo data** (a tenant, 2 widgets, 25 submissions spread
across 2 weeks, geo-enriched, some with a failed notification — so the
dashboard shows something real immediately):

```bash
docker compose exec app python -m app.seed
```

This prints a login you can use straight away:
```
Login:   demo@acme-bakery-demo.io / demo-password-123
```
Safe to run more than once — it's a no-op if the demo tenant already exists
(see `tests/test_seed.py`, which proves this).

Run the test suite:
```bash
docker compose exec app pytest -v
```

**Try the actual widget rendering on a separate origin** (the whole point of
this capstone): log in as the demo user, `GET /widgets` to find a widget id,
paste it into `static/test-page/index.html` in place of `WIDGET_ID_HERE`,
then:
```bash
cd static/test-page && python3 -m http.server 5500
```
Open `http://localhost:5500` — the widget renders, fetched live from the API
on a page that has no other connection to it.

## API docs

Full interactive documentation, auto-generated from the code and therefore
always in sync: `http://localhost:8000/docs`

## Continuous integration

Every push runs the full test suite against a **real Postgres instance**, not
SQLite — see `.github/workflows/tests.yml`. This isn't decorative: a real bug
(SQLAlchemy storing enum names instead of values — see BUILDLOG.md's "Phase
2/3 hotfix") passed every test on SQLite and only surfaced against Postgres.
CI running on SQLite would have shipped that bug straight to `main`.

## Limitations

Deliberate scope cuts, not oversights — see `DESIGN.md` § 6 for the reasoning:

- **No visual widget builder.** Widgets are configured via JSON in the API
  request body, not a drag-and-drop GUI. This is a backend capstone; the
  effort went into the submission path's reliability, not a form designer.
- **No real hosting/CDN/domain.** Everything runs locally via Docker Compose;
  the "customer site" is a plain HTML file on a second local port, exactly as
  the brief specifies.
- **Email/webhook notifications are a console log by default** (`ConsoleNotifier`).
  A real `WebhookNotifier` exists (`app/notifications/webhook.py`) and is a
  one-env-var swap (`NOTIFY_BACKEND=webhook`), but what's graded here is that
  a *failing* side effect never breaks a submission — not the delivery
  mechanism itself.
- **Rate limiting is in-process memory**, not Redis-backed. Explicitly
  documented as a one-file swap in `app/core/rate_limit.py`'s docstring —
  correct for a single instance, would need a shared backend the moment this
  runs on more than one.
- **No production email deliverability, GDPR export/delete, or bot CAPTCHA
  challenge** — these are the natural "if I kept going" additions (see
  `capstone.yaml`'s scope and the stretch-goal ideas in the original capstone
  brief), deliberately cut to keep effort focused on submission-path
  reliability over feature breadth.

## Project layout

```
app/
  core/          config, logging, security, rate limiting
  db/            session management, base model
  models/        SQLAlchemy ORM models
  schemas/       Pydantic request/response schemas
  api/           FastAPI routers
  services/      business logic (framework-agnostic)
  repositories/  DB access, always tenant-scoped
  enrichment/    geo provider clients + fallback chain
  notifications/ safe side-effect delivery (email/webhook)
  seed.py        idempotent demo data script
alembic/         schema migrations
static/widget/   embeddable widget.js + customer test page
tests/
.github/workflows/ CI: full suite against real Postgres on every push
```

## Status

- [x] Phase 0 — foundations: config, logging, DB pooling, health checks, Docker, CI-ready test setup
- [x] Phase 1 — design doc: data model, tenancy rule, idempotency strategy, API surface (see `DESIGN.md`)
- [x] Phase 2 — auth (JWT), tenant isolation, full widget CRUD — 12/12 tests passing
- [x] Phase 3 — embed snippet, cached public config delivery, versioned widget.js, test page — 19/19 tests passing
- [x] Phase 4 — hardened public submission path: CORS, validation, rate limiting, spam control, geo fallback chain, safe side effects, idempotency — 38/38 tests passing
- [x] Phase 5 — owner dashboard: paginated submissions, stats (per-day, per-widget, per-country), tenant-isolated — 44/44 tests passing
- [x] Phase 6 — CI (real Postgres), seed script (verified idempotent), full docs, submission pack — 46/46 tests passing
- [ ] Phase 7 — demo prep
