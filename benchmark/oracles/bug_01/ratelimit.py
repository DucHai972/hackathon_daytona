"""Request rate limiting for the public API.

A limiter admits at most `limit` events in any `window_seconds` interval. The
window is *sliding*: an event recorded at time `t` still counts against a later
event at time `u` for as long as `u - t < window_seconds`. Two events exactly
`window_seconds` apart therefore belong to different windows.

Times are numeric seconds supplied by the caller and never move backwards.
"""

from collections import deque


class RateLimiter:
    def __init__(self, limit, window_seconds):
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self._limit = limit
        self._window = window_seconds
        self._events = deque()

    def allow(self, now):
        """Record an event at `now` and report whether it is admitted."""
        cutoff = now - self._window
        while self._events and self._events[0] <= cutoff:
            self._events.popleft()
        if len(self._events) >= self._limit:
            return False
        self._events.append(now)
        return True
