from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.fake import FakeLLM
from app.retrieval.hybrid import read_fields, search


async def test_lexical_finds_bazel(ingested: AsyncSession) -> None:
    hits = await search(ingested, FakeLLM(), "Bazel", top_k=3)
    assert any(h.path == "projects[comeback].tech" for h in hits)


async def test_search_filters_kinds(ingested: AsyncSession) -> None:
    hits = await search(ingested, FakeLLM(), "Clean Code", kinds={"book"})
    assert hits and all(h.entity_id.startswith("book:") for h in hits)


async def test_boost_reorders(ingested: AsyncSession) -> None:
    plain = await search(ingested, FakeLLM(), "board", top_k=10)
    boosted = await search(ingested, FakeLLM(), "board", top_k=10, boost_kinds={"person": 50.0})
    assert plain[0].entity_id == "project:kanban-board"
    assert boosted[0].entity_id == "person:moeein"


async def test_read_fields(ingested: AsyncSession) -> None:
    fields = dict(await read_fields(ingested, "project:comeback"))
    assert fields["projects[comeback].summary"] == "Comeback — A Persian sports PWA."
    only = await read_fields(ingested, "project:comeback", ["tech"])
    assert [path for path, _ in only] == ["projects[comeback].tech"]
