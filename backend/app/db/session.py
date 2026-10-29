"""Async engine and session factory."""

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings, get_settings


def engine_from(settings: Settings) -> AsyncEngine:
    return create_async_engine(settings.database_url, pool_pre_ping=True, pool_size=10)


@lru_cache
def _sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine_from(get_settings()), expire_on_commit=False)


def session_factory() -> async_sessionmaker[AsyncSession]:
    """For work that outlives a request dependency (streaming responses, background jobs)."""
    return _sessionmaker()


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request."""
    async with _sessionmaker()() as session:
        yield session
