#!/usr/bin/env bash
set -e
if [ ! -d ".git" ]; then echo "No .git folder found. Run from repo root."; exit 1; fi
if [ ! -f "DEMO_SCRIPT.md" ]; then echo "Extract phase7-files.zip into this folder first."; exit 1; fi

git add app/core/config.py .env.example
git commit -q -m "feat(demo): add reproducible failure toggles for geo provider and notifications" \
  -m "Makes the 'kill provider live' and 'break the notification' demo moments reproducible on command instead of dependent on a real outage."

git add app/enrichment/ip_api.py app/notifications/console.py
git commit -q -m "feat(demo): wire force-fail toggles into provider A and the console notifier"

git add tests/test_demo_toggles.py
git commit -q -m "test(demo): verify force-fail toggles work and are off by default"

git add DEMO_SCRIPT.md
git commit -q -m "docs: add rehearsed demo script mapped to real commands"

git add README.md EVIDENCE.md BUILDLOG.md
git commit -q -m "docs: log evidence and buildlog notes for demo prep"

git tag -a v1.0 -m "v1.0 — capstone submission

Embeddable Widget & Lead-Capture Platform. All 7 build phases complete,
50/50 tests passing in CI against real Postgres.

Full definition-of-done checklist met (see EVIDENCE.md), including:
- Multi-tenant widget CRUD with proven tenant isolation
- Cached, versioned public widget delivery
- Hardened public submission endpoint: CORS, boundary validation,
  per-IP and per-widget rate limiting, honeypot spam control,
  geo enrichment with a provider fallback chain, safe side effects,
  and idempotent retries
- Owner dashboard with correct, tenant-isolated aggregation
- Two real production bugs found, fixed, and covered by permanent
  regression tests (see BUILDLOG.md)"

echo ""
echo "Phase 7 commits added (5 total) + v1.0 tag created:"
git log --oneline -5
echo ""
echo "Now: pip install -r requirements.txt && pytest -v  ->  should say 50 passed"
echo "Then: git push && git push origin v1.0   (tags don't push automatically!)"
echo ""
echo "Then open DEMO_SCRIPT.md and rehearse it end to end at least twice."
