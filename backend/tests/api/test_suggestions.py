import httpx


async def test_suggestions_per_audience_fa(client: httpx.AsyncClient) -> None:
    body = (
        await client.get("/v1/suggestions", params={"audience": "professor", "lang": "fa"})
    ).json()
    assert len(body["suggestions"]) >= 4
    assert all(any("؀" <= ch <= "ۿ" for ch in s) for s in body["suggestions"])


async def test_suggestions_rejects_unknown_audience(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1/suggestions", params={"audience": "hacker", "lang": "en"})
    assert response.status_code == 422


async def test_popular_questions_need_distinct_conversations_and_clean_text(
    ingested: object,
) -> None:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.models import TraceRow
    from app.suggestions import STATIC, suggestions

    session: AsyncSession = ingested  # type: ignore[assignment]

    def trace(question: str, conversation: uuid.UUID) -> TraceRow:
        return TraceRow(
            id=uuid.uuid4(),
            conversation_id=conversation,
            question=question,
            capability="answer_from_record",
            intent="fact_lookup",
            channel="http",
            language="en",
            latency_ms=1,
            data={},
        )

    one_chat = uuid.uuid4()
    session.add_all([trace("Spam asked five times in one chat", one_chat) for _ in range(5)])
    session.add_all([trace("Visit https://evil.example now", uuid.uuid4()) for _ in range(4)])
    session.add_all([trace("Does he know Docker?", uuid.uuid4()) for _ in range(3)])
    await session.commit()

    result = await suggestions("general", "en", session)
    assert result == [*STATIC["general"]["en"], "Does he know Docker?"]
