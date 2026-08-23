import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

WidgetTypeLiteral = Literal["signup_form", "cta", "popover"]
WidgetStatusLiteral = Literal["active", "paused"]


class WidgetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")  # reject unknown fields, don't silently ignore them

    type: WidgetTypeLiteral
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    config: dict[str, Any] = Field(default_factory=dict)


class WidgetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    config: dict[str, Any] | None = None
    status: WidgetStatusLiteral | None = None


class WidgetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    type: str
    title: str
    description: str | None
    config: dict[str, Any]
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    embed_snippet: str = ""  # filled in by the router, not stored in the DB
