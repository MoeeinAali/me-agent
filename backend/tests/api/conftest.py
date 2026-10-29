import json
from collections.abc import AsyncIterator

import httpx
import pytest
import respx
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_http, get_record
from app.api.main import create_app
from app.db.session import get_session
from app.llm.client import get_llm
from app.llm.fake import FakeLLM
from app.record.schema import Record
from tests.dbfixtures import two_project_record


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def test_record() -> Record:
    payload = two_project_record()
    with open("../data/record.json", encoding="utf-8") as f:
        payload["limits"] = json.load(f)["limits"]
    return Record.model_validate(payload)


@pytest.fixture
def external() -> respx.MockRouter:
    """Outbound HTTP the pipeline makes (GitHub, link checks). Healthy by default."""
    with respx.mock(assert_all_called=False) as router:
        router.head("https://comeback.top/").mock(return_value=httpx.Response(200))
        router.route(host="api.github.com").mock(return_value=httpx.Response(500))
        yield router


async def _client(session: AsyncSession, llm: FakeLLM, record: Record) -> httpx.AsyncClient:
    app = create_app()

    async def session_override() -> AsyncIterator[AsyncSession]:
        yield session

    outbound = httpx.AsyncClient()
    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_llm] = lambda: llm
    app.dependency_overrides[get_record] = lambda: record
    app.dependency_overrides[get_http] = lambda: outbound
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def client(
    ingested: AsyncSession, fake_llm: FakeLLM, test_record: Record, external: respx.MockRouter
) -> AsyncIterator[httpx.AsyncClient]:
    async with await _client(ingested, fake_llm, test_record) as c:
        yield c


@pytest.fixture
async def empty_client(
    session: AsyncSession, fake_llm: FakeLLM, test_record: Record
) -> AsyncIterator[httpx.AsyncClient]:
    async with await _client(session, fake_llm, test_record) as c:
        yield c
