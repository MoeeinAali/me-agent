"""Hybrid retrieval: vector similarity + trigram + full-text, fused with Reciprocal Rank Fusion.

Vectors find paraphrases ("real-time systems" → WebSocket chat); lexical search finds exact
technology names ("Bazel", "Zustand") that embeddings blur.
"""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.client import LLM
from app.retrieval.normalize import normalize

CANDIDATES_PER_RETRIEVER = 20
RRF_K = 60


@dataclass(frozen=True)
class Hit:
    chunk_id: str
    entity_id: str
    kind: str
    path: str
    text: str
    score: float


def rrf(rankings: list[list[str]], k: int = RRF_K) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


_KIND_FILTER = "(cast(:kinds as text[]) is null or e.kind = any(cast(:kinds as text[])))"

_VECTOR_SQL = text(f"""
    select c.id from chunks c join entities e on e.id = c.entity_id
    where {_KIND_FILTER}
    order by c.embedding <=> cast(:vector as vector) limit :limit
""")

_TRIGRAM_SQL = text(f"""
    select c.id from chunks c join entities e on e.id = c.entity_id
    where {_KIND_FILTER} and word_similarity(:query, lower(c.text)) > 0.3
    order by word_similarity(:query, lower(c.text)) desc limit :limit
""")

_FULLTEXT_SQL = text(f"""
    select c.id from chunks c join entities e on e.id = c.entity_id
    where {_KIND_FILTER} and c.tsv @@ plainto_tsquery('simple', :query)
    order by ts_rank(c.tsv, plainto_tsquery('simple', :query)) desc limit :limit
""")

_ROWS_SQL = text("""
    select c.id, c.entity_id, e.kind, c.path, c.text
    from chunks c join entities e on e.id = c.entity_id where c.id = any(:ids)
""")


async def search(
    session: AsyncSession,
    llm: LLM,
    query: str,
    kinds: set[str] | None = None,
    top_k: int = 8,
    boost_kinds: dict[str, float] | None = None,
) -> list[Hit]:
    vector = (await llm.embed([query]))[0]
    params = {
        "kinds": sorted(kinds) if kinds else None,
        "limit": CANDIDATES_PER_RETRIEVER,
        "query": normalize(query),
    }
    rankings = [
        list((await session.scalars(_VECTOR_SQL, {**params, "vector": str(vector)})).all()),
        list((await session.scalars(_TRIGRAM_SQL, params)).all()),
        list((await session.scalars(_FULLTEXT_SQL, params)).all()),
    ]
    fused = rrf(rankings)
    if not fused:
        return []
    rows = {r.id: r for r in await session.execute(_ROWS_SQL, {"ids": [i for i, _ in fused]})}
    boosts = boost_kinds or {}
    hits = [
        Hit(
            cid,
            rows[cid].entity_id,
            rows[cid].kind,
            rows[cid].path,
            rows[cid].text,
            score * boosts.get(rows[cid].kind, 1.0),
        )
        for cid, score in fused
        if cid in rows
    ]
    return sorted(hits, key=lambda h: -h.score)[:top_k]


async def read_fields(
    session: AsyncSession, entity_id: str, fields: list[str] | None = None
) -> list[tuple[str, str]]:
    """Structured read: an entity's chunks by path, optionally only the given top-level fields."""
    rows = await session.execute(
        text("select path, text from chunks where entity_id = :id order by path"),
        {"id": entity_id},
    )
    out = []
    for path, value in rows:
        field = path.split("].", 1)[-1] if "]." in path else path.split(".", 1)[-1]
        if fields is None or field.split("[", 1)[0] in fields:
            out.append((path, value))
    return out
