"""
Tries each provider in order and returns the first real answer. If every
provider fails, returns (None, None) — the caller stores the submission
anyway, just without geo data. This function must never raise; a dead
upstream geo provider can never be allowed to take down submission storage.
"""
import logging

from app.enrichment.base import GeoProvider, GeoResult

logger = logging.getLogger("app.enrichment")


class GeoFallbackChain:
    def __init__(self, providers: list[GeoProvider]):
        self.providers = providers

    async def lookup(self, ip_address: str) -> tuple[GeoResult | None, str | None]:
        for provider in self.providers:
            try:
                result = await provider.lookup(ip_address)
            except Exception:
                # Belt-and-braces: providers are contracted to never raise,
                # but the chain doesn't trust that blindly either.
                logger.warning("geo_provider_raised_unexpectedly", extra={"provider": provider.name})
                continue

            if result is not None:
                return result, provider.name

            logger.info("geo_provider_no_result", extra={"provider": provider.name})

        logger.warning("geo_enrichment_exhausted_all_providers")
        return None, None
