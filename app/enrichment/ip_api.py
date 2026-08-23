import httpx

from app.core.config import settings
from app.enrichment.base import GeoProvider, GeoResult


class IpApiProvider(GeoProvider):
    name = "ip_api_com"

    async def lookup(self, ip_address: str) -> GeoResult | None:
        url = settings.GEO_PROVIDER_A_URL.format(ip=ip_address)
        try:
            async with httpx.AsyncClient(timeout=settings.GEO_PROVIDER_TIMEOUT_SECONDS) as client:
                resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != "success":
                return None
            return GeoResult(country=data.get("country"), city=data.get("city"))
        except Exception:
            # Timeout, connection error, bad JSON, unexpected shape — all of
            # it degrades to "this provider has no answer," never a crash.
            return None
