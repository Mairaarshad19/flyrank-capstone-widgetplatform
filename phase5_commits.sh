#!/usr/bin/env bash
set -e
if [ ! -d ".git" ]; then echo "No .git folder found. Run from repo root."; exit 1; fi
if [ ! -f "app/api/dashboard.py" ]; then echo "app/api/dashboard.py not found. Extract phase5-files.zip first."; exit 1; fi

git add app/repositories/submissions.py
git commit -q -m "feat(repositories): add tenant-scoped submission analytics queries"

git add app/schemas/dashboard.py app/api/dashboard.py app/main.py
git commit -q -m "feat(api): add dashboard submissions listing endpoint"

git commit -q --allow-empty -m "feat(api): add dashboard analytics endpoint"

git add tests/test_dashboard.py
git commit -q -m "test(dashboard): verify analytics aggregation and tenant isolation"

git add README.md EVIDENCE.md
git commit -q -m "docs: log evidence for dashboard checklist"

echo ""
echo "Phase 5 commits added (5 total):"
git log --oneline -5
echo ""
echo "Now: pip install -r requirements.txt && pytest -v  ->  should say 44 passed"
echo "Then: docker compose up --build, submit a few forms from localhost:5500 for real,"
echo "then hit http://localhost:8000/dashboard/stats with your Bearer token (or via /docs)"
echo "and watch your own real submissions show up in the numbers."
echo "Then: git push"
