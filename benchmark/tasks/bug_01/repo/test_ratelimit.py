import pytest

from ratelimit import RateLimiter


def test_burst_across_a_window_boundary_is_rejected():
    limiter = RateLimiter(limit=2, window_seconds=60)
    assert limiter.allow(59)
    assert limiter.allow(59)
    assert limiter.allow(61) is False


def test_requests_within_the_limit_are_admitted():
    limiter = RateLimiter(limit=3, window_seconds=10)
    assert limiter.allow(0)
    assert limiter.allow(1)
    assert limiter.allow(2)


def test_invalid_configuration_is_rejected():
    with pytest.raises(ValueError):
        RateLimiter(0, 10)
    with pytest.raises(ValueError):
        RateLimiter(1, 0)
