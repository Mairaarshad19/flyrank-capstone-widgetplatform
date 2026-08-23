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
