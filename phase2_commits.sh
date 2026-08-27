#!/usr/bin/env bash
# Run from inside your cloned repo root, AFTER extracting phase2-files.zip's
# contents directly into this folder (so app/models/tenant.py etc. land in
# the right place, overwriting app/main.py, app/core/config.py, alembic/env.py,
# requirements.txt, EVIDENCE.md, and README.md).
set -e

if [ ! -d ".git" ]; then
  echo "No .git folder found. Run this from inside your cloned repo root."
  exit 1
fi
if [ ! -f "app/models/tenant.py" ]; then
  echo "app/models/tenant.py not found. Extract phase2-files.zip into this folder first."
  exit 1
fi

git add app/models/tenant.py app/models/user.py app/models/widget.py app/models/__init__.py
git commit -q -m "feat(models): add Tenant, User, and Widget models"

git add alembic/versions/0001_add_tenant_user_widget_tables.py alembic/env.py
git commit -q -m "chore(db): add initial migration for tenant, user, widget tables"

git add app/core/security.py
git commit -q -m "feat(auth): add password hashing and JWT token utilities"

git add requirements.txt
git commit -q -m "fix(auth): pin bcrypt to 4.0.1 for passlib compatibility" \
  -m "passlib 1.7.4's internal self-test breaks on bcrypt>=4.1 (missing __about__ attribute), causing every password hash to fail at runtime. Pinning avoids the trap."

git add app/schemas/auth.py
git commit -q -m "feat(auth): add register and login request/response schemas"

git add app/api/auth.py app/main.py
git commit -q -m "feat(auth): add register and login endpoints"

git add app/core/deps.py
git commit -q -m "feat(auth): add authenticated dependency with tenant resolution"

git add app/repositories/widgets.py
git commit -q -m "feat(repositories): add tenant-scoped widget repository"

git add app/schemas/widget.py app/services/widgets.py
git commit -q -m "feat(services): add widget service layer"

git add app/core/config.py app/api/widgets.py
git commit -q -m "feat(api): add widget CRUD endpoints"

git add tests/test_auth.py
git commit -q -m "test(auth): cover register, login, and duplicate-email cases"

git add tests/test_widgets.py
git commit -q -m "test(widgets): verify cross-tenant isolation on widget access"

git add EVIDENCE.md README.md
git commit -q -m "docs: log evidence for widget management checklist"

echo ""
echo "Phase 2 commits added (13 total):"
git log --oneline -13
echo ""
echo "Now run your own tests: pip install -r requirements.txt && pytest -v"
echo "Then: git push"
