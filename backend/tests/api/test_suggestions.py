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


async def test_suggestions_never_show_raw_visitor_text_only_owner_faq(
    ingested: object, test_record: object
) -> None:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.models import TraceRow
    from app.record.schema import Record
    from app.suggestions import STATIC, suggestions

    session: AsyncSession = ingested  # type: ignore[assignment]
    record: Record = test_record  # type: ignore[assignment]
    session.add_all(
        [
            TraceRow(
                id=uuid.uuid4(),
                conversation_id=uuid.uuid4(),
                question="Visitor spam text",
                capability="answer_from_record",
                intent="fact_lookup",
                channel="http",
                language="en",
                latency_ms=1,
                data={},
            )
            for _ in range(10)
        ]
    )
    await session.commit()
    payload = record.model_dump(mode="json")
    payload["faq"] = [
        {
            "id": "gap-1",
            "question": "Is he open to remote work?",
            "answer": "Yes.",
            "added": "2026-10-30",
            "source": "gap:1",
        }
    ]
    with_faq = Record.model_validate(payload)

    result = await suggestions("general", "en", with_faq)
    assert result == [*STATIC["general"]["en"], "Is he open to remote work?"]
    assert "Visitor spam text" not in result
