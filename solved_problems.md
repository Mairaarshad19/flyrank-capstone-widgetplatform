# Capstone Project — Problems Faced & How We Resolved Them

During the development of the **Embeddable Widget & Lead-Capture Platform**, we faced several real development, integration, database, Docker, CORS, authentication, and testing issues. Here is a complete summary you can use for your documentation, presentation, or viva.

---

## 1. Docker couldn't download the PostgreSQL image

### Problem

When we first ran:

```bash
docker compose up --build
```

Docker showed:

```text
failed to resolve source metadata for docker.io/library/postgres:16-alpine
```

and:

```text
dial tcp: lookup registry-1.docker.io:443
```

### Cause

Docker Desktop temporarily couldn't connect to Docker Hub because of a **DNS/network resolution problem**.

### Solution

We retried the Docker pull/build after the network connection became available. The PostgreSQL image was eventually downloaded successfully.

---

# 2. PostgreSQL enum error during registration

### Problem

Registration initially failed with:

```text
InvalidTextRepresentationError:
invalid input value for enum userrole: "OWNER"
```

The SQL query was trying to insert:

```text
"OWNER"
```

while PostgreSQL's enum contained lowercase values:

```text
owner
member
```

### Cause

There was a mismatch between the Python enum/database representation and the PostgreSQL enum values.

### Solution

We checked:

```text
app/models/user.py
```

and the migration:

```text
alembic/versions/0001_add_tenant_user_widget_tables.py
```

The Python enum was corrected to use:

```python
OWNER = "owner"
```

and:

```python
MEMBER = "member"
```

This made the application and PostgreSQL enum consistent.

---

# 3. Widget returned 404 — "Widget not found"

### Problem

The widget JavaScript requested:

```text
GET /widgets/{widget_id}/config
```

but returned:

```json
{
  "detail": "Widget not found"
}
```

### Cause

The test page was using a widget ID that didn't correspond to the widget belonging to the current database/tenant.

### Solution

We created a new widget through:

```text
POST /widgets
```

and used the **actual returned widget ID** in:

```text
static/test-page/index.html
```

For example:

```text
e4d29bf3-4421-4e54-84dd-602866b4b724
```

The widget could then be loaded using the correct ID.

---

# 4. CORS blocked the widget

### Problem

The browser showed:

```text
Access to fetch ... has been blocked by CORS policy
```

Specifically:

```text
No 'Access-Control-Allow-Origin' header is present
```

### Cause

The widget was running on:

```text
http://localhost:5500
```

while the API was running on:

```text
http://localhost:8000
```

These are different origins.

The browser therefore required the API to explicitly allow the test page's origin.

### Solution

We configured CORS in the FastAPI application to allow the test page origin.

After that, the widget could successfully fetch:

```text
/widgets/{widget_id}/config
```

from the separate test website.

---

# 5. The widget title appeared but the actual form didn't

### Problem

The test page showed:

> Acme Bakery
> Get 10% off your first order

but there was no email field or submit button.

### Cause

The widget JavaScript was running, but the configuration request was failing.

The browser showed:

```text
Failed to load widget config
```

and later:

```text
ERR_CONNECTION_REFUSED
```

### Solution

We checked Docker:

```bash
docker compose ps
```

and discovered:

```text
app   Restarting (1)
```

The API container was continuously crashing.

---

# 6. Docker app couldn't connect to PostgreSQL

### Problem

The app container logs showed:

```text
socket.gaierror: [Errno -3] Temporary failure in name resolution
```

### Cause

The FastAPI container couldn't resolve/connect to the PostgreSQL container.

Therefore:

```text
app → PostgreSQL
```

was failing, causing the app to crash and restart.

### Solution

We stopped the Compose environment:

```bash
docker compose down
```

and started it again:

```bash
docker compose up -d
```

After that:

```bash
docker compose ps
```

showed:

```text
app       Up
db        Up (healthy)
```

The API became available again at:

```text
http://localhost:8000
```

and the widget form loaded correctly.

---

# 7. Form submissions were not initially visible

### Problem

We needed to prove that a real visitor submission was actually being processed.

### Solution

We submitted the form from:

```text
http://localhost:5500
```

and checked:

```bash
docker compose logs app | findstr new_submission_notification
```

We received:

```text
new_submission_notification
```

with:

```text
tenant_id
widget_id
submission_id
```

This proved that the real submission travelled through the application and triggered the notification side effect.

---

# 8. Submission statistics verification

### Problem

We needed to verify that actual submissions were reaching the dashboard statistics.

### Solution

We used:

```text
GET /dashboard/stats
```

with the authentication token.

The API returned data such as:

```json
{
  "total_submissions": 25
}
```

and breakdowns by:

* day
* widget
* country

This proved that submissions were being stored and aggregated correctly.

---

# 9. Seed demo login failed because of `.test`

### Problem

The seeded demo account originally used:

```text
demo@acme-bakery.test
```

When we tried to log in through `/docs`, FastAPI returned:

```text
422
```

with:

```text
The part after the @-sign is a special-use or reserved name
```

### Cause

The project uses Pydantic's:

```python
EmailStr
```

for email validation.

The `.test` domain is reserved for testing and was rejected by the email validator before the login function was even executed.

### Solution

We changed the demo email to:

```text
demo@acme-bakery-demo.io
```

while keeping the password:

```text
demo-password-123
```

We also added regression tests for the issue.

The test suite then reached:

```text
47 passed
```

---

# 10. Demo seed data already existed

### Problem

When we ran:

```bash
docker compose exec app python -m app.seed
```

we saw:

```text
Demo tenant already seeded (demo@acme-bakery.test). Nothing to do.
```

### Cause

The demo data already existed in the database.

### Solution

The seed command correctly detected the existing data instead of creating duplicates.

After fixing the demo email, the seed process could use the corrected demo account.

---

# 11. Git Bash multiline curl commands caused errors

### Problem

During the rate-limit demo, we initially got:

```text
422
bash: -H: command not found
bash: -d: command not found
```

### Cause

The multiline shell command wasn't being interpreted correctly in Git Bash. Parts of the command were being treated as separate commands.

### Solution

We tested the request as a single line:

```bash
curl -i -X POST http://localhost:8000/submissions -H "Content-Type: application/json" -d "{\"widget_id\":\"...\",\"fields\":{\"email\":\"test123@gmail.com\"}}"
```

It successfully returned:

```text
HTTP/1.1 201 Created
```

So the API itself was working; the problem was the shell command formatting.

---

# 12. Geo-enrichment fallback testing

### Problem

The demo needed to demonstrate what happens if the primary geo provider fails.

Using a real external service would be unreliable because it might simply be working during the demonstration.

### Solution

We introduced a controlled demo switch:

```env
GEO_PROVIDER_A_FORCE_FAIL=true
```

This deliberately makes Provider A fail.

The application then tries the fallback provider.

The logs showed:

```text
geo_provider_no_result
provider: ip_api_com
```

followed by:

```text
geo_provider_no_result
provider: ipapi_co
```

and finally:

```text
geo_enrichment_exhausted_all_providers
```

### Important observation

The fallback mechanism itself worked correctly.

The local environment simply couldn't obtain a usable geographic result, so:

```json
"geo_country": null,
"geo_city": null
```

was returned.

The important thing for the demo was that the application **didn't crash when a provider failed**.

---

# 13. Notification failure testing

### Problem

The demo required proving that if the notification system fails, the user's submission should still succeed.

Normally it would be difficult to reliably "break" a notification system during a live demo.

### Solution

We added another controlled demo switch:

```env
NOTIFY_FORCE_FAIL=true
```

This lets us deliberately trigger notification failure.

The expected behavior is:

```text
User submits form
        ↓
Submission succeeds
        ↓
Notification fails
        ↓
Failure is logged
        ↓
User still gets successful submission
```

This demonstrates an important reliability principle:

> **Non-critical failures should not break the main user flow.**

---

# 14. 422 responses during the security/rate-limit demo

### Problem

The demo's burst test initially produced many:

```text
422
```

responses.

### Cause

The request payload/command formatting was incorrect rather than the rate limiter rejecting the requests.

### Solution

We first tested a valid single submission and confirmed:

```text
201 Created
```

Then the burst test could be performed using the correct payload.

The purpose of the burst test is to eventually demonstrate:

```text
429 Too Many Requests
```

while confirming that the service itself remains alive.

---

# 15. Accidentally pushed from a subdirectory

### Problem

We ran:

```bash
git push origin main
```

while the terminal was inside:

```text
static/test-page
```

instead of the project root.

### Concern

We were worried that this might damage the repository.

### Result

It was fine because Git recognized the parent repository.

The push successfully updated:

```text
main -> main
```

No repository history was lost.

---

# 16. GitHub repository rename

### Problem

We wanted to change the repository name from:

```text
Embeddable-Widget-Lead-Capture-Platform
```

to:

```text
flyrank-capstone-widgetplatform
```

### Solution

The repository can be renamed directly through GitHub Settings.

Then the local remote should be updated:

```bash
git remote set-url origin https://github.com/Mairaarshad19/flyrank-capstone-widgetplatform.git
```

The Git history remains intact.

---

# 17. Important lesson from the two major bugs

Two particularly valuable bugs were discovered because they existed between different layers of the application.

### Bug 1 — PostgreSQL enum mismatch

The database logic looked fine in isolation, but the **real PostgreSQL database** exposed the mismatch:

```text
OWNER
```

vs.

```text
owner
```

### Bug 2 — Demo email validation

The seed/database test passed, but the **real API validation layer** rejected:

```text
demo@acme-bakery.test
```

because of Pydantic `EmailStr`.

### Lesson

Testing only individual functions isn't enough.

You also need to test the **actual boundaries between components**:

```text
API
 ↓
Validation
 ↓
Database
 ↓
External services
 ↓
Browser
```

That's a strong point to mention in your capstone presentation.

---

# Final Project Verification

By the end, we had verified:

| Area                         | Status      |
| ---------------------------- | ----------- |
| FastAPI backend              | ✅           |
| PostgreSQL                   | ✅           |
| Docker Compose               | ✅           |
| Authentication               | ✅           |
| JWT authorization            | ✅           |
| Widget creation              | ✅           |
| Embeddable JavaScript widget | ✅           |
| Cross-origin rendering       | ✅           |
| CORS                         | ✅           |
| Form submission              | ✅           |
| Notification side effect     | ✅           |
| Dashboard statistics         | ✅           |
| Geo-enrichment               | ✅           |
| Geo fallback                 | ✅           |
| Rate limiting                | ✅           |
| Input validation             | ✅           |
| Tenant isolation             | ✅           |
| Failure handling             | ✅           |
| Seed data                    | ✅           |
| Automated tests              | ✅ **47/47** |
| Demo chaos toggles           | ✅           |
| GitHub repository            | ✅           |

### The biggest takeaway

The capstone isn't just a form that saves an email.

It's a complete flow:

```text
Customer Website
       ↓
Embeddable Widget
       ↓
FastAPI API
       ↓
Validation + Rate Limiting
       ↓
PostgreSQL
       ↓
Geo Enrichment
       ↓
Notification
       ↓
Dashboard / Statistics
```

And the important engineering part is that **when individual components fail, the whole application doesn't necessarily fail**. That is exactly what the fallback and failure-handling demos are designed to prove.
