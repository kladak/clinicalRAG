from api.rate_limit import RateLimiter


def test_rate_limiter_blocks_after_limit():
    limiter = RateLimiter(limit_per_minute=3)
    assert limiter.allow("127.0.0.1") is True
    assert limiter.allow("127.0.0.1") is True
    assert limiter.allow("127.0.0.1") is True
    assert limiter.allow("127.0.0.1") is False


def test_rate_limiter_separate_keys():
    limiter = RateLimiter(limit_per_minute=1)
    assert limiter.allow("a") is True
    assert limiter.allow("b") is True
    assert limiter.allow("a") is False
