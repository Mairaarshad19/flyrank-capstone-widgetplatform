#!/usr/bin/env bash
# Run this ONCE, from inside the flyrank-capstone-widget-platform folder,
# right after you extract the zip. It creates the same 14-commit history
# I built while scaffolding Phase 0 — but with YOU as the author.
set -e

if [ ! -f "README.md" ] || [ ! -d "app" ]; then
  echo "Run this from inside the flyrank-capstone-widget-platform/ folder."
  exit 1
fi

if [ -d ".git" ]; then
  echo "A .git folder already exists here. Delete it first if you want to redo this (rm -rf .git)."
  exit 1
fi

git init -q

echo ""
echo "Set your git identity for this repo (used as the commit author):"
read -p "Your name: " GIT_NAME
read -p "Your email: " GIT_EMAIL
git config user.name "$GIT_NAME"
git config user.email "$GIT_EMAIL"

git add LICENSE .gitignore
git commit -q -m "chore: initialize repo with license and gitignore"

git add README.md
git commit -q -m "docs: add README skeleton"

git add app/__init__.py app/api/__init__.py app/core/__init__.py app/db/__init__.py \
        app/enrichment/__init__.py app/models/__init__.py app/notifications/__init__.py \
        app/repositories/__init__.py app/schemas/__init__.py app/services/__init__.py \
        tests/__init__.py alembic/versions/.gitkeep .dockerignore
git commit -q -m "chore: scaffold project directory structure"

git add requirements.txt pytest.ini
git commit -q -m "chore: add project dependencies"

git add docker-compose.yml Dockerfile
git commit -q -m "chore: add Docker Compose setup for app and postgres"

git add .env.example
git commit -q -m "chore: add .env.example with required environment variables"

git add app/core/config.py
git commit -q -m "feat(core): add fail-fast typed settings loaded from env"

git add app/core/logging.py
git commit -q -m "feat(core): add structured JSON logging"

git add app/db/session.py
git commit -q -m "feat(db): add async engine with bounded pooling and commit-safe session dependency"

git add app/api/health.py
git commit -q -m "feat(api): add liveness and readiness health check endpoints"

git add app/main.py
git commit -q -m "feat: add FastAPI entrypoint with request logging and global exception handling"

git add alembic.ini alembic/env.py alembic/script.py.mako
git commit -q -m "chore(db): wire Alembic migrations to async engine and app settings"

git add tests/conftest.py tests/test_health.py
git commit -q -m "test: add isolated test DB fixtures and health endpoint tests"

git add capstone.yaml
git commit -q -m "docs: add capstone.yaml evaluator manifest"

git add EVIDENCE.md BUILDLOG.md
git commit -q -m "docs: scaffold EVIDENCE.md and BUILDLOG.md"

echo ""
echo "Done. History created:"
git log --oneline
