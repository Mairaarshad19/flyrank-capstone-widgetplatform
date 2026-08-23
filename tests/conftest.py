"""
Test isolation matters as much as test coverage: a test suite where tests can
affect each other's outcome is worse than no test suite, because it lies to
you. Every test here gets a fresh in-memory SQLite DB and a fresh app instance
via dependency override — no test can leak state into another.
"""
import os

# Set BEFORE importing app.main, so app.api.submissions builds its rate
# limiters from these test-friendly values instead of the .env.example
# production defaults (60/minute is too high to trip deterministically in a
# fast test). Chosen so the per-IP and per-widget tests can each isolate
# their own dimension — see tests/test_submissions.py for why.
os.environ.setdefault("SUBMISSION_RATE_LIMIT_PER_IP", "10/minute")
os.environ.setdefault("SUBMISSION_RATE_LIMIT_PER_WIDGET", "5/minute")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.db.session import Base, get_db
from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def _reset_rate_limits():
    """slowapi's Limiter and our custom per-widget limiter both keep counters
    in module-level memory, which persists across tests in the same process.
    Without this, a burst in one test can leave another test pre-rate-limited
    before it even starts."""
    from app.core.rate_limit import limiter
    from app.api.submissions import widget_rate_limiter

    limiter.reset()
    widget_rate_limiter.reset()
    yield


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
