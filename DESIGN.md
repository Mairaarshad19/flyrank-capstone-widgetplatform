# Design Doc — Widget & Lead-Capture Platform

## 1. Problem statement

A customer (tenant) needs to collect leads from their own website without
building any backend themselves. They configure a widget on our platform, get
one `<script>` tag, and every visitor submission on their site has to reach
us, survive validation and abuse, and end up safely stored and visible on
their dashboard — even though we don't control the visitor's browser, their
network, or how much traffic hits us at once.

## 2. Data model

Four tables. Every table that isn't `tenants` itself carries a `tenant_id`,
even where it could be derived through a join — see § 3 for why.

### `tenants`
| column | type | notes |
|---|---|---|
| id | UUID, PK | |
| name | text | |
| slug | text, unique, indexed | used in URLs / embed script query params |
| created_at | timestamptz | |

### `users`
| column | type | notes |
|---|---|---|
| id | UUID, PK | |
| tenant_id | UUID, FK → tenants, **indexed** | a user belongs to exactly one tenant |
| email | text, **unique index** | login identity |
| hashed_password | text | bcrypt, never logged, never returned in any response |
| role | enum(`owner`, `member`) | room to add roles later without a migration |
| created_at | timestamptz | |

### `widgets`
| column | type | notes |
|---|---|---|
| id | UUID, PK | this is the `id` in `widget.js?id=...` |
| tenant_id | UUID, FK → tenants, **indexed** | |
| type | enum(`signup_form`, `cta`, `popover`) | |
| title, description | text | |
| config | JSONB | form fields, button text, display options — see § 5 non-goal |
| status | enum(`active`, `paused`) | paused widgets stop accepting submissions |
| version | integer, default 1, incremented on every config change | drives cache-busting on the public config endpoint (Phase 3) |
| created_at, updated_at | timestamptz | |
| **index** | `(tenant_id, status)` | powers "list my active widgets" — the most common owner-side query |

### `submissions`
| column | type | notes |
|---|---|---|
| id | UUID, PK | |
| widget_id | UUID, FK → widgets, **indexed** | |
| tenant_id | UUID, FK → tenants, **indexed, denormalized** | see § 3 |
| payload | JSONB | the actual submitted form fields |
| ip_address | inet | source of enrichment, kept for abuse investigation |
| geo_country, geo_city | text, nullable | null when both providers fail — never blocks the write |
| geo_provider_used | text, nullable | `"provider_a"` / `"provider_b"` / `null` — makes fallback behavior auditable |
| idempotency_key | text, nullable | see § 4 |
| notification_status | enum(`sent`, `failed`, `skipped`) | records the side-effect outcome without ever affecting the row's own existence |
| created_at | timestamptz | |
| **index** | `(tenant_id, created_at)` | dashboard time-series and pagination — the hottest read path in the whole system |
| **index** | `(widget_id, created_at)` | per-widget stats |
| **unique index** | `(widget_id, idempotency_key)` where `idempotency_key IS NOT NULL` | see § 4 |

## 3. Tenancy rule (read this before writing any query)

**Every query against `widgets` or `submissions` filters by `tenant_id`,
sourced from the authenticated user's token — never from a client-supplied
value in the URL or body.**

`submissions.tenant_id` is intentionally denormalized (copied from the parent
widget at insert time) rather than requiring a join through `widgets` on every
read. Two reasons:
1. **Performance** — the dashboard's hottest query (`submissions` by
   `tenant_id` + date range) never needs a join.
2. **Defense in depth** — if a repository function ever forgets to join
   correctly, a direct `tenant_id` filter still can't leak another tenant's
   rows. A missing join fails differently than a missing `WHERE`, and the
   latter is the one that's actually safe to forget.

Cross-tenant access attempts return **404, not 403** — we don't confirm to
tenant A that a resource belonging to tenant B even exists.

## 4. Idempotency

A visitor's browser can retry a submission (flaky mobile network, accidental
double-click, a script auto-retrying a failed fetch). Without protection,
that becomes duplicate leads in the owner's dashboard — a real data-integrity
bug, not a cosmetic one.

The widget script generates a UUID **once**, before the first submit attempt,
and sends it as `idempotency_key`. The unique index on `(widget_id,
idempotency_key)` means a retried request with the same key either:
- fails the insert on a duplicate key, and the API catches that and returns
  the **original** stored submission instead of erroring, or
- is checked first with a lookup and short-circuited.

Net effect: the same physical submission is stored exactly once, no matter
how many times the network retries it.

## 5. The three request paths → API surface

```
Widget Owner (authenticated, JWT)
  POST   /auth/register
  POST   /auth/login
  POST   /widgets
  GET    /widgets
  GET    /widgets/{id}
  PATCH  /widgets/{id}
  DELETE /widgets/{id}
  GET    /dashboard/submissions
  GET    /dashboard/stats

Customer Website (any origin, public, cached)
  GET    /widgets/{id}/config          # short cache (config.version-aware)
  GET    /static/widget/widget.v{n}.js  # long cache, immutable

Website Visitor (public, CORS-enabled, rate-limited)
  POST   /submissions
```

Every authenticated route requires `Authorization: Bearer <jwt>`, resolved to
`(user_id, tenant_id)` by the `get_current_user` dependency — routes never
read `tenant_id` from anywhere else.

## 6. Non-goal (explicit)

**No visual drag-and-drop widget builder.** Customers configure a widget by
sending JSON (`config` field) through the API — field names, types, button
text — not through a GUI form designer. This is a backend capstone; the
"grade" lives in how the submission path behaves under bad input and load,
not in a WYSIWYG editor. A minimal `<div>` + form is enough to prove the
config renders correctly.

## 7. Architecture diagram

See `README.md` § Architecture — same diagram, kept in one place so it never
drifts out of sync between the two docs.
