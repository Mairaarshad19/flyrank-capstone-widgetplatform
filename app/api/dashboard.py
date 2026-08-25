import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_current_user
from app.db.session import get_db
from app.repositories.submissions import SubmissionRepository
from app.schemas.dashboard import (
    CountryCount,
    DailyCount,
    PaginatedSubmissions,
    StatsResponse,
    SubmissionListItem,
    WidgetCount,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_submission_repo(db: AsyncSession = Depends(get_db)) -> SubmissionRepository:
    return SubmissionRepository(db)


@router.get("/submissions", response_model=PaginatedSubmissions)
async def list_submissions(
    widget_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    repo: SubmissionRepository = Depends(get_submission_repo),
) -> PaginatedSubmissions:
    items, total = await repo.list_for_tenant(user.tenant_id, widget_id, limit, offset)
    return PaginatedSubmissions(
        items=[SubmissionListItem.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    user: CurrentUser = Depends(get_current_user),
    repo: SubmissionRepository = Depends(get_submission_repo),
) -> StatsResponse:
    total = await repo.count_for_tenant(user.tenant_id)
    by_day = await repo.count_by_day(user.tenant_id)
    by_widget = await repo.count_by_widget(user.tenant_id)
    by_country = await repo.count_by_country(user.tenant_id)

    return StatsResponse(
        total_submissions=total,
        submissions_by_day=[DailyCount(date=day, count=count) for day, count in by_day],
        submissions_by_widget=[
            WidgetCount(widget_id=widget_id, widget_title=title, count=count)
            for widget_id, title, count in by_widget
        ],
        submissions_by_country=[CountryCount(country=country, count=count) for country, count in by_country],
    )
