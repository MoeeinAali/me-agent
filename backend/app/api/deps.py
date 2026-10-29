"""FastAPI dependencies; tests override session, LLM, record, and outbound HTTP client."""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from functools import lru_cache
from typing import Annotated

import httpx
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_session, session_factory
from app.llm.client import LLM, get_llm
from app.pipeline.deps import Deps
from app.record.loader import load_record
from app.record.schema import Record
from app.tools.cache import DbCache


@lru_cache
def get_record() -> Record:
    return load_record(get_settings().record_path)


_http: httpx.AsyncClient | None = None


def get_http() -> httpx.AsyncClient:
    """One shared outbound client per process (connection pooling); closed on shutdown."""
    global _http
    if _http is None:
        _http = httpx.AsyncClient(headers={"user-agent": "me-agent/0.1"})
    return _http


async def close_http() -> None:
    global _http
    if _http is not None:
        await _http.aclose()
        _http = None


SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


def get_session_factory() -> SessionFactory:
    return session_factory()


def build_deps(
    session: AsyncSession, llm: LLM, record: Record, settings: Settings, http: httpx.AsyncClient
) -> Deps:
    return Deps(
        session=session,
        llm=llm,
        record=record,
        settings=settings,
        http=http,
        cache=DbCache(session),
    )


def get_deps(
    session: Annotated[AsyncSession, Depends(get_session)],
    llm: Annotated[LLM, Depends(get_llm)],
    record: Annotated[Record, Depends(get_record)],
    settings: Annotated[Settings, Depends(get_settings)],
    http: Annotated[httpx.AsyncClient, Depends(get_http)],
) -> Deps:
    return Deps(
        session=session,
        llm=llm,
        record=record,
        settings=settings,
        http=http,
        cache=DbCache(session),
    )


DepsDep = Annotated[Deps, Depends(get_deps)]
