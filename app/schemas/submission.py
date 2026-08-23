import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_FIELD_VALUE_LENGTH = 2000
MAX_FIELDS_COUNT = 20
MAX_FIELD_NAME_LENGTH = 100


class SubmissionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown fields are rejected, never silently dropped

    widget_id: uuid.UUID
    fields: dict[str, str] = Field(default_factory=dict)
    # Bots fill this; real visitors never see it (see static/widget/widget.v1.js).
    honeypot: str = Field(default="", max_length=500)
    # Generated once by the widget script before the first submit attempt,
    # so a network retry reuses the same key instead of creating a duplicate lead.
    idempotency_key: str | None = Field(default=None, max_length=100)

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, value: dict[str, str]) -> dict[str, str]:
        if not value:
            raise ValueError("fields cannot be empty")
        if len(value) > MAX_FIELDS_COUNT:
            raise ValueError(f"too many fields (max {MAX_FIELDS_COUNT})")
        for key, val in value.items():
            if len(key) > MAX_FIELD_NAME_LENGTH:
                raise ValueError(f"field name '{key[:20]}...' exceeds max length of {MAX_FIELD_NAME_LENGTH}")
            if len(val) > MAX_FIELD_VALUE_LENGTH:
                raise ValueError(f"field '{key}' exceeds max length of {MAX_FIELD_VALUE_LENGTH}")
        return value


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    widget_id: uuid.UUID
    created_at: datetime
