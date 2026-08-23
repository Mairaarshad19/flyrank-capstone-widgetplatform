import httpx

from app.core.config import settings
from app.enrichment.base import GeoProvider, GeoResult


class IpapiCoProvider(GeoProvider):
    name = "ipapi_co"

    async def lookup(self, ip_address: str) -> GeoResult | None:
        url = settings.GEO_PROVIDER_B_URL.format(ip=ip_address)
        try:
            async with httpx.AsyncClient(timeout=settings.GEO_PROVIDER_TIMEOUT_SECONDS) as client:
                resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                return None
            return GeoResult(country=data.get("country_name"), city=data.get("city"))
        except Exception:
            return None
