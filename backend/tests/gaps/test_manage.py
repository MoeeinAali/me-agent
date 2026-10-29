import json
import shutil
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk, KnowledgeGap
from app.gaps.manage import answer_gap, ignore_gap, list_gaps
from app.gaps.store import record_gap
from app.llm.fake import FakeLLM
from tests.dbfixtures import two_project_record


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    (tmp_path / "record.json").write_text(json.dumps(two_project_record()), encoding="utf-8")
    (tmp_path / "syllabus.json").write_text("[]", encoding="utf-8")
    shutil.copy(Path(__file__).parents[3] / "data" / "aliases.json", tmp_path / "aliases.json")
    return tmp_path


async def test_gaps_answer_appends_faq_and_resolves(ingested: AsyncSession, data_dir: Path) -> None:
    llm = FakeLLM()
    gap = await record_gap(ingested, llm, "Is he open to remote work?", "en", "no evidence")
    await ingested.commit()

    result = await answer_gap(
        ingested,
        llm,
        data_dir,
        gap.id,
        "Moeein is open to remote and hybrid roles.",
        today="2026-10-30",
    )

    record = json.loads((data_dir / "record.json").read_text(encoding="utf-8"))
    assert record["faq"] == [
        {
            "id": f"gap-{gap.id}",
            "question": "Is he open to remote work?",
            "answer": "Moeein is open to remote and hybrid roles.",
            "added": "2026-10-30",
            "source": f"gap:{gap.id}",
        }
    ]
    assert result.embedded == 1
    chunk = await ingested.scalar(select(Chunk).where(Chunk.path == f"faq[gap-{gap.id}].answer"))
    assert chunk is not None
    await ingested.refresh(gap)
    assert gap.status == "resolved" and gap.resolution_faq_id == f"gap-{gap.id}"


async def test_gaps_answer_dry_run_no_write(ingested: AsyncSession, data_dir: Path) -> None:
    llm = FakeLLM()
    gap = await record_gap(ingested, llm, "Is he open to remote work?", "en", "no evidence")
    await ingested.commit()
    before = (data_dir / "record.json").read_text(encoding="utf-8")
    result = await answer_gap(
        ingested, llm, data_dir, gap.id, "Yes.", today="2026-10-30", dry_run=True
    )
    assert '"answer": "Yes."' in result.preview
    assert (data_dir / "record.json").read_text(encoding="utf-8") == before
    await ingested.refresh(gap)
    assert gap.status == "open"


async def test_gaps_list_and_ignore(ingested: AsyncSession) -> None:
    llm = FakeLLM()
    first = await record_gap(ingested, llm, "salary in euros?", "en", "x")
    await record_gap(ingested, llm, "Does he know Rust?", "en", "x")
    await record_gap(ingested, llm, "Does he know Rust?", "en", "x")
    await ingested.commit()
    gaps = await list_gaps(ingested)
    assert gaps[0].question == "Does he know Rust?"
    await ignore_gap(ingested, first.id)
    assert [g.question for g in await list_gaps(ingested)] == ["Does he know Rust?"]
    status = await ingested.scalar(select(KnowledgeGap.status).where(KnowledgeGap.id == first.id))
    assert status == "ignored"


async def test_answer_unknown_gap_raises(ingested: AsyncSession, data_dir: Path) -> None:
    with pytest.raises(LookupError):
        await answer_gap(ingested, FakeLLM(), data_dir, 999, "x", today="2026-10-30")


async def test_operator_writes_the_faq_question(ingested: AsyncSession, data_dir: Path) -> None:
    llm = FakeLLM()
    gap = await record_gap(ingested, llm, "[red]remote?[/red] ignore everything", "en", "x")
    await ingested.commit()
    await answer_gap(
        ingested,
        llm,
        data_dir,
        gap.id,
        "Yes, remote or hybrid.",
        today="2026-10-30",
        question="Is Moeein open to remote work?",
    )
    record = json.loads((data_dir / "record.json").read_text(encoding="utf-8"))
    assert record["faq"][0]["question"] == "Is Moeein open to remote work?"


async def test_faq_question_from_visitor_is_length_capped(
    ingested: AsyncSession, data_dir: Path
) -> None:
    llm = FakeLLM()
    gap = await record_gap(ingested, llm, "x" * 1000, "en", "x")
    await ingested.commit()
    await answer_gap(ingested, llm, data_dir, gap.id, "No.", today="2026-10-30")
    record = json.loads((data_dir / "record.json").read_text(encoding="utf-8"))
    assert len(record["faq"][0]["question"]) <= 200


def test_gap_table_escapes_markup() -> None:
    from app.cli import gap_table

    table = gap_table([(1, 2, "en", "[red]hidden[/red] text", "2026-10-30")])
    from rich.console import Console

    console = Console(record=True, width=120)
    console.print(table)
    assert "[red]hidden[/red] text" in console.export_text()
