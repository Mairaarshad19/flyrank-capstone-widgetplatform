import pytest

from app.core.config import settings
from app.enrichment.ip_api import IpApiProvider
from app.notifications.console import ConsoleNotifier


@pytest.mark.asyncio
async def test_geo_provider_a_force_fail_toggle_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "GEO_PROVIDER_A_FORCE_FAIL", True)
    provider = IpApiProvider()
    result = await provider.lookup("203.0.113.1")
    assert result is None


@pytest.mark.asyncio
async def test_notify_force_fail_toggle_raises(monkeypatch):
    monkeypatch.setattr(settings, "NOTIFY_FORCE_FAIL", True)
    notifier = ConsoleNotifier()
    with pytest.raises(RuntimeError):
        await notifier.notify_new_submission(
            tenant_id="00000000-0000-0000-0000-000000000000",
            widget_id="00000000-0000-0000-0000-000000000000",
            submission_id="00000000-0000-0000-0000-000000000000",
        )


@pytest.mark.asyncio
async def test_toggles_are_off_by_default(monkeypatch):
    # Guards against ever accidentally shipping these flipped on.
    assert settings.GEO_PROVIDER_A_FORCE_FAIL is False
    assert settings.NOTIFY_FORCE_FAIL is False
