import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SubmissionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    widget_id: uuid.UUID
    payload: dict[str, Any]
    geo_country: str | None
    geo_city: str | None
    created_at: datetime


class PaginatedSubmissions(BaseModel):
    items: list[SubmissionListItem]
    total: int
    limit: int
    offset: int


class DailyCount(BaseModel):
    date: str
    count: int


class WidgetCount(BaseModel):
    widget_id: uuid.UUID
    widget_title: str
    count: int


class CountryCount(BaseModel):
    country: str | None
    count: int


class StatsResponse(BaseModel):
    total_submissions: int
    submissions_by_day: list[DailyCount]
    submissions_by_widget: list[WidgetCount]
    submissions_by_country: list[CountryCount]
