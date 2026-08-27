#!/usr/bin/env bash
# Run from inside your cloned repo root, AFTER extracting phase3-files.zip's
# contents directly into this folder.
set -e

if [ ! -d ".git" ]; then
  echo "No .git folder found. Run this from inside your cloned repo root."
  exit 1
fi
if [ ! -f "app/api/public.py" ]; then
  echo "app/api/public.py not found. Extract phase3-files.zip into this folder first."
  exit 1
fi

git add app/api/widgets.py app/core/config.py
git commit -q -m "feat(api): add versioned embed snippet generation to widget response"

git add static/widget/widget.v1.js
git commit -q -m "feat(widget): add embeddable widget script with render and submit logic"

git add app/repositories/widgets.py app/api/public.py app/main.py
git commit -q -m "feat(api): add public cached widget config endpoint" \
  -m "Also wires basic CORS (needed for cross-origin GET to even be readable by the browser) and mounts the new public router. Full preflight/POST CORS hardening lands in Phase 4."

git add static/test-page/index.html
git commit -q -m "feat(test-page): add customer-site test page on separate origin"

git add tests/test_public.py
git commit -q -m "test(public): verify cache headers, ETag revalidation, and paused-widget 404s"

git add README.md EVIDENCE.md
git commit -q -m "docs: log evidence for widget delivery checklist"

echo ""
echo "Phase 3 commits added (6 total):"
git log --oneline -6
echo ""
echo "Now verify yourself: pip install -r requirements.txt && pytest -v  ->  should say 19 passed"
echo "Then: docker compose up --build, create a widget, paste its id into static/test-page/index.html,"
echo "run: cd static/test-page && python3 -m http.server 5500, and open http://localhost:5500"
echo "Then: git push"
