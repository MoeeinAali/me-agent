"""Questions the page could not answer, merged by meaning so repeats raise a count."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KnowledgeGap
from app.domain import Lang
from app.llm.client import LLM

MERGE_SIMILARITY = 0.88


async def record_gap(
    session: AsyncSession, llm: LLM, question: str, language: Lang, reason: str
) -> KnowledgeGap:
    vector = (await llm.embed([question]))[0]
    distance = KnowledgeGap.embedding.cosine_distance(vector)
    nearest = (
        await session.execute(
            select(KnowledgeGap, distance)
            .where(KnowledgeGap.status == "open")
            .order_by(distance)
            .limit(1)
        )
    ).first()
    if nearest is not None and 1 - float(nearest[1]) >= MERGE_SIMILARITY:
        gap: KnowledgeGap = nearest[0]
        gap.count += 1
        gap.last_seen = datetime.now(UTC)
    else:
        gap = KnowledgeGap(question=question, language=language, reason=reason, embedding=vector)
        session.add(gap)
    await session.flush()
    return gap
