from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from mcp import Client
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import build_deps
from app.config import get_settings
from app.db.models import TraceRow
from app.domain import Claim
from app.llm.fake import FakeLLM
from app.mcp_server import build_mcp
from app.pipeline.deps import Deps
from app.pipeline.generate import GenerationOut
from app.pipeline.understand import UnderstandOut
from app.record.schema import Record
from tests.dbfixtures import two_project_record


def deps_factory(session: AsyncSession, llm: FakeLLM, record: Record):  # type: ignore[no-untyped-def]
    @asynccontextmanager
    async def make() -> AsyncIterator[Deps]:
        async with httpx.AsyncClient() as http:
            yield build_deps(session, llm, record, get_settings(), http)

    return make


async def test_mcp_list_tools_and_call(ingested: AsyncSession) -> None:
    record = Record.model_validate(two_project_record())
    llm = FakeLLM()
    server = build_mcp(deps_factory(ingested, llm, record))

    async with Client(server) as client:
        names = {tool.name for tool in (await client.list_tools()).tools}
        assert names == {"ask_about_moeein", "job_fit", "list_projects", "get_limits"}

        limits = await client.call_tool("get_limits", {})
        assert limits.structured_content == record.limits.model_dump(mode="json")

        projects = await client.call_tool("list_projects", {})
        assert [p["id"] for p in projects.structured_content["result"]] == [
            "comeback",
            "kanban-board",
        ]

        llm.script(
            UnderstandOut(
                intent="project_summary",
                language="en",
                entities=["Kanban Board"],
                asks_for="Kanban summary",
                wants_action=None,
            ),
            GenerationOut(
                claims=[Claim(text="A drag-and-drop board.", evidence=["E1"])], missing=[]
            ),
        )
        answer = await client.call_tool("ask_about_moeein", {"question": "Summarize Kanban"})
        assert answer.structured_content["answer"] == "A drag-and-drop board."

    channels = (await ingested.scalars(select(TraceRow.channel))).all()
    assert channels == ["mcp"]


async def test_mcp_is_mounted_over_streamable_http() -> None:
    from app.api.main import create_app

    app = create_app()
    async with app.state.mcp.session_manager.run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/mcp/",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "t", "version": "1"},
                    },
                },
                headers={"accept": "application/json, text/event-stream"},
            )
    assert response.status_code == 200, response.text
    assert response.json()["result"]["serverInfo"]["name"] == "me-agent"
