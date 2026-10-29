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
