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
