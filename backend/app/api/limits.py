"""Reject oversized request bodies before anything parses them (JSON or multipart)."""

from contextlib import suppress

from starlette.types import ASGIApp, Message, Receive, Scope, Send

DEFAULT_MAX_BODY = 64_000
UPLOAD_OVERHEAD = 64_000  # multipart boundaries and the small form fields next to the file


class _TooLarge(Exception):
    pass


class BodySizeLimit:
    """Per-path caps. Content-Length is checked up front; bodies without it (chunked) are
    counted while they stream in and cut off at the cap."""

    def __init__(self, app: ASGIApp, limits: dict[str, int], default: int = DEFAULT_MAX_BODY):
        self.app = app
        self.limits = limits
        self.default = default

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in {"GET", "HEAD", "OPTIONS"}:
            await self.app(scope, receive, send)
            return
        limit = self.limits.get(scope["path"], self.default)
        headers = dict(scope["headers"])
        length = headers.get(b"content-length")
        if length is not None and length.isdigit() and int(length) > limit:
            await self._reject(send)
            return

        received = 0
        started = False
        rejected = False

        async def counted() -> Message:
            nonlocal received, rejected
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit and not rejected:
                    rejected = True
                    if not started:
                        await self._reject(send)
                    raise _TooLarge
            return message

        async def guarded_send(message: Message) -> None:
            nonlocal started
            if rejected:  # we already answered 413; drop whatever the app sends afterwards
                return
            started = started or message["type"] == "http.response.start"
            await send(message)

        with suppress(_TooLarge):
            await self.app(scope, counted, guarded_send)

    @staticmethod
    async def _reject(send: Send) -> None:
        body = b'{"detail":"Request body is too large."}'
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


class RateLimit:
    """Per-client-IP moving-window limit for every route, including mounted apps (MCP).

    The client IP comes from the ASGI scope, which uvicorn fills from X-Forwarded-For only for
    trusted proxies (FORWARDED_ALLOW_IPS). Health checks are exempt.
    """

    EXEMPT = frozenset({"/healthz", "/readyz"})

    def __init__(self, app: ASGIApp, limit: str, client_header: str | None = None) -> None:
        from limits import parse
        from limits.aio.storage import MemoryStorage
        from limits.aio.strategies import MovingWindowRateLimiter

        self.app = app
        self.item = parse(limit)
        self.client_header = client_header.lower().encode() if client_header else None
        self.limiter = MovingWindowRateLimiter(MemoryStorage())

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in self.EXEMPT:
            await self.app(scope, receive, send)
            return
        client = scope.get("client")
        key = client[0] if client else "unknown"
        if self.client_header:
            for name, value in scope.get("headers", []):
                if name == self.client_header and value:
                    key = value.decode("latin-1").strip()
                    break
        if await self.limiter.hit(self.item, key):
            await self.app(scope, receive, send)
            return
        body = b'{"detail":"Too many requests. Please slow down."}'
        await send(
            {
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"retry-after", b"60"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
