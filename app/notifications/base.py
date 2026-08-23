"""
Unlike GeoProvider, a Notifier IS allowed to raise — the safety guarantee
lives in the caller (app/api/submissions.py), which wraps every notify call
in try/except and records the outcome on the submission itself
(NotificationStatus.SENT/FAILED) without ever letting the exception affect
the HTTP response. Keeping the "may raise" contract here, rather than forcing
every notifier to swallow its own errors, keeps failure visible in logs
instead of silently disappearing inside the notifier.
"""
import uuid
from abc import ABC, abstractmethod


class Notifier(ABC):
    @abstractmethod
    async def notify_new_submission(self, *, tenant_id: uuid.UUID, widget_id: uuid.UUID, submission_id: uuid.UUID) -> None: ...
