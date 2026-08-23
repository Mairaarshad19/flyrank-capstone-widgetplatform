import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.widget import Widget
from app.repositories.widgets import WidgetRepository
from app.schemas.widget import WidgetCreate, WidgetOut, WidgetUpdate
from app.services.widgets import WidgetNotFoundError, WidgetService

router = APIRouter(prefix="/widgets", tags=["widgets"])


def get_widget_service(db: AsyncSession = Depends(get_db)) -> WidgetService:
    return WidgetService(WidgetRepository(db))


def _to_widget_out(widget: Widget) -> WidgetOut:
    out = WidgetOut.model_validate(widget)
    out.embed_snippet = f'<script src="{settings.PUBLIC_BASE_URL}/static/widget/widget.js?id={widget.id}"></script>'
    return out


@router.post("", response_model=WidgetOut, status_code=status.HTTP_201_CREATED)
async def create_widget(
    data: WidgetCreate,
    user: CurrentUser = Depends(get_current_user),
    service: WidgetService = Depends(get_widget_service),
) -> WidgetOut:
    widget = await service.create_widget(user.tenant_id, data)
    return _to_widget_out(widget)


@router.get("", response_model=list[WidgetOut])
async def list_widgets(
    user: CurrentUser = Depends(get_current_user),
    service: WidgetService = Depends(get_widget_service),
) -> list[WidgetOut]:
    widgets = await service.list_widgets(user.tenant_id)
    return [_to_widget_out(w) for w in widgets]


@router.get("/{widget_id}", response_model=WidgetOut)
async def get_widget(
    widget_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    service: WidgetService = Depends(get_widget_service),
) -> WidgetOut:
    try:
        widget = await service.get_widget(widget_id, user.tenant_id)
    except WidgetNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")
    return _to_widget_out(widget)


@router.patch("/{widget_id}", response_model=WidgetOut)
async def update_widget(
    widget_id: uuid.UUID,
    data: WidgetUpdate,
    user: CurrentUser = Depends(get_current_user),
    service: WidgetService = Depends(get_widget_service),
) -> WidgetOut:
    try:
        widget = await service.update_widget(widget_id, user.tenant_id, data)
    except WidgetNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")
    return _to_widget_out(widget)


@router.delete("/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_widget(
    widget_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    service: WidgetService = Depends(get_widget_service),
) -> None:
    try:
        await service.delete_widget(widget_id, user.tenant_id)
    except WidgetNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")
