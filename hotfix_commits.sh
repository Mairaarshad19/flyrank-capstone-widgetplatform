#!/usr/bin/env bash
# Run from inside your cloned repo root, AFTER extracting
# hotfix-enum-values.zip's contents directly into this folder.
set -e

if [ ! -d ".git" ]; then
  echo "No .git folder found. Run this from inside your cloned repo root."
  exit 1
fi
if [ ! -f "tests/test_enum_db_values.py" ]; then
  echo "tests/test_enum_db_values.py not found. Extract hotfix-enum-values.zip into this folder first."
  exit 1
fi

git add app/models/user.py app/models/widget.py
git commit -q -m "fix(db): store enum VALUES not NAMES to match Postgres native enum types" \
  -m "SQLAlchemy's Enum type defaults to persisting a Python enum member's name (e.g. \"OWNER\"), not its value (\"owner\"). Our Postgres migration created native enum types using lowercase values, so every insert against real Postgres failed with 'invalid input value for enum userrole: OWNER' -- even though all tests passed, because SQLite's generic enum fallback validates names on both sides and never surfaced the mismatch. Fixed with values_callable on every enum column."

git add tests/test_enum_db_values.py
git commit -q -m "test(db): add Postgres-dialect regression test for enum value binding" \
  -m "Compiles the bind processor against the real postgresql dialect (no live DB needed) and asserts the bound value is lowercase."

git add BUILDLOG.md EVIDENCE.md
git commit -q -m "docs: log root cause and fix for the enum storage hotfix"

echo ""
echo "Hotfix commits added (3 total):"
git log --oneline -3
echo ""
echo "Now: docker compose down && docker compose up --build"
echo "Then retry POST /auth/register from http://localhost:8000/docs -- it should return 201 this time."
echo "Then: pytest -v  ->  should say 22 passed"
echo "Then: git push"
