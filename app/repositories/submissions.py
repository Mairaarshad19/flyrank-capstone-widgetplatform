import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.submission import Submission


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
