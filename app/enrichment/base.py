"""
Every provider implementation MUST catch its own exceptions and return None
on any failure (timeout, bad response, rate limit, malformed JSON) — never
raise. The fallback chain in chain.py relies on that contract completely;
a provider that raises would break the "degrade, never fail" guarantee for
the whole submission path.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GeoResult:
    country: str | None
    city: str | None


class GeoProvider(ABC):
    name: str

    @abstractmethod
    async def lookup(self, ip_address: str) -> GeoResult | None: ...
