import pytest

from ratelimit import RateLimiter


def test_traffic_ages_out_of_the_window():
    limiter = RateLimiter(limit=2, window_seconds=60)
    assert limiter.allow(0)
    assert limiter.allow(0)
    assert limiter.allow(61) is True


def test_event_exactly_one_window_later_is_a_new_window():
    limiter = RateLimiter(limit=1, window_seconds=10)
    assert limiter.allow(0)
    assert limiter.allow(9) is False
    assert limiter.allow(10) is True


def test_burst_across_a_boundary_is_rejected():
    limiter = RateLimiter(limit=2, window_seconds=60)
    assert limiter.allow(59)
    assert limiter.allow(59)
    assert limiter.allow(61) is False


def test_rejected_events_do_not_consume_budget():
    limiter = RateLimiter(limit=1, window_seconds=10)
    assert limiter.allow(0)
    assert limiter.allow(1) is False
    assert limiter.allow(2) is False
    assert limiter.allow(10) is True


def test_limit_is_never_exceeded_over_a_long_stream():
    limiter = RateLimiter(limit=5, window_seconds=10)
    admitted = [second for second in range(200) if limiter.allow(second)]
    for start in range(0, 200):
        inside = [t for t in admitted if start <= t < start + 10]
        assert len(inside) <= 5, f"window starting at {start} admitted {len(inside)}"


def test_steady_traffic_is_admitted_at_the_configured_rate():
    limiter = RateLimiter(limit=1, window_seconds=5)
    admitted = [second for second in range(0, 30) if limiter.allow(second)]
    assert admitted == [0, 5, 10, 15, 20, 25]


def test_limiters_are_independent():
    first = RateLimiter(limit=1, window_seconds=10)
    second = RateLimiter(limit=1, window_seconds=10)
    assert first.allow(0)
    assert second.allow(0)
    assert first.allow(1) is False
    assert second.allow(1) is False


def test_invalid_configuration_is_still_rejected():
    with pytest.raises(ValueError):
        RateLimiter(0, 10)
    with pytest.raises(ValueError):
        RateLimiter(1, 0)
