"""
Every read/update/delete method here REQUIRES a tenant_id argument and filters
on it. There is deliberately no `get_by_id(widget_id)` without a tenant_id in
this file — that method would be one lazy call site away from a cross-tenant
data leak. (Phase 3 adds a separate, clearly-named `get_public_by_id` for the
public config endpoint, which is intentionally NOT tenant-scoped by design,
not by omission.)
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.widget import Widget, WidgetStatus


class WidgetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, widget: Widget) -> Widget:
        self.session.add(widget)
        await self.session.flush()  # populate widget.id/created_at without ending the transaction
        return widget

    async def get_by_id(self, widget_id: uuid.UUID, tenant_id: uuid.UUID) -> Widget | None:
        stmt = select(Widget).where(Widget.id == widget_id, Widget.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_tenant(self, tenant_id: uuid.UUID) -> list[Widget]:
        stmt = select(Widget).where(Widget.tenant_id == tenant_id).order_by(Widget.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, widget: Widget) -> None:
        await self.session.delete(widget)

    async def get_active_public(self, widget_id: uuid.UUID) -> Widget | None:
        """Public lookup: NO tenant filter, by design, not omission — this is
        what backs the public config endpoint any visitor's browser calls.
        Only ever returns ACTIVE widgets; a paused widget is invisible to the
        public API exactly like a nonexistent one (same 404, no distinction)."""
        stmt = select(Widget).where(Widget.id == widget_id, Widget.status == WidgetStatus.ACTIVE)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
