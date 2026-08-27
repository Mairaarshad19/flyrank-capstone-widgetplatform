#!/usr/bin/env bash
set -e
if [ ! -d ".git" ]; then echo "No .git folder found. Run from repo root."; exit 1; fi
if [ ! -f "tests/test_seed.py" ]; then echo "Extract hotfix2-seed-email.zip into this folder first."; exit 1; fi

git add app/seed.py README.md
git commit -q -m "fix(seed): use a non-reserved TLD for the demo email" \
  -m "email-validator rejects RFC 2606 reserved TLDs (.test/.example/.invalid/.localhost) as a syntax-level guard. demo@acme-bakery.test made POST /auth/register 422 before login() ever ran. Fixed by moving to demo@acme-bakery-demo.io."

git add tests/test_seed.py
git commit -q -m "test(seed): add regression test validating the demo email against the real register schema"

git add BUILDLOG.md EVIDENCE.md
git commit -q -m "docs: log root cause and fix for the seed email hotfix"

echo ""
echo "Hotfix commits added (3 total):"
git log --oneline -3
echo ""
echo "Now: pip install -r requirements.txt && pytest -v  ->  should say 47 passed"
echo "Then: docker compose exec app python -m app.seed"
echo "Then log in with demo@acme-bakery-demo.io / demo-password-123 -- should work now."
echo "Then: git push"
