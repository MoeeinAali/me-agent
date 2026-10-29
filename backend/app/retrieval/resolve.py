"""Map a mention in the question ("Comeback", "کامبک", "his project") to record entities.

Exact name/alias match beats trigram similarity, which beats embedding similarity; a generic
mention of a kind ("project", "پروژه") deliberately returns every entity of that kind so the
pipeline asks which one instead of picking.
"""

from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Entity
from app.llm.client import LLM
from app.retrieval.normalize import normalize

TRIGRAM_MIN = 0.45
EMBEDDING_MIN = 0.80

GENERIC_MENTIONS: dict[str, set[str]] = {
    "project": {
        "project",
        "projects",
        "his project",
        "a project",
        "the project",
        "پروژه",
        "پروژه‌اش",
        "پروژه هاش",
        "پروژه‌هاش",
        "پروژه‌ها",
        "پروژش",
    },
    "experience": {"job", "his job", "work", "کار", "شغل", "سابقه کاری"},
    "book": {"book", "books", "کتاب", "کتاب‌ها"},
}


@dataclass(frozen=True)
class Candidate:
    entity_id: str
    kind: str
    label: str
    score: float


def _kind_filter(kind: str | None) -> str:
    return "" if kind is None else "and kind = :kind"


async def resolve(
    session: AsyncSession, llm: LLM, mention: str, kind: str | None
) -> list[Candidate]:
    wanted = normalize(mention)
    if not wanted:
        return []

    query = select(Entity.id, Entity.kind, Entity.name, Entity.aliases)
    if kind is not None:
        query = query.where(Entity.kind == kind)
    entities = (await session.execute(query)).all()

    if kind and wanted in {normalize(m) for m in GENERIC_MENTIONS.get(kind, set())}:
        return [Candidate(e.id, e.kind, e.name, 1.0) for e in entities]

    exact = [
        Candidate(e.id, e.kind, e.name, 1.0)
        for e in entities
        if wanted in {normalize(n) for n in [e.name, *e.aliases]}
    ]
    if exact:
        return exact

    trigram = await session.execute(
        text(f"""
            select id, kind, name, greatest(
                word_similarity(:m, lower(name)),
                coalesce((select max(word_similarity(:m, lower(a))) from unnest(aliases) a), 0)
            ) as score
            from entities where true {_kind_filter(kind)}
            order by score desc limit 5
        """),
        {"m": wanted, "kind": kind},
    )
    best = [
        Candidate(r.id, r.kind, r.name, float(r.score)) for r in trigram if r.score >= TRIGRAM_MIN
    ]
    if best:
        top = best[0].score
        return [c for c in best if top - c.score < 1e-6]

    vector = (await llm.embed([mention]))[0]
    semantic = await session.execute(
        text(f"""
            select id, kind, name, 1 - (name_embedding <=> cast(:v as vector)) as score
            from entities where name_embedding is not null {_kind_filter(kind)}
            order by name_embedding <=> cast(:v as vector) limit 3
        """),
        {"v": str(vector), "kind": kind},
    )
    close = [
        Candidate(r.id, r.kind, r.name, float(r.score))
        for r in semantic
        if r.score >= EMBEDDING_MIN
    ]
    return close[:1]
