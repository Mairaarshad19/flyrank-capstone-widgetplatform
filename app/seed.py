"""
Seed script: creates one demo tenant, two widgets, and 25 realistic
submissions spread across the last two weeks, so a stranger cloning this repo
sees real data in the dashboard within a minute of `docker compose up`.

Run with: docker compose exec app python -m app.seed

Safe to run more than once: it checks for the demo user by email first and
exits without creating duplicates if it already exists. Idempotency isn't
just a submission-endpoint concern — a seed script that duplicates data on
every re-run is a real, if smaller, version of the same bug class.
"""
import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import session_scope
from app.models.submission import NotificationStatus, Submission
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.widget import Widget, WidgetStatus, WidgetType

DEMO_EMAIL = "demo@acme-bakery-demo.io"
DEMO_PASSWORD = "demo-password-123"
# Deliberately NOT a .test/.example/.invalid/.localhost domain: those are
# RFC 2606 reserved TLDs, and Pydantic's EmailStr (via the email-validator
# package) rejects them as a syntax-level guard — independent of and in
# addition to DNS deliverability checks. Using demo@acme-bakery.test here
# originally made POST /auth/register return 422 before login() ever ran.

# (country, city) pairs to scatter across demo submissions, including one
# None/None pair to simulate a submission where geo enrichment failed —
# exactly the "degrade, never fail" behavior built in Phase 4.
GEO_SAMPLES = [
    ("United States", "New York"),
    ("United Kingdom", "London"),
    ("Pakistan", "Lahore"),
    ("Germany", "Berlin"),
    (None, None),
]


async def seed() -> None:
    async with session_scope() as session:
        existing = await session.execute(select(User).where(User.email == DEMO_EMAIL))
        if existing.scalar_one_or_none() is not None:
            print(f"Demo tenant already seeded ({DEMO_EMAIL}). Nothing to do.")
            return

        tenant = Tenant(name="Acme Bakery (demo)", slug=f"acme-bakery-demo-{uuid.uuid4().hex[:6]}")
        session.add(tenant)
        await session.flush()

        user = User(
            tenant_id=tenant.id,
            email=DEMO_EMAIL,
            hashed_password=hash_password(DEMO_PASSWORD),
            role=UserRole.OWNER,
        )
        session.add(user)

        newsletter = Widget(
            tenant_id=tenant.id,
            type=WidgetType.SIGNUP_FORM,
            title="Get 10% off your first order",
            description="Newsletter signup shown on the homepage",
            config={"fields": ["email"], "button_text": "Join"},
            status=WidgetStatus.ACTIVE,
        )
        tasting = Widget(
            tenant_id=tenant.id,
            type=WidgetType.CTA,
            title="Book a tasting",
            description="CTA shown on the catering page",
            config={"fields": ["name", "email"], "button_text": "Request a tasting"},
            status=WidgetStatus.ACTIVE,
        )
        session.add_all([newsletter, tasting])
        await session.flush()

        now = datetime.now(timezone.utc)
        for i in range(25):
            widget = random.choice([newsletter, tasting])
            country, city = random.choice(GEO_SAMPLES)
            submitted_at = now - timedelta(days=random.randint(0, 13), hours=random.randint(0, 23))
            session.add(
                Submission(
                    widget_id=widget.id,
                    tenant_id=tenant.id,
                    payload={"email": f"lead{i}@example.com"},
                    ip_address=f"203.0.113.{random.randint(1, 254)}",
                    geo_country=country,
                    geo_city=city,
                    geo_provider_used="ip_api_com" if country else None,
                    notification_status=random.choice(
                        [NotificationStatus.SENT, NotificationStatus.SENT, NotificationStatus.FAILED]
                    ),
                    created_at=submitted_at,
                )
            )

        print(f"Seeded demo tenant: {tenant.name}")
        print(f"  Login:   {DEMO_EMAIL} / {DEMO_PASSWORD}")
        print(f"  Widgets: {newsletter.title!r}, {tasting.title!r}")
        print("  25 demo submissions spread across the last 2 weeks")


if __name__ == "__main__":
    asyncio.run(seed())
