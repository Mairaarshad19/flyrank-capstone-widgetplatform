"""add submissions table

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    notification_status_enum = postgresql.ENUM("sent", "failed", "skipped", name="notificationstatus")

    op.create_table(
        "submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "widget_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("widgets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("geo_country", sa.String(length=255), nullable=True),
        sa.Column("geo_city", sa.String(length=255), nullable=True),
        sa.Column("geo_provider_used", sa.String(length=50), nullable=True),
        sa.Column("idempotency_key", sa.String(length=100), nullable=True),
        sa.Column("notification_status", notification_status_enum, nullable=False, server_default="skipped"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("widget_id", "idempotency_key", name="uq_submissions_widget_idempotency"),
    )
    op.create_index("ix_submissions_widget_id", "submissions", ["widget_id"])
    op.create_index("ix_submissions_tenant_id", "submissions", ["tenant_id"])
    op.create_index("ix_submissions_tenant_created", "submissions", ["tenant_id", "created_at"])
    op.create_index("ix_submissions_widget_created", "submissions", ["widget_id", "created_at"])


def downgrade() -> None:
    op.drop_table("submissions")
    op.execute("DROP TYPE IF EXISTS notificationstatus")
