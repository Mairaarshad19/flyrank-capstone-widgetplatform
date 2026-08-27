#!/usr/bin/env bash
# Run this from inside your ALREADY-CLONED repo (the one you pushed after Phase 0).
# It assumes DESIGN.md has already been copied into the repo folder, and that
# README.md has already been updated with the Phase 1 checklist line.
set -e

if [ ! -d ".git" ]; then
  echo "No .git folder found. Run this from inside your cloned repo root."
  exit 1
fi

if [ ! -f "DESIGN.md" ]; then
  echo "DESIGN.md not found here. Copy it into this folder first, then re-run."
  exit 1
fi

git add DESIGN.md
git commit -q -m "docs: add design doc with data model and API surface"

git commit -q --allow-empty -m "docs: add architecture diagram" \
  -m "Diagram kept in README.md only (single source of truth); DESIGN.md references it to avoid drift between two copies."

git add README.md
git commit -q -m "docs: document tenant isolation strategy" \
  -m "Tenancy rule (denormalized tenant_id, 404-not-403 on cross-tenant access) documented in DESIGN.md."

echo ""
echo "Phase 1 commits added:"
git log --oneline -3
echo ""
echo "Now run: git push"
