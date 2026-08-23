"""
Everything in this file is intentionally public and unauthenticated — it's
what a stranger's browser calls when it loads a customer's website. Two
separate concerns, two different caching strategies:

1. GET /widgets/{id}/config — changes whenever the widget owner edits their
   widget, so it's cached SHORT (60s) and carries an ETag keyed on the
   widget's version, so a repeat visitor gets a cheap 304 instead of a full
   payload.
2. GET /static/widget/widget.v{n}.js — the loader script itself changes only
   when we ship a new version, which is a new URL. Because the URL itself
   changes on any change, we can tell the browser to cache this forever.
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.widgets import WidgetRepository

router = APIRouter(tags=["public"])

STATIC_DIR = Path(__file__).resolve().parents[2] / "static"
WIDGET_BUNDLE_PATH = STATIC_DIR / "widget" / "widget.v1.js"


@router.get("/widgets/{widget_id}/config")
async def get_widget_config(
    widget_id: uuid.UUID,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    repo = WidgetRepository(db)
    widget = await repo.get_active_public(widget_id)
    if widget is None:
        # Nonexistent widget and paused widget return the identical 404 —
        # the public internet shouldn't be able to tell them apart.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")

    etag = f'W/"{widget.id}-{widget.version}"'
    if request.headers.get("if-none-match") == etag:
        return Response(
            status_code=status.HTTP_304_NOT_MODIFIED,
            headers={"ETag": etag, "Cache-Control": "public, max-age=60"},
        )

    response.headers["Cache-Control"] = "public, max-age=60"
    response.headers["ETag"] = etag
    return {
        "id": str(widget.id),
        "type": widget.type.value,
        "title": widget.title,
        "config": widget.config,
        "version": widget.version,
    }


@router.get("/static/widget/widget.v1.js")
async def get_widget_bundle() -> FileResponse:
    return FileResponse(
        WIDGET_BUNDLE_PATH,
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
