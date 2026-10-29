"""``me-agent`` command line: ingestion, knowledge gaps, evals."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import date
from typing import TYPE_CHECKING, Annotated

import typer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.db.session import engine_from
from app.ingest.ingest import ingest as run_ingest
from app.llm.client import get_llm

if TYPE_CHECKING:
    from rich.table import Table

app = typer.Typer(no_args_is_help=True, help="me-agent operations")
gaps_app = typer.Typer(help="Questions the record could not answer")
app.add_typer(gaps_app, name="gaps")


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


def gap_table(rows: list[tuple[int, int, str, str, str]]) -> "Table":
    """Visitor questions are untrusted: render them as plain text, never as Rich markup."""
    from rich.table import Table
    from rich.text import Text

    from app.text import one_line

    table = Table("id", "count", "lang", "question", "last seen")
    for gap_id, count, lang, question, seen in rows:
        table.add_row(str(gap_id), str(count), lang, Text(one_line(question)), seen)
    return table


@gaps_app.callback(invoke_without_command=True)
def gaps(ctx: typer.Context) -> None:
    """List open gaps, most-asked first."""
    if ctx.invoked_subcommand is not None:
        return
    from rich.console import Console
    from rich.table import Table

    from app.gaps.manage import list_gaps

    async def go(session: AsyncSession) -> None:
        table = Table("id", "count", "lang", "question", "last seen")
        for gap in await list_gaps(session):
            table.add_row(
                str(gap.id),
                str(gap.count),
                gap.language,
                gap.question,
                gap.last_seen.strftime("%Y-%m-%d"),
            )
        Console().print(table)

    with_session(go)


@gaps_app.command("answer")
def gaps_answer(
    gap_id: int,
    text: str,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show the FAQ entry only")] = False,
    question: Annotated[
        str | None, typer.Option(help="Your wording of the FAQ question (default: visitor's)")
    ] = None,
) -> None:
    """Add the answer to data/record.json as a FAQ entry and make it searchable now."""
    from app.gaps.manage import answer_gap

    async def go(session: AsyncSession) -> None:
        result = await answer_gap(
            session,
            get_llm(),
            get_settings().data_dir,
            gap_id,
            text,
            today=date.today().isoformat(),
            dry_run=dry_run,
        )
        typer.echo(result.preview)
        if dry_run:
            typer.echo("dry run: nothing written")
        else:
            typer.echo(
                f"added {result.faq_id} to data/record.json and embedded it. "
                "Commit data/record.json so the next deploy keeps it."
            )

    with_session(go)


@gaps_app.command("ignore")
def gaps_ignore(gap_id: int) -> None:
    """Close a gap without answering it (e.g. a topic Moeein won't publish)."""
    from app.gaps.manage import ignore_gap

    with_session(lambda session: ignore_gap(session, gap_id))
    typer.echo(f"gap {gap_id} ignored")


@app.command("eval")
def run_eval(
    subset: Annotated[str | None, typer.Option(help="Only cases tagged with this subset")] = None,
    judge: Annotated[bool, typer.Option(help="Also run the LLM groundedness judge")] = True,
    min_pass: Annotated[float, typer.Option(help="Fail below this pass rate")] = 0.85,
) -> None:
    """Run the eval suite against the real model; exit 1 if the pass rate is too low."""
    import httpx

    from app.api.deps import build_deps, get_record
    from app.evals.runner import run_suite

    async def go(session: AsyncSession) -> float:
        async with httpx.AsyncClient() as http:
            deps = build_deps(session, get_llm(), get_record(), get_settings(), http)
            run, results = await run_suite(deps, session, subset, judge)
        for result in results:
            mark = "PASS" if result.passed else "FAIL"
            typer.echo(
                f"{mark} [{result.case.category}] {result.case.id}: " + "; ".join(result.failures)
            )
        for category, counts in run.summary.items():
            typer.echo(f"{category:>22}: {counts['passed']}/{counts['total']}")
        rate = run.passed / run.total if run.total else 0.0
        typer.echo(f"overall: {run.passed}/{run.total} = {rate:.0%} (prompt {run.prompt_version})")
        return rate

    if with_session(go) < min_pass:
        raise typer.Exit(code=1)


@app.command("traces")
def traces(
    capability: Annotated[str | None, typer.Option(help="Only this capability")] = None,
    limit: Annotated[int, typer.Option(help="How many, newest first")] = 5,
) -> None:
    """Print recent traces in the assignment's report format."""
    from app.traces import format_trace, latest_traces

    async def go(session: AsyncSession) -> None:
        for data in await latest_traces(session, capability, limit):
            typer.echo(format_trace(data) + "\n")

    with_session(go)


if __name__ == "__main__":
    app()
