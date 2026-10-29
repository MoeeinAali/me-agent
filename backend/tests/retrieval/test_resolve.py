from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.fake import FakeLLM
from app.retrieval.resolve import resolve


async def test_resolve_persian_alias(ingested: AsyncSession) -> None:
    candidates = await resolve(ingested, FakeLLM(), "کامبک", "project")
    assert [c.entity_id for c in candidates] == ["project:comeback"]


async def test_resolve_arabic_kaf_variant(ingested: AsyncSession) -> None:
    candidates = await resolve(ingested, FakeLLM(), "كامبك", None)
    assert candidates[0].entity_id == "project:comeback"


async def test_resolve_typo_by_trigram(ingested: AsyncSession) -> None:
    candidates = await resolve(ingested, FakeLLM(), "Kanban bord", "project")
    assert [c.entity_id for c in candidates] == ["project:kanban-board"]


async def test_resolve_ambiguous_project(ingested: AsyncSession) -> None:
    for mention in ("project", "his project", "پروژه"):
        candidates = await resolve(ingested, FakeLLM(), mention, "project")
        assert {c.entity_id for c in candidates} == {"project:comeback", "project:kanban-board"}
        assert all(c.label for c in candidates)


async def test_resolve_unknown_returns_nothing(ingested: AsyncSession) -> None:
    assert await resolve(ingested, FakeLLM(), "Google", "project") == []


async def test_resolve_partial_name_inside_long_name(ingested: AsyncSession) -> None:
    candidates = await resolve(ingested, FakeLLM(), "Kanban", None)
    assert [c.entity_id for c in candidates] == ["project:kanban-board"]


async def test_resolve_word_inside_experience_name(ingested: AsyncSession) -> None:
    candidates = await resolve(ingested, FakeLLM(), "Uranus", None)
    assert [c.entity_id for c in candidates] == ["experience:yektanet-uranus"]
