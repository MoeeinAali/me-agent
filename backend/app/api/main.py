"""The FastAPI application."""

import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import openai
import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    routes_chat,
    routes_jobs,
    routes_meta,
    routes_stream,
    routes_suggest,
    routes_voice,
)
from app.api.deps import close_http
from app.api.limits import UPLOAD_OVERHEAD, BodySizeLimit, RateLimit
from app.config import get_settings
from app.jobs.base import JobFetchError, JobInputError
from app.llm.client import LLM_UNAVAILABLE
from app.logging import configure_logging
from app.mcp_server import build_mcp

log = structlog.get_logger()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    mcp = build_mcp()
    mcp_app = mcp.streamable_http_app(
        streamable_http_path="/", stateless_http=True, json_response=True, host="0.0.0.0"
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        async with mcp.session_manager.run():
            yield
        await close_http()

    app = FastAPI(
        title="me-agent",
        version="0.1.0",
        summary="A grounded, explainable agent that answers questions about Moeein Aali.",
        lifespan=lifespan,
    )

    app.add_middleware(
        RateLimit, limit=settings.rate_limit, client_header=settings.rate_limit_client_header
    )
    app.add_middleware(
        BodySizeLimit,
        limits={
            "/v1/jobs/fit": settings.max_pdf_bytes + UPLOAD_OVERHEAD,
            "/v1/voice": settings.max_audio_bytes + UPLOAD_OVERHEAD,
        },
    )
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

    @app.exception_handler(openai.APIError)
    async def llm_unavailable(_request: Request, exc: openai.APIError) -> JSONResponse:
        log.error("llm_unavailable", error=type(exc).__name__, detail=str(exc)[:300])
        return JSONResponse(status_code=503, content={"detail": LLM_UNAVAILABLE})

    app.state.mcp = mcp
    app.mount("/mcp", mcp_app)
    app.include_router(routes_chat.router)
    app.include_router(routes_jobs.router)
    app.include_router(routes_stream.router)
    app.include_router(routes_suggest.router)
    app.include_router(routes_voice.router)
    app.include_router(routes_meta.router)
    return app


app = create_app()
