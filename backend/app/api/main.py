"""The FastAPI application."""

import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api import routes_chat, routes_meta
from app.api.deps import close_http
from app.config import get_settings
from app.jobs.base import JobFetchError, JobInputError
from app.logging import configure_logging

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
    await close_http()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    app = FastAPI(
        title="me-agent",
        version="0.1.0",
        summary="A grounded, explainable agent that answers questions about Moeein Aali.",
        lifespan=lifespan,
    )

    limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["content-type", "x-request-id"],
        expose_headers=["x-request-id"],
    )

    @app.middleware("http")
    async def request_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        structlog.contextvars.bind_contextvars(request_id=rid)
        start = time.monotonic()
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers["x-request-id"] = rid
        log.info(
            "request",
            path=request.url.path,
            status=response.status_code,
            ms=int((time.monotonic() - start) * 1000),
            request_id=rid,
        )
        return response

    @app.exception_handler(JobInputError)
    async def job_input_error(_request: Request, exc: JobInputError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(JobFetchError)
    async def job_fetch_error(_request: Request, exc: JobFetchError) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={"detail": f"{exc}. Please paste the job description text instead."},
        )

    app.include_router(routes_chat.router)
    app.include_router(routes_meta.router)
    return app


app = create_app()
