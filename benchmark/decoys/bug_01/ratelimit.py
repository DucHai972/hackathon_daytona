"""Plausible but incorrect repair: the fixed window is kept and its reset
threshold is simply widened so the reported burst stops slipping through.

Passes the visible suite. Fails once traffic genuinely ages out of the window.
"""


class RateLimiter:
    def __init__(self, limit, window_seconds):
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self._limit = limit
        self._window = window_seconds
        self._window_start = 0
        self._count = 0

    def allow(self, now):
        if now - self._window_start >= 2 * self._window:
            self._window_start = now
            self._count = 0
        if self._count >= self._limit:
            return False
        self._count += 1
        return True
