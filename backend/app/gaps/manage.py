"""The knowledge-gap loop: list what visitors asked that the record could not answer, and turn
an answer into a FAQ entry in ``data/record.json`` that is searchable immediately."""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KnowledgeGap
from app.ingest.ingest import ingest
from app.llm.client import LLM
from app.record.schema import Record


@dataclass
class AnswerResult:
    faq_id: str
    preview: str
    embedded: int = 0


async def list_gaps(session: AsyncSession) -> list[KnowledgeGap]:
    rows = await session.scalars(
        select(KnowledgeGap)
        .where(KnowledgeGap.status == "open")
        .order_by(KnowledgeGap.count.desc(), KnowledgeGap.last_seen.desc())
    )
    return list(rows)


async def _gap(session: AsyncSession, gap_id: int) -> KnowledgeGap:
    gap = await session.get(KnowledgeGap, gap_id)
    if gap is None:
        raise LookupError(f"no knowledge gap with id {gap_id}")
    return gap


def _write_faq(record_path: Path, entry: dict[str, str], dry_run: bool) -> str:
    raw = json.loads(record_path.read_text(encoding="utf-8"))
    raw["faq"] = [f for f in raw.get("faq", []) if f["id"] != entry["id"]] + [entry]
    Record.model_validate(raw)  # never write an invalid record
    if not dry_run:
        text = json.dumps(raw, indent=2, ensure_ascii=False) + "\n"
        record_path.write_text(text, encoding="utf-8")
    return json.dumps(entry, indent=2, ensure_ascii=False)


async def answer_gap(
    session: AsyncSession,
    llm: LLM,
    data_dir: Path,
    gap_id: int,
    answer: str,
    today: str,
    dry_run: bool = False,
) -> AnswerResult:
    gap = await _gap(session, gap_id)
    faq_id = f"gap-{gap.id}"
    entry = {
        "id": faq_id,
        "question": gap.question,
        "answer": answer.strip(),
        "added": today,
        "source": f"gap:{gap.id}",
    }
    preview = await asyncio.to_thread(_write_faq, data_dir / "record.json", entry, dry_run)
    result = AnswerResult(faq_id=faq_id, preview=preview)
    if dry_run:
        return result
    report = await ingest(
        session,
        llm,
        data_dir / "record.json",
        data_dir / "syllabus.json",
        data_dir / "aliases.json",
        only_ids={faq_id},
    )
    gap.status = "resolved"
    gap.resolution_faq_id = faq_id
    await session.commit()
    result.embedded = report.embedded
    return result


async def ignore_gap(session: AsyncSession, gap_id: int) -> None:
    gap = await _gap(session, gap_id)
    gap.status = "ignored"
    await session.commit()
