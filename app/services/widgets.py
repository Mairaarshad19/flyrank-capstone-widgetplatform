import uuid

from app.models.widget import Widget, WidgetStatus, WidgetType
from app.repositories.widgets import WidgetRepository
from app.schemas.widget import WidgetCreate, WidgetUpdate


class WidgetNotFoundError(Exception):
    """Raised for both 'doesn't exist' and 'belongs to another tenant' —
    the router turns this into a 404 either way. We never let a client
    distinguish the two cases; see DESIGN.md § 3."""


class WidgetService:
    def __init__(self, repo: WidgetRepository):
        self.repo = repo

    async def create_widget(self, tenant_id: uuid.UUID, data: WidgetCreate) -> Widget:
        widget = Widget(
            tenant_id=tenant_id,
            type=WidgetType(data.type),
            title=data.title,
            description=data.description,
            config=data.config,
        )
        return await self.repo.create(widget)

    async def get_widget(self, widget_id: uuid.UUID, tenant_id: uuid.UUID) -> Widget:
        widget = await self.repo.get_by_id(widget_id, tenant_id)
        if widget is None:
            raise WidgetNotFoundError()
        return widget

    async def list_widgets(self, tenant_id: uuid.UUID) -> list[Widget]:
        return await self.repo.list_for_tenant(tenant_id)

    async def update_widget(self, widget_id: uuid.UUID, tenant_id: uuid.UUID, data: WidgetUpdate) -> Widget:
        widget = await self.get_widget(widget_id, tenant_id)

        if data.title is not None:
            widget.title = data.title
        if data.description is not None:
            widget.description = data.description
        if data.status is not None:
            widget.status = WidgetStatus(data.status)
        if data.config is not None:
            widget.config = data.config
            # Bump version so cached public config/script responses (Phase 3)
            # bust correctly — a config change must never serve stale cached data.
            widget.version += 1

        return widget

    async def delete_widget(self, widget_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        widget = await self.get_widget(widget_id, tenant_id)
        await self.repo.delete(widget)
