"""Is a project's live link up right now? Feeds the "verifiable CV" proof status."""

import time
from datetime import UTC, datetime

import httpx

from app.domain import Evidence, Proof, ToolCall
from app.tools.base import ToolResult, elapsed_ms
from app.tools.cache import Cache

TTL_SECONDS = 3600
TIMEOUT_SECONDS = 5.0


class LinkChecker:
    def __init__(self, client: httpx.AsyncClient, cache: Cache) -> None:
        self._client = client
        self._cache = cache

    async def check(self, url: str, path: str) -> ToolResult:
        start = time.monotonic()
        key = f"link:{url}"
        payload = await self._cache.get(key)
        if payload is None:
            payload = {
                "status": await self._status(url),
                "checked_at": datetime.now(UTC).isoformat(),
            }
            await self._cache.set(key, "link_check", payload, TTL_SECONDS)
        code: int | None = payload["status"]
        up = code is not None and code < 400
        value = f"{url} is {'up' if up else 'down'}" + (f" (HTTP {code})" if code else "")
        evidence = Evidence(
            id="",
            path=path,
            value=value,
            source="link_check",
            trusted=True,
            proof=Proof(
                type="live_url",
                url=url,
                status="up" if up else "down",
                checked_at=datetime.fromisoformat(payload["checked_at"]),
            ),
        )
        return ToolResult(
            True,
            [evidence],
            ToolCall(name=f"link_check:{url}", ok=True, latency_ms=elapsed_ms(start)),
        )

    async def _status(self, url: str) -> int | None:
        for method in ("HEAD", "GET"):
            try:
                response = await self._client.request(
                    method, url, timeout=TIMEOUT_SECONDS, follow_redirects=True
                )
            except httpx.HTTPError:
                continue
            if method == "HEAD" and response.status_code in (403, 405, 501):
                continue
            return response.status_code
        return None
