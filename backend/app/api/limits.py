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
