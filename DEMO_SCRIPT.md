# Demo Script — 6 Minutes

Rehearse this end to end at least twice before the real thing. One clean run
beats a perfect script you've never actually executed.

**Before you start:** `docker compose up --build`, confirm `http://localhost:8000/health/ready`
says `ready`, and have three terminal tabs open: one for `docker compose logs -f app`,
one for curl commands, and your browser on `http://localhost:5500` (or ready to open it).

---

## 1. Create a widget, show the embed snippet (45s)

```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@acme-bakery-demo.io", "password": "demo-password-123"}' | tee /tmp/token.json
TOKEN=$(python3 -c "import json;print(json.load(open('/tmp/token.json'))['access_token'])")

curl -s -X POST http://localhost:8000/widgets \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"type": "signup_form", "title": "10% off", "config": {"fields": ["email"], "button_text": "Join"}}'
```

**Say:** "That `embed_snippet` field is the entire integration story — a
customer pastes that one line into their site and everything else is
automatic."

## 2. Show it rendering on a page you don't control (30s)

Open `http://localhost:5500` (your `static/test-page/index.html`, already
pointed at a real widget id). **Say:** "This page has zero other connection
to my backend — no shared code, no shared server, different port entirely.
The browser is fetching config and rendering the form live."

## 3. Submit it, show the enriched dashboard (45s)

Submit the form in the browser, then:

```bash
curl -s http://localhost:8000/dashboard/stats -H "Authorization: Bearer $TOKEN"
```

**Say:** "That submission is already geo-enriched and counted in stats — no
manual step in between."

## 4. Attack yourself (90s)

**Bad payload — clean 4xx, never a 500:**
```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/submissions \
  -H "Content-Type: application/json" -d '{"widget_id": "not-a-uuid"}'
```
Expect `422`.

**Disallowed origin — CORS actually enforced:**
```bash
curl -s -i -X OPTIONS http://localhost:8000/submissions \
  -H "Origin: http://evil.example.com" -H "Access-Control-Request-Method: POST" \
  | grep -i "access-control-allow-origin" || echo "(no header — correctly rejected)"
```

**Burst — rate limiter answers, service stays up:**
```bash
WIDGET_ID="<paste your widget id>"
for i in $(seq 1 12); do
  curl -s -o /dev/null -w "%{http_code} " -X POST http://localhost:8000/submissions \
    -H "Content-Type: application/json" \
    -d "{\"widget_id\": \"$WIDGET_ID\", \"fields\": {\"email\": \"burst$i@x.com\"}}"
done
echo ""
curl -s -o /dev/null -w "still up: %{http_code}\n" http://localhost:8000/health/live
```
**Say:** "You'll see 429s appear partway through, and the health check right
after proves the burst never took the service down."

## 5. Kill the primary geo provider live, watch fallback take over (60s)

```bash
# In your .env: set GEO_PROVIDER_A_FORCE_FAIL=true, then:
docker compose restart app
```
Submit another form on the test page, then:
```bash
curl -s "http://localhost:8000/dashboard/submissions?limit=1" -H "Authorization: Bearer $TOKEN"
```
**Say:** "`geo_provider_used` on that new row says `ipapi_co`, not
`ip_api_com` — provider A is dead right now and the fallback chain caught it
transparently. This is a deliberate on/off switch (`GEO_PROVIDER_A_FORCE_FAIL`
in `.env`), not luck — a real outage would behave identically."

**Reset before continuing:** set `GEO_PROVIDER_A_FORCE_FAIL=false`, `docker compose restart app`.

## 6. Break the notification, submission still succeeds (45s)

```bash
# In your .env: set NOTIFY_FORCE_FAIL=true, then:
docker compose restart app
```
Submit one more form. It succeeds in the browser. Then:
```bash
docker compose logs app --tail=20 | grep submission_notification_failed
```
**Say the sentence:** *"Non-critical failures never break the main path."*
Point at the log line as proof the failure happened and was recorded —
without the visitor ever seeing an error.

**Reset:** `NOTIFY_FORCE_FAIL=false`, `docker compose restart app`.

## 7. Close on the dashboard (15s)

```bash
curl -s http://localhost:8000/dashboard/stats -H "Authorization: Bearer $TOKEN"
```
**Say:** "Submissions, stats, geo breakdown — this application safely accepts
data from websites it doesn't own, from visitors it doesn't control, and it
degrades instead of breaking every time something downstream fails."

---

## If asked to explain 2–3 lines of code

Be ready to talk through, without notes:
- **The fallback chain** (`app/enrichment/chain.py`) — why it catches
  exceptions defensively even though providers are contracted not to raise.
- **Tenant isolation** (`app/repositories/widgets.py` / `submissions.py`) —
  why `tenant_id` is filtered directly rather than relying on a join, and why
  cross-tenant access returns 404 instead of 403.
- **The `get_db` commit boundary** (`app/db/session.py`) — why only one place
  in the whole app is allowed to commit or roll back.
- **The two hotfixes in `BUILDLOG.md`** — genuinely good material if asked
  "tell me about a bug you found": both were invisible to the entire test
  suite until real Postgres / the real validation schema exposed them, and
  both got permanent regression tests, proven to fail without the fix.
