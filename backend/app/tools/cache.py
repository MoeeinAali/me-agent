"""Cache for external API responses (GitHub, link checks): Postgres in production, memory in
tests and one-off scripts."""

from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ExternalCache


class Cache(Protocol):
    async def get(self, key: str) -> dict[str, Any] | None: ...

    async def set(self, key: str, source: str, payload: dict[str, Any], ttl: int) -> None: ...


class MemoryCache:
    def __init__(self) -> None:
        self._items: dict[str, tuple[datetime, dict[str, Any]]] = {}

    async def get(self, key: str) -> dict[str, Any] | None:
        item = self._items.get(key)
        if item is None or item[0] < datetime.now(UTC):
            return None
        return item[1]

    async def set(self, key: str, source: str, payload: dict[str, Any], ttl: int) -> None:
        self._items[key] = (datetime.now(UTC) + timedelta(seconds=ttl), payload)


class DbCache:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, key: str) -> dict[str, Any] | None:
        row = await self._session.scalar(select(ExternalCache).where(ExternalCache.key == key))
        if row is None:
            return None
        if row.fetched_at + timedelta(seconds=row.ttl_seconds) < datetime.now(UTC):
            return None
        return row.payload

    async def set(self, key: str, source: str, payload: dict[str, Any], ttl: int) -> None:
        values = {
            "key": key,
            "source": source,
            "payload": payload,
            "fetched_at": datetime.now(UTC),
            "ttl_seconds": ttl,
        }
        statement = insert(ExternalCache).values(**values)
        await self._session.execute(
            statement.on_conflict_do_update(index_elements=["key"], set_=values)
        )
        await self._session.commit()
