from datetime import UTC, datetime, timedelta

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ExternalCache
from app.tools.cache import DbCache


async def test_db_cache_roundtrip_and_upsert(session: AsyncSession) -> None:
    cache = DbCache(session)
    assert await cache.get("k") is None
    await cache.set("k", "github", {"v": 1}, ttl=60)
    await cache.set("k", "github", {"v": 2}, ttl=60)
    assert await cache.get("k") == {"v": 2}


async def test_db_cache_expires(session: AsyncSession) -> None:
    cache = DbCache(session)
    await cache.set("old", "link_check", {"status": 200}, ttl=60)
    await session.execute(
        update(ExternalCache)
        .where(ExternalCache.key == "old")
        .values(fetched_at=datetime.now(UTC) - timedelta(seconds=61))
    )
    await session.commit()
    session.expire_all()
    assert await cache.get("old") is None
