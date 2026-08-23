import uuid

import httpx

from app.core.config import settings
from app.notifications.base import Notifier


class WebhookNotifier(Notifier):
    async def notify_new_submission(self, *, tenant_id: uuid.UUID, widget_id: uuid.UUID, submission_id: uuid.UUID) -> None:
        if not settings.NOTIFY_WEBHOOK_URL:
            raise RuntimeError("NOTIFY_WEBHOOK_URL is not configured")
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                settings.NOTIFY_WEBHOOK_URL,
                json={
                    "tenant_id": str(tenant_id),
                    "widget_id": str(widget_id),
                    "submission_id": str(submission_id),
                },
            )
            resp.raise_for_status()
