"""A real Postgres + pgvector for tests, migrated with Alembic, truncated between tests."""

import json
import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.community.postgres import PostgresContainer

from app.ingest.ingest import ingest
from app.llm.fake import FakeLLM
from tests.record.factories import minimal_record

BACKEND = Path(__file__).resolve().parents[1]

# Ryuk (the container reaper) is another image pull; the `with` block below cleans up itself.
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    with PostgresContainer("pgvector/pgvector:pg16", driver="asyncpg") as pg:
        url = pg.get_connection_url()
        config = Config(str(BACKEND / "alembic.ini"))
        config.set_main_option("script_location", str(BACKEND / "alembic"))
        config.set_main_option("sqlalchemy.url", url)
        command.upgrade(config, "head")
        yield url


@pytest.fixture(scope="session")
async def engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(database_url)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    async with engine.begin() as conn:
        tables = (
            await conn.execute(
                text(
                    "select string_agg(quote_ident(tablename), ',') from pg_tables "
                    "where schemaname = 'public' and tablename <> 'alembic_version'"
                )
            )
        ).scalar_one()
        await conn.execute(text(f"truncate {tables} restart identity cascade"))


def two_project_record() -> dict[str, object]:
    payload = minimal_record()
    payload["projects"][0].update(
        tech=["Next.js", "Bazel", "Kubernetes"], highlights=["Served over one million users"]
    )
    payload["projects"].append(
        {
            "id": "kanban-board",
            "title": "Kanban Board",
            "summary": "A drag-and-drop task board.",
            "date": "2026-02",
            "tags": ["react"],
            "tech": ["React", "DnDKit"],
            "github_repo": "moeeinaali/kanban-board",
        }
    )
    payload["experience"] = [
        {
            "id": "yektanet-uranus",
            "company": "Yektanet",
            "role": "Software Engineer, Uranus Business Line",
            "employment": "Full-time",
            "start": "January 2025",
            "end": "May 2026",
            "bullets": ["Built the Uranus website."],
        }
    ]
    payload["books"] = [
        {"id": "clean-code", "title": "Clean Code", "author": "Robert C. Martin", "status": "read"}
    ]
    return payload


@pytest.fixture
async def ingested(session: AsyncSession, tmp_path: Path) -> AsyncSession:
    (tmp_path / "record.json").write_text(json.dumps(two_project_record()), encoding="utf-8")
    (tmp_path / "syllabus.json").write_text("[]", encoding="utf-8")
    (tmp_path / "aliases.json").write_text('{"comeback": ["کامبک"]}', encoding="utf-8")
    await ingest(
        session,
        FakeLLM(),
        tmp_path / "record.json",
        tmp_path / "syllabus.json",
        tmp_path / "aliases.json",
    )
    return session
