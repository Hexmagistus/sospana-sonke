"""Tests for the politeness helpers: robots checking and retry/backoff."""
import httpx
import pytest

from app.scraper.politeness import RobotsChecker, RateLimiter, request_with_backoff


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_robots_allows_when_missing():
    def handler(request):
        return httpx.Response(404)
    with _client(handler) as c:
        assert RobotsChecker(c).is_allowed("https://x.co.za/careers") is True


def test_robots_disallows_matching_rule():
    def handler(request):
        return httpx.Response(200, text="User-agent: *\nDisallow: /careers")
    with _client(handler) as c:
        assert RobotsChecker(c).is_allowed("https://x.co.za/careers") is False


def test_rate_limiter_waits_within_min_interval():
    import time as time_mod

    limiter = RateLimiter(min_interval_seconds=2.0)
    # Pretend the domain was last hit 0.5s ago, real elapsed time on top of
    # that stays negligible for the duration of this assertion.
    limiter._last["x.co.za"] = time_mod.monotonic() - 0.5
    waits = []
    limiter.wait("https://x.co.za/b", sleep=waits.append)
    assert len(waits) == 1
    assert 1.4 < waits[0] <= 2.0


def test_rate_limiter_does_not_wait_after_interval_elapsed():
    import time as time_mod

    limiter = RateLimiter(min_interval_seconds=2.0)
    limiter._last["x.co.za"] = time_mod.monotonic() - 3.0  # well past the interval
    waits = []
    limiter.wait("https://x.co.za/b", sleep=waits.append)
    assert waits == []


def test_backoff_retries_on_server_error_then_succeeds():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    sleeps = []
    with _client(handler) as c:
        resp = request_with_backoff(c, "https://x.co.za/api", sleep=sleeps.append)
    assert resp.status_code == 200
    assert calls["n"] == 3
    assert len(sleeps) == 2


def test_backoff_retries_on_429_and_honours_retry_after():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "5"})
        return httpx.Response(200, json={"ok": True})

    sleeps = []
    with _client(handler) as c:
        resp = request_with_backoff(c, "https://x.co.za/api", base_delay=0.1, sleep=sleeps.append)
    assert resp.status_code == 200
    assert sleeps == [5.0]  # Retry-After overrides the tiny exponential default


def test_backoff_gives_up_after_retries_exhausted():
    def handler(request):
        return httpx.Response(500)

    with _client(handler) as c:
        with pytest.raises(httpx.HTTPStatusError):
            request_with_backoff(c, "https://x.co.za/api", retries=2, sleep=lambda s: None)


def test_backoff_does_not_retry_ordinary_4xx():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(404)

    with _client(handler) as c:
        resp = request_with_backoff(c, "https://x.co.za/api", sleep=lambda s: None)
    assert resp.status_code == 404
    assert calls["n"] == 1  # not retried -- caller's raise_for_status() surfaces this
