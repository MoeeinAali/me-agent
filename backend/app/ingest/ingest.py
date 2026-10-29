"""Load ``record.json`` + ``syllabus.json`` into Postgres, embedding only what changed."""

import asyncio
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk, Entity
from app.ingest.chunker import EntityDraft, explode
from app.llm.client import LLM
from app.record.loader import load_record, load_syllabus


@dataclass
class IngestReport:
    added: int = 0
    updated: int = 0
    deleted: int = 0
    embedded: int = 0


def _hash(*parts: object) -> str:
    raw = json.dumps(parts, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def _entity_hash(draft: EntityDraft) -> str:
    return _hash(draft.name, draft.aliases, draft.data, draft.path)


def _load_drafts(
    record_path: Path, syllabus_path: Path, aliases_path: Path | None
) -> list[EntityDraft]:
    aliases = (
        json.loads(aliases_path.read_text(encoding="utf-8"))
        if aliases_path and aliases_path.exists()
        else {}
    )
    return explode(load_record(record_path), load_syllabus(syllabus_path), aliases)


async def ingest(
    session: AsyncSession,
    llm: LLM,
    record_path: Path,
    syllabus_path: Path,
    aliases_path: Path | None = None,
    only_ids: set[str] | None = None,
) -> IngestReport:
    """Idempotent: unchanged chunks are skipped, removed ones deleted.

    ``only_ids`` (record ids) limits the run to those entities and skips deletions; it is how
    ``me-agent gaps answer`` makes a single new FAQ searchable in one embedding call.
    """
    drafts = await asyncio.to_thread(_load_drafts, record_path, syllabus_path, aliases_path)
    if only_ids is not None:
        drafts = [d for d in drafts if d.record_id in only_ids]

    report = IngestReport()
    existing_entities = {e.id: e for e in (await session.scalars(select(Entity))).all()}
    existing_chunks = {c.id: c.content_hash for c in (await session.scalars(select(Chunk))).all()}

    changed_entities: list[EntityDraft] = []
    for draft in drafts:
        entity_hash = _entity_hash(draft)
        current = existing_entities.get(draft.id)
        if current is None:
            report.added += 1
            changed_entities.append(draft)
        elif current.content_hash != entity_hash:
            report.updated += 1
            changed_entities.append(draft)

    new_chunks = [
        (draft, chunk)
        for draft in drafts
        for chunk in draft.chunks
        if existing_chunks.get(chunk.path) != _hash(chunk.text, chunk.lang)
    ]
    texts = [chunk.text for _, chunk in new_chunks]
    names = [" / ".join([d.name, *d.aliases]) for d in changed_entities]
    vectors = await llm.embed(texts + names) if texts or names else []
    chunk_vectors, name_vectors = vectors[: len(texts)], vectors[len(texts) :]
    report.embedded = len(texts)

    for draft, vector in zip(changed_entities, name_vectors, strict=True):
        await session.merge(
            Entity(
                id=draft.id,
                kind=draft.kind,
                path=draft.path,
                name=draft.name,
                aliases=draft.aliases,
                data=draft.data,
                content_hash=_entity_hash(draft),
                name_embedding=vector,
            )
        )
    await session.flush()

    for (draft, chunk), vector in zip(new_chunks, chunk_vectors, strict=True):
        await session.merge(
            Chunk(
                id=chunk.path,
                entity_id=draft.id,
                path=chunk.path,
                text=chunk.text,
                lang=chunk.lang,
                content_hash=_hash(chunk.text, chunk.lang),
                embedding=vector,
            )
        )

    if only_ids is None:
        wanted_entities = {d.id for d in drafts}
        wanted_chunks = {c.path for d in drafts for c in d.chunks}
        stale_entities = set(existing_entities) - wanted_entities
        stale_chunks = set(existing_chunks) - wanted_chunks
        if stale_chunks:
            await session.execute(delete(Chunk).where(Chunk.id.in_(stale_chunks)))
        if stale_entities:
            await session.execute(delete(Entity).where(Entity.id.in_(stale_entities)))
        report.deleted = len(stale_entities)

    await session.commit()
    return report
