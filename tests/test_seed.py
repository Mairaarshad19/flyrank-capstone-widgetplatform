import contextlib

import pytest
from sqlalchemy import func, select

from app import seed as seed_module
from app.models.submission import Submission
from app.models.user import User
from app.models.widget import Widget
from app.schemas.auth import RegisterRequest


def _patch_session_scope(monkeypatch, db_session):
    @contextlib.asynccontextmanager
    async def fake_session_scope():
        yield db_session

    monkeypatch.setattr(seed_module, "session_scope", fake_session_scope)


def test_demo_email_passes_the_same_validation_register_uses():
    """Regression test: demo@acme-bakery.test previously failed here, because
    email-validator (which backs Pydantic's EmailStr) rejects RFC 2606
    reserved TLDs (.test/.example/.invalid/.localhost) as a syntax-level
    guard — independent of DNS deliverability checks. This caused
    POST /auth/register to 422 on the seeded demo login before login() ever
    ran. This test validates the DEMO_EMAIL constant through the exact same
    Pydantic schema the real endpoint uses, so this class of bug can't
    silently come back if the demo email is ever changed again."""
    RegisterRequest(tenant_name="Acme Bakery (demo)", email=seed_module.DEMO_EMAIL, password=seed_module.DEMO_PASSWORD)


@pytest.mark.asyncio
async def test_seed_creates_demo_tenant_widgets_and_submissions(monkeypatch, db_session):
    _patch_session_scope(monkeypatch, db_session)

    await seed_module.seed()

    user_result = await db_session.execute(select(User).where(User.email == seed_module.DEMO_EMAIL))
    assert user_result.scalar_one_or_none() is not None

    widgets_result = await db_session.execute(select(Widget))
    assert len(widgets_result.scalars().all()) == 2

    submissions_result = await db_session.execute(select(Submission))
    assert len(submissions_result.scalars().all()) == 25


@pytest.mark.asyncio
async def test_seed_is_idempotent_on_second_run(monkeypatch, db_session, capsys):
    _patch_session_scope(monkeypatch, db_session)

    await seed_module.seed()
    await seed_module.seed()  # second call must be a no-op, not a duplicate

    user_count = await db_session.execute(
        select(func.count()).select_from(User).where(User.email == seed_module.DEMO_EMAIL)
    )
    assert user_count.scalar_one() == 1

    submission_count = await db_session.execute(select(func.count()).select_from(Submission))
    assert submission_count.scalar_one() == 25  # not 50

    captured = capsys.readouterr()
    assert "already seeded" in captured.out
