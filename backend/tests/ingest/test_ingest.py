import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk, Entity
from app.ingest.ingest import ingest
from app.llm.fake import FakeLLM
from tests.record.factories import minimal_record


def write(tmp: Path, record: dict[str, object]) -> tuple[Path, Path, Path]:
    (tmp / "record.json").write_text(json.dumps(record), encoding="utf-8")
    (tmp / "syllabus.json").write_text("[]", encoding="utf-8")
    (tmp / "aliases.json").write_text('{"comeback": ["کامبک"]}', encoding="utf-8")
    return tmp / "record.json", tmp / "syllabus.json", tmp / "aliases.json"


async def test_ingest_idempotent(session: AsyncSession, tmp_path: Path) -> None:
    payload = minimal_record()
    payload["books"] = [
        {"id": "clean-code", "title": "Clean Code", "author": "R. Martin", "status": "read"}
    ]
    llm = FakeLLM()

    first = await ingest(session, llm, *write(tmp_path, payload))
    assert first.embedded > 0 and first.added > 0

    second = await ingest(session, llm, *write(tmp_path, payload))
    assert (second.embedded, second.added, second.updated, second.deleted) == (0, 0, 0, 0)

    payload["projects"][0]["summary"] = "A Persian sports PWA with live chat."
    third = await ingest(session, llm, *write(tmp_path, payload))
    assert third.embedded == 1
    assert third.updated == 1

    payload["books"] = []
    fourth = await ingest(session, llm, *write(tmp_path, payload))
    assert fourth.deleted >= 1
    assert await session.scalar(select(Entity).where(Entity.id == "book:clean-code")) is None
    total = await session.scalar(select(func.count()).select_from(Chunk))
    assert total and total > 0


async def test_ingest_only_ids_touches_just_that_entity(
    session: AsyncSession, tmp_path: Path
) -> None:
    payload = minimal_record()
    llm = FakeLLM()
    await ingest(session, llm, *write(tmp_path, payload))
    payload["projects"][0]["summary"] = "Changed."
    payload["person"]["headline"] = "Changed too."
    report = await ingest(session, llm, *write(tmp_path, payload), only_ids={"comeback"})
    assert report.embedded == 1
    person = await session.scalar(select(Chunk).where(Chunk.path == "person.headline"))
    assert person is not None and "Changed too." not in person.text
