"""
Database engine + session management.

Design decisions that matter for a system meant to survive real traffic:

1. Pooling is explicit and bounded (pool_size + max_overflow), not "whatever
   the default is." Under a traffic spike, a bounded pool means requests queue
   or fail fast with a clear error — an *unbounded* pool means you silently
   open thousands of connections and take the database down with you.
2. pool_pre_ping=True makes the pool test a connection before handing it out,
   so a connection killed by the DB/network doesn't surface as a random 500
   on some unlucky request.
3. pool_recycle prevents handing out connections older than the DB's own
   idle-connection timeout.
4. The `get_db` dependency is the ONLY place that commits or rolls back.
   Routers/services never call session.commit() themselves — this guarantees
   a half-finished unit of work can never be left committed.
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT_SECONDS,
    pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
    pool_pre_ping=True,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """All models inherit from this so Alembic autogenerate can find them."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: one session per request, committed on success,
    rolled back on any exception, always closed."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Same contract as get_db, for use outside request context
    (e.g. seed scripts, background tasks)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """Used by the readiness probe — a real round trip, not just 'engine exists'."""
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
