import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, JSON, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class NotificationStatus(str, enum.Enum):
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        # The hottest read path in the system: dashboard time-series queries
        # and pagination, always scoped by tenant.
        Index("ix_submissions_tenant_created", "tenant_id", "created_at"),
        # Per-widget stats.
        Index("ix_submissions_widget_created", "widget_id", "created_at"),
        # Idempotency: a retried submission with the same key can never be
        # inserted twice. Standard SQL semantics mean multiple NULL
        # idempotency_keys never conflict with each other, so submissions
        # that never supplied a key are unaffected.
        UniqueConstraint("widget_id", "idempotency_key", name="uq_submissions_widget_idempotency"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    widget_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("widgets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Denormalized from the parent widget at insert time — see DESIGN.md § 3.
    # Powers tenant-scoped dashboard queries without a join through widgets.
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    geo_country: Mapped[str | None] = mapped_column(String(255))
    geo_city: Mapped[str | None] = mapped_column(String(255))
    # Which provider actually answered ("ip_api_com" / "ipapi_co" / None) —
    # makes the fallback chain's behavior auditable after the fact.
    geo_provider_used: Mapped[str | None] = mapped_column(String(50))
    idempotency_key: Mapped[str | None] = mapped_column(String(100))
    notification_status: Mapped[NotificationStatus] = mapped_column(
        SAEnum(NotificationStatus, values_callable=lambda enum_cls: [m.value for m in enum_cls]),
        default=NotificationStatus.SKIPPED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
