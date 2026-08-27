#!/usr/bin/env bash
# Run from inside your cloned repo root, AFTER extracting phase4-files.zip's
# contents directly into this folder.
set -e

if [ ! -d ".git" ]; then
  echo "No .git folder found. Run this from inside your cloned repo root."
  exit 1
fi
if [ ! -f "app/api/submissions.py" ]; then
  echo "app/api/submissions.py not found. Extract phase4-files.zip into this folder first."
  exit 1
fi

git add app/models/submission.py app/models/__init__.py alembic/versions/0002_add_submissions_table.py
git commit -q -m "feat(models): add Submission model and migration"

git add app/main.py
git commit -q -m "feat(cors): configure CORS middleware for public submission endpoint"

git add app/schemas/submission.py
git commit -q -m "feat(schemas): add strict validation schema for submissions"

git add app/repositories/submissions.py app/api/submissions.py
git commit -q -m "feat(api): add public submission endpoint with boundary validation"

git add app/core/rate_limit.py
git commit -q -m "feat(rate-limit): add per-IP rate limiting to submission endpoint"

git commit -q --allow-empty -m "feat(rate-limit): add per-widget rate limiting" \
  -m "Custom sliding-window limiter rather than slowapi, since widget_id lives inside the JSON body, not somewhere slowapi's key_func can see pre-parse."

git add static/widget/widget.v1.js
git commit -q -m "feat(spam): add honeypot field spam detection" \
  -m "Field added to the widget script in Phase 3 already; this wires the server-side check and adds idempotency key generation."

git add app/enrichment/base.py
git commit -q -m "feat(enrichment): add geo provider interface"

git add app/enrichment/ip_api.py app/enrichment/ipapi_co.py
git commit -q -m "feat(enrichment): implement ip-api.com and ipapi.co provider clients"

git add app/enrichment/chain.py
git commit -q -m "feat(enrichment): add provider fallback chain"

git commit -q --allow-empty -m "feat(submissions): wire geo enrichment into submission flow"

git add app/notifications/base.py app/notifications/console.py app/notifications/webhook.py
git commit -q -m "feat(notifications): add confirmation notification interface"

git commit -q --allow-empty -m "feat(submissions): trigger safe post-commit confirmation side effect"

git add tests/conftest.py
git commit -q -m "test: add deterministic mock providers and rate-limit isolation fixtures"

git add tests/test_submissions.py
git commit -q -m "test(submissions): cover CORS, validation, rate limiting, spam, fallback chain, safe side effects, and idempotency"

git add README.md EVIDENCE.md
git commit -q -m "docs: log evidence for submission path checklists"

echo ""
echo "Phase 4 commits added (16 total):"
git log --oneline -16
echo ""
echo "Now: pip install -r requirements.txt && pytest -v  ->  should say 38 passed"
echo "Then: docker compose down && docker compose up --build  (new migration + new deps)"
echo "Then test the LIVE widget you already have on localhost:5500 -- submit the form for real"
echo "and check docker compose logs app for the new_submission_notification log line."
echo "Then: git push"
