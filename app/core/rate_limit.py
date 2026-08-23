"""
Two independent rate-limit dimensions, deliberately implemented two
different ways:

- Per-IP uses slowapi (built on the `limits` library) — the standard,
  well-tested choice for "limit by client address," which is exactly what
  its key_func extraction is designed for.
- Per-widget uses a small custom in-process sliding-window counter, because
  the widget_id lives inside the JSON request body, not somewhere slowapi's
  key_func can see before the body is parsed. Isolating it in one small class
  here means swapping this for a Redis-backed limiter later (needed the
  moment this runs on more than one instance) is a one-file change.
"""
import time
from collections import defaultdict, deque

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        window = self._hits[key]
        while window and now - window[0] > self.window_seconds:
            window.popleft()
        if len(window) >= self.max_requests:
            return False
        window.append(now)
        return True

    def reset(self) -> None:
        """Test-only escape hatch — production never needs to clear counters."""
        self._hits.clear()


def _parse_rate_spec(spec: str) -> tuple[int, int]:
    """'5/minute' -> (5, 60)"""
    count_str, _, unit = spec.partition("/")
    unit = unit.strip().lower()
    seconds = {"second": 1, "minute": 60, "hour": 3600}.get(unit, 60)
    return int(count_str), seconds


def build_widget_rate_limiter(spec: str) -> SlidingWindowRateLimiter:
    max_requests, window_seconds = _parse_rate_spec(spec)
    return SlidingWindowRateLimiter(max_requests=max_requests, window_seconds=window_seconds)
