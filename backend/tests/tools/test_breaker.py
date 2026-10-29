import pytest

from app.tools.base import CircuitBreaker, CircuitOpen


async def test_breaker_opens_after_3_failures() -> None:
    now = [0.0]
    breaker = CircuitBreaker(fail_threshold=3, reset_seconds=60, clock=lambda: now[0])

    async def boom() -> None:
        raise RuntimeError("down")

    for _ in range(3):
        with pytest.raises(RuntimeError):
            await breaker.call(boom)
    with pytest.raises(CircuitOpen):
        await breaker.call(boom)

    now[0] = 61.0  # half-open: one trial call goes through

    async def ok() -> str:
        return "ok"

    assert await breaker.call(ok) == "ok"
    assert breaker.failures == 0
