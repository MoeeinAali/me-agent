"""Shared plumbing for external tools: results, and a circuit breaker so a dead API costs one
fast failure instead of a timeout on every request."""

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TypeVar

from app.domain import Evidence, ToolCall

T = TypeVar("T")


@dataclass
class ToolResult:
    ok: bool
    evidence: list[Evidence]
    call: ToolCall


class CircuitOpen(RuntimeError):
    pass


@dataclass
class CircuitBreaker:
    fail_threshold: int = 3
    reset_seconds: float = 60.0
    clock: Callable[[], float] = time.monotonic
    failures: int = 0
    opened_at: float | None = field(default=None)

    async def call(self, fn: Callable[[], Awaitable[T]]) -> T:
        if self.opened_at is not None:
            if self.clock() - self.opened_at < self.reset_seconds:
                raise CircuitOpen("circuit open")
            self.opened_at = None  # half-open: allow one trial
        try:
            result = await fn()
        except Exception:
            self.failures += 1
            if self.failures >= self.fail_threshold:
                self.opened_at = self.clock()
            raise
        self.failures = 0
        return result


def elapsed_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)
