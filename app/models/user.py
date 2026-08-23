import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class UserRole(str, enum.Enum):
    OWNER = "owner"
    MEMBER = "member"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    # Never returned in any response schema, never logged. See app/core/security.py.
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    # values_callable forces SQLAlchemy to store the enum's VALUE ("owner"),
    # not its Python member NAME ("OWNER") — its default behavior. The
    # Postgres migration created the native enum type with lowercase values,
    # so without this, every insert fails with
    # "invalid input value for enum userrole: OWNER".
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, values_callable=lambda enum_cls: [member.value for member in enum_cls]),
        default=UserRole.OWNER,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="users")
