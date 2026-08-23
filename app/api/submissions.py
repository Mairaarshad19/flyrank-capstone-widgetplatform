"""
The single most attacked surface in this whole system. Order of operations
in this file is deliberate and matches DESIGN.md / the architecture diagram:

  validate -> rate limit -> widget lookup -> idempotency check -> honeypot
  -> enrich (never blocks) -> store (committed) -> notify (never blocks)

Every step that CAN fail degrades gracefully instead of taking the request
down: rate limiting returns a clean 429, enrichment failure just means no
geo data, and a notification failure is logged and recorded on the row —
never raised back to the client.
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.rate_limit import build_widget_rate_limiter, limiter
from app.db.session import get_db
from app.enrichment.chain import GeoFallbackChain
from app.enrichment.ip_api import IpApiProvider
from app.enrichment.ipapi_co import IpapiCoProvider
from app.models.submission import NotificationStatus, Submission
from app.notifications.base import Notifier
from app.notifications.console import ConsoleNotifier
from app.repositories.submissions import SubmissionRepository
from app.repositories.widgets import WidgetRepository
from app.schemas.submission import SubmissionCreate, SubmissionOut

logger = logging.getLogger("app.submissions")

router = APIRouter(tags=["submissions"])

# Built once from settings at import time. Test-only note: conftest.py sets
# SUBMISSION_RATE_LIMIT_PER_WIDGET before this module is first imported, and
# calls .reset() between tests so bursts in one test can't bleed into another.
widget_rate_limiter = build_widget_rate_limiter(settings.SUBMISSION_RATE_LIMIT_PER_WIDGET)


def get_geo_chain() -> GeoFallbackChain:
    return GeoFallbackChain([IpApiProvider(), IpapiCoProvider()])


def get_notifier() -> Notifier:
    return ConsoleNotifier()


@router.post("/submissions", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.SUBMISSION_RATE_LIMIT_PER_IP)
async def create_submission(
    request: Request,
    data: SubmissionCreate,
    db: AsyncSession = Depends(get_db),
    geo_chain: GeoFallbackChain = Depends(get_geo_chain),
    notifier: Notifier = Depends(get_notifier),
) -> SubmissionOut:
    # --- per-widget rate limit: a separate dimension from the per-IP limit
    # above, so one widget being hammered can't exhaust another's traffic. ---
    if not widget_rate_limiter.allow(str(data.widget_id)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many submissions for this widget. Please try again shortly.",
        )

    # --- widget must exist and be active; nonexistent and paused widgets
    # are indistinguishable to the public internet. ---
    widget_repo = WidgetRepository(db)
    widget = await widget_repo.get_active_public(data.widget_id)
    if widget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")

    submission_repo = SubmissionRepository(db)

    # --- idempotency: a retried submission with the same key returns the
    # ORIGINAL row instead of creating a duplicate lead. ---
    if data.idempotency_key:
        existing = await submission_repo.get_by_idempotency_key(data.widget_id, data.idempotency_key)
        if existing is not None:
            return existing

    # --- spam control: honeypot. Respond exactly like success so a bot never
    # learns its submission was rejected, but store nothing. ---
    if data.honeypot:
        logger.info("submission_dropped_honeypot", extra={"widget_id": str(data.widget_id)})
        return SubmissionOut(id=uuid.uuid4(), widget_id=data.widget_id, created_at=datetime.now(timezone.utc))

    # --- enrichment: try provider A, then B. Never raises, never blocks
    # storage — a submission with no geo data is still a successful submission. ---
    client_ip = request.client.host if request.client else "unknown"
    geo_result, provider_used = await geo_chain.lookup(client_ip)

    submission = Submission(
        widget_id=data.widget_id,
        tenant_id=widget.tenant_id,
        payload=data.fields,
        ip_address=client_ip,
        geo_country=geo_result.country if geo_result else None,
        geo_city=geo_result.city if geo_result else None,
        geo_provider_used=provider_used,
        idempotency_key=data.idempotency_key,
        notification_status=NotificationStatus.SKIPPED,
    )
    submission = await submission_repo.create(submission)

    # --- safe side effect: a failing notification is logged and recorded,
    # but NEVER allowed to turn a stored submission into a failed response. ---
    try:
        await notifier.notify_new_submission(
            tenant_id=widget.tenant_id, widget_id=widget.id, submission_id=submission.id
        )
        submission.notification_status = NotificationStatus.SENT
    except Exception:
        logger.exception("submission_notification_failed", extra={"submission_id": str(submission.id)})
        submission.notification_status = NotificationStatus.FAILED

    return submission
