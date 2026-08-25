import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.submission import Submission
from app.models.widget import Widget


class SubmissionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, submission: Submission) -> Submission:
        self.session.add(submission)
        await self.session.flush()
        return submission

    async def get_by_idempotency_key(self, widget_id: uuid.UUID, idempotency_key: str) -> Submission | None:
        stmt = select(Submission).where(
            Submission.widget_id == widget_id, Submission.idempotency_key == idempotency_key
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # --- Dashboard / analytics queries. Every one of these filters by
    # tenant_id — see DESIGN.md § 3. ---

    async def list_for_tenant(
        self, tenant_id: uuid.UUID, widget_id: uuid.UUID | None, limit: int, offset: int
    ) -> tuple[list[Submission], int]:
        filters = [Submission.tenant_id == tenant_id]
        if widget_id is not None:
            filters.append(Submission.widget_id == widget_id)

        count_stmt = select(func.count()).select_from(Submission).where(and_(*filters))
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Submission)
            .where(and_(*filters))
            .order_by(Submission.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def count_for_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Submission).where(Submission.tenant_id == tenant_id)
        return (await self.session.execute(stmt)).scalar_one()

    async def count_by_day(self, tenant_id: uuid.UUID) -> list[tuple[str, int]]:
        # func.date() works identically as a grouping key on both SQLite
        # (used in tests) and Postgres (production) — see BUILDLOG.md for a
        # prior bug caused by exactly this kind of dialect mismatch, which is
        # why this comment exists.
        day_expr = func.date(Submission.created_at)
        stmt = (
            select(day_expr.label("day"), func.count().label("count"))
            .where(Submission.tenant_id == tenant_id)
            .group_by(day_expr)
            .order_by(day_expr)
        )
        result = await self.session.execute(stmt)
        return [(str(row.day), row.count) for row in result.all()]

    async def count_by_widget(self, tenant_id: uuid.UUID) -> list[tuple[uuid.UUID, str, int]]:
        stmt = (
            select(Widget.id, Widget.title, func.count(Submission.id).label("count"))
            .join(Submission, Submission.widget_id == Widget.id)
            .where(Widget.tenant_id == tenant_id)
            .group_by(Widget.id, Widget.title)
            .order_by(func.count(Submission.id).desc())
        )
        result = await self.session.execute(stmt)
        return [(row.id, row.title, row.count) for row in result.all()]

    async def count_by_country(self, tenant_id: uuid.UUID) -> list[tuple[str | None, int]]:
        stmt = (
            select(Submission.geo_country, func.count().label("count"))
            .where(Submission.tenant_id == tenant_id)
            .group_by(Submission.geo_country)
            .order_by(func.count().desc())
        )
        result = await self.session.execute(stmt)
        return [(row.geo_country, row.count) for row in result.all()]
