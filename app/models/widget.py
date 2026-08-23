import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, Integer, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class WidgetType(str, enum.Enum):
    SIGNUP_FORM = "signup_form"
    CTA = "cta"
    POPOVER = "popover"


class WidgetStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"


class Widget(Base):
    __tablename__ = "widgets"
    __table_args__ = (
        # Powers "list my active widgets" — the most common owner-side query.
        Index("ix_widgets_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[WidgetType] = mapped_column(SAEnum(WidgetType), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    # Form fields, button text, display options. See DESIGN.md § 6 non-goal —
    # this is configured as JSON, not through a visual builder.
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[WidgetStatus] = mapped_column(SAEnum(WidgetStatus), default=WidgetStatus.ACTIVE, nullable=False)
    # Bumped on every config change. Phase 3 uses this to cache-bust the
    # public config endpoint without needing a content hash.
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="widgets")
