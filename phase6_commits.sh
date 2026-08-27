#!/usr/bin/env bash
set -e
if [ ! -d ".git" ]; then echo "No .git folder found. Run from repo root."; exit 1; fi
if [ ! -f "app/seed.py" ]; then echo "app/seed.py not found. Extract phase6-files.zip into this folder first."; exit 1; fi

git add .github/workflows/tests.yml
git commit -q -m "ci: add GitHub Actions workflow to run tests against real Postgres on every push" \
  -m "Deliberately Postgres, not SQLite: the enum name-vs-value bug (see BUILDLOG.md 'Phase 2/3 hotfix') passed every test on SQLite and only failed against real Postgres."

git add app/seed.py
git commit -q -m "feat(seed): add demo data seeding script" \
  -m "Idempotent by design -- checks for the demo user first and no-ops on a second run."

git add tests/test_seed.py
git commit -q -m "test(seed): verify seed creates correct data and is genuinely idempotent"

git add README.md
git commit -q -m "docs: complete README with setup, architecture, CI, and limitations"

git add EVIDENCE.md
git commit -q -m "docs: finalize EVIDENCE.md with proof for every checklist item"

git add BUILDLOG.md
git commit -q -m "docs: finalize BUILDLOG.md with Phase 6 AI usage notes"

git commit -q --allow-empty -m "chore: audit repo for committed secrets" \
  -m "Confirmed .env never appears in git history, .env.example contains only placeholders, and the only credential in code is an intentionally-fake demo account."

echo ""
echo "Phase 6 commits added (7 total):"
git log --oneline -7
echo ""
echo "Now: pip install -r requirements.txt && pytest -v  ->  should say 46 passed"
echo "Then: git push  (this will trigger the new GitHub Actions workflow automatically —"
echo "check the 'Actions' tab on your GitHub repo page to watch it run against real Postgres)"
echo ""
echo "Optional but worth it: docker compose up --build, then:"
echo "  docker compose exec app python -m app.seed"
echo "and log into /docs with demo@acme-bakery.test / demo-password-123 to see real seeded data."
