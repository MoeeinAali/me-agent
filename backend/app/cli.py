"""``me-agent`` command line: ingestion, knowledge gaps, evals."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Annotated

import typer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.db.session import engine_from
from app.ingest.ingest import ingest as run_ingest
from app.llm.client import get_llm

app = typer.Typer(no_args_is_help=True, help="me-agent operations")


@app.callback()
def main() -> None:
    """me-agent operations."""


def with_session[T](fn: Callable[[AsyncSession], Awaitable[T]]) -> T:
    async def main() -> T:
        engine = engine_from(get_settings())
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as session:
                return await fn(session)
        finally:
            await engine.dispose()

    return asyncio.run(main())


@app.command()
def ingest(
    only: Annotated[list[str] | None, typer.Option(help="Record ids to (re)ingest")] = None,
) -> None:
    """Load data/record.json and data/syllabus.json into the database (incremental)."""
    settings = get_settings()

    async def go(session: AsyncSession) -> None:
        report = await run_ingest(
            session,
            get_llm(),
            settings.record_path,
            settings.syllabus_path,
            settings.data_dir / "aliases.json",
            only_ids=set(only) if only else None,
        )
        typer.echo(
            f"added={report.added} updated={report.updated} "
            f"deleted={report.deleted} embedded={report.embedded}"
        )

    with_session(go)


if __name__ == "__main__":
    app()
