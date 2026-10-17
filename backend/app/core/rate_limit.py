"""In-memory fixed-window rate limiter (API_SPEC §2.4). Valid for a single process only.

Disabled when THUNAI_ENV=test, except in tests that turn it on explicitly.
"""

import threading
import time
from collections.abc import Callable

from app.core.errors import RateLimited


class RateLimiter:
    def __init__(self, *, enabled: bool, clock: Callable[[], float] = time.monotonic) -> None:
        self.enabled = enabled
        self._clock = clock
        self._lock = threading.Lock()
        self._windows: dict[str, tuple[float, int]] = {}

    def hit(self, key: str, limit: int, window_seconds: int) -> None:
        """Count one request. Raises RateLimited once `limit` is exceeded in the window."""
        if not self.enabled:
            return
        now = self._clock()
        with self._lock:
            started, count = self._windows.get(key, (now, 0))
            if now - started >= window_seconds:
                started, count = now, 0
            count += 1
            self._windows[key] = (started, count)
            if len(self._windows) > 50_000:
                self._evict(now)
        if count > limit:
            raise RateLimited(int(window_seconds - (now - started)) + 1)

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        """Raise if the key is already over its limit, without counting a new hit."""
        if not self.enabled:
            return
        now = self._clock()
        with self._lock:
            started, count = self._windows.get(key, (now, 0))
        if now - started < window_seconds and count >= limit:
            raise RateLimited(int(window_seconds - (now - started)) + 1)

    def reset(self, key: str) -> None:
        with self._lock:
            self._windows.pop(key, None)

    def _evict(self, now: float) -> None:
        stale = [k for k, (start, _) in self._windows.items() if now - start > 3600]
        for key in stale:
            del self._windows[key]
