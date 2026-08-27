# Build Log — AI Usage

Honest record of where AI assisted, where it was wrong, and what I changed.
Updated as I go, not reconstructed at the end.

## Phase 0 — Foundations

- **Where AI helped:** scaffolding the initial project structure, the
  structured JSON logging formatter, and the async SQLAlchemy pooling
  configuration (pool_size/max_overflow/pool_recycle/pool_pre_ping) — I knew
  *what* I needed conceptually (bounded connections, dead-connection
  detection) but not the exact SQLAlchemy 2.0 async API for it.
- **Where I made the call myself:** splitting health checks into `/live` vs
  `/ready` instead of one endpoint, requiring every write to go through a
  single commit-or-rollback point in `get_db`, and the decision to fail fast
  on invalid config (Pydantic validators) rather than defaulting silently.
- **What I verified rather than trusted:** ran the actual test suite and a
  manual app import before accepting this skeleton — didn't take generated
  code on faith.
- **What I'll double check going forward:** the JWT expiry default and the
  rate-limit thresholds are placeholders — I'll tune these against realistic
  traffic assumptions once the submission endpoint exists (Phase 4).

## Phase 2/3 hotfix — enum name-vs-value mismatch (found by the user in real Docker use)

- **The bug:** `POST /auth/register` returned 500 in real Docker + Postgres,
  even though all 19 tests were green. Root cause: SQLAlchemy's `Enum` type
  defaults to persisting a Python enum member's **name** (`"OWNER"`), not its
  **value** (`"owner"`) — a genuinely non-obvious default. Our Postgres
  migration created the native `userrole`/`widgettype`/`widgetstatus` enum
  types with lowercase values, so Postgres rejected every insert with
  `invalid input value for enum userrole: "OWNER"`.
- **Why the test suite didn't catch it:** the tests run against SQLite (fast,
  no Docker needed), and SQLite's generic enum fallback validates the *name*
  on both write and read — so it "agreed with itself" and never surfaced the
  mismatch. It only broke against real Postgres, which is exactly why local
  Docker verification matters even when `pytest` is green.
- **The fix:** added `values_callable=lambda enum_cls: [m.value for m in enum_cls]`
  to every `SAEnum(...)` column definition, forcing SQLAlchemy to bind the
  lowercase value instead of the uppercase name.
- **What I did instead of just trusting the fix:** wrote
  `tests/test_enum_db_values.py`, which compiles the bind processor against
  the actual `postgresql` dialect (no live DB needed) and asserts the bound
  value is lowercase. Then I deliberately reverted the fix and reran that
  test to confirm it fails the same way the real bug did (`'OWNER' == 'owner'`
  assertion error) — then restored the fix and confirmed all 22 tests pass.
  This is now a permanent regression test; this exact bug can't silently
  reappear even though it lives entirely on the SQLite/Postgres seam that the
  rest of the suite can't see.

## Phase 6 — CI, seed script, and docs

- **Where AI helped:** structuring the GitHub Actions workflow (the exact
  `services:` block syntax for running Postgres as a CI service container,
  and its healthcheck options) and the seed script's data-shape choices
  (spreading submissions across a date range, mixing in a `None`/`None` geo
  pair to simulate a failed enrichment realistically).
- **Where I made the call myself:** deciding CI should run against real
  Postgres, not SQLite, specifically *because* of the Phase 2/3 enum bug —
  that bug is the concrete argument for why this matters, not an abstract
  best practice. Also decided the seed script needed its own test rather
  than being "obviously fine because it's just inserts" — a seed script that
  silently duplicates data on every re-run is a real, smaller version of the
  same idempotency bug class the submission endpoint guards against.
- **What I verified rather than trusted:** ran `tests/test_seed.py` for
  real — first confirming it creates exactly 1 demo user, 2 widgets, and 25
  submissions, then calling `seed()` a second time and confirming the counts
  don't double. Also ran a manual secrets audit (`git log --all --full-history
  -- .env`, grep across tracked files for secret-shaped strings) rather than
  assuming `.gitignore` alone was sufficient proof nothing leaked.
- **What I'd do differently with more time:** the per-widget/per-IP rate
  limiter is in-process memory, documented as a known limitation — the
  moment this runs on more than one instance, both counters need to move to
  Redis or another shared store. Left as a documented limitation rather than
  built, since the capstone's grading weight is on correctness and
  resilience of the pattern, not premature horizontal-scaling infrastructure.

## Hotfix — seed demo email rejected by EmailStr (found by the user testing the seed script)

- **The bug:** `DEMO_EMAIL = "demo@acme-bakery.test"` failed Pydantic's
  `EmailStr` validation with "reserved name that cannot be used with email" —
  before `login()` or `register()` ever ran. Root cause: `email-validator`
  (which backs `EmailStr`) special-cases RFC 2606 reserved TLDs (`.test`,
  `.example`, `.invalid`, `.localhost`) and rejects them at the syntax level,
  entirely independent of DNS deliverability checks being on or off.
- **Why nothing in the test suite caught it originally:** `tests/test_seed.py`
  tested the seed script's *database* behavior (row counts, idempotency) by
  calling `seed()` directly — it never round-tripped the demo email through
  the actual Pydantic schema the real `/auth/register` endpoint uses, so the
  validation-layer bug was invisible to it. The person building this caught
  it manually by actually trying to log in with the seeded credentials.
- **The fix:** changed `DEMO_EMAIL` to `demo@acme-bakery-demo.io` — any TLD
  outside the RFC 2606 reserved set works, since no DNS check happens by
  default.
- **The regression test added, and proven to catch the bug**:
  `test_demo_email_passes_the_same_validation_register_uses` constructs a
  real `RegisterRequest` (the exact schema `/auth/register` validates
  against) using `seed_module.DEMO_EMAIL`. Deliberately reverted the fix,
  reran, and got the identical error message reported
  ("special-use or reserved name"), then restored the fix and confirmed all
  47 tests pass. Same discipline as the earlier enum hotfix: don't just fix
  it, prove the regression test actually catches it.
