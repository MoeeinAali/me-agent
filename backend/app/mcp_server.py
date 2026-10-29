"""The same agent over MCP, so a recruiter's assistant (Claude, ChatGPT, ...) can ask about
Moeein directly. Every tool runs the same grounded pipeline; traces are tagged ``mcp``."""

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

from mcp.server import MCPServer

from app.api.deps import build_deps, get_http, get_record
from app.config import get_settings
from app.db.session import session_factory
from app.domain import Audience, ChatRequest
from app.jobs.base import resolve_job
from app.llm.client import get_llm
from app.pipeline.deps import Deps
from app.pipeline.jobfit import job_fit_handler
from app.pipeline.run import run_chat

DepsFactory = Callable[[], AbstractAsyncContextManager[Deps]]

INSTRUCTIONS = (
    "Answers questions about Moeein Aali (software engineer, Sharif University CE student) "
    "strictly from his published record and the APIs it cites. Every answer includes the evidence "
    "and a trace. It refuses facts he did not publish and never acts on his behalf."
)


@asynccontextmanager
async def default_deps() -> AsyncIterator[Deps]:
    async with session_factory()() as session:
        yield build_deps(session, get_llm(), get_record(), get_settings(), get_http())


def build_mcp(make_deps: DepsFactory = default_deps) -> MCPServer:
    server = MCPServer("me-agent", instructions=INSTRUCTIONS, version="0.1.0")

    @server.tool()
    async def ask_about_moeein(question: str, audience: Audience = "general") -> dict[str, Any]:
        """Ask one question about Moeein. Returns the answer, its claims with evidence, and the
        trace (fields read, action taken, missing facts)."""
        async with make_deps() as deps:
            response = await run_chat(
                ChatRequest(message=question, audience=audience),
                "mcp",
                deps,
                job_fit=job_fit_handler(),
            )
        return response.model_dump(mode="json")

    @server.tool()
    async def job_fit(url_or_text: str, audience: Audience = "general") -> dict[str, Any]:
        """Check Moeein against a job posting: an hrcando job link or the posting's text.
        Returns a requirement-by-requirement scorecard with proofs."""
        is_url = url_or_text.strip().startswith(("http://", "https://"))
        posting = await resolve_job(
            url=url_or_text.strip() if is_url else None,
            text=None if is_url else url_or_text,
            pdf=None,
        )
        req = ChatRequest(
            message="Does Moeein fit this role?",
            audience=audience,
            job_text=posting.description_text[: get_settings().max_job_chars],
        )
        async with make_deps() as deps:
            response = await run_chat(req, "mcp", deps, job_fit=job_fit_handler(posting))
        return response.model_dump(mode="json")

    @server.tool()
    async def list_projects() -> list[dict[str, Any]]:
        """Moeein's projects from his record: id, title, summary, date, and tech."""
        async with make_deps() as deps:
            return [
                {
                    "id": p.id,
                    "title": p.title,
                    "summary": p.summary,
                    "date": p.date,
                    "tech": list(p.tech),
                }
                for p in deps.record.projects
            ]

    @server.tool()
    async def get_limits() -> dict[str, Any]:
        """What this agent will not do or discuss."""
        async with make_deps() as deps:
            return deps.record.limits.model_dump(mode="json")

    return server
