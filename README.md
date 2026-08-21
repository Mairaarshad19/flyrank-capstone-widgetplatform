# Widget & Lead-Capture Platform

> Status: 🚧 in progress — Phase 0 (foundations) complete.

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
cp .env.example .env          # fill in JWT_SECRET (see comment in the file)
docker compose up --build     # builds app, starts Postgres, runs migrations
```

App: http://localhost:8000
Interactive API docs: http://localhost:8000/docs
Liveness: http://localhost:8000/health/live
Readiness (checks real DB round-trip): http://localhost:8000/health/ready

Seed demo data (added in Phase 6):
```bash
docker compose exec app python -m app.seed
```

Run tests:
```bash
docker compose exec app pytest -q
```

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
alembic/         schema migrations
static/widget/   embeddable widget.js + test HTML page
tests/
```

## Limitations

_(filled in honestly as of Phase 6 — this capstone deliberately does not
attempt a visual widget builder, real hosting/CDN, or a production email
provider; see `DESIGN.md` for the full non-goals list.)_

## Status

- [x] Phase 0 — foundations: config, logging, DB pooling, health checks, Docker, CI-ready test setup
- [ ] Phase 1 — design doc
- [ ] Phase 2 — auth, tenancy, widget CRUD
- [ ] Phase 3 — embed snippet & cached delivery
- [ ] Phase 4 — hardened public submission path
- [ ] Phase 5 — dashboard & analytics
- [ ] Phase 6 — tests, docs, submission pack
- [ ] Phase 7 — demo prep
