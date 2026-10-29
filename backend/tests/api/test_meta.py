import httpx

from app.record.schema import Record


async def test_limits_endpoint_matches_record(
    client: httpx.AsyncClient, test_record: Record
) -> None:
    response = await client.get("/v1/limits")
    assert response.status_code == 200
    assert response.json() == test_record.limits.model_dump(mode="json")


async def test_record_endpoint_is_public_view(client: httpx.AsyncClient) -> None:
    body = (await client.get("/v1/record")).json()
    assert "sources" not in body["meta"]
    assert body["projects"][0]["id"] == "comeback"


async def test_healthz(client: httpx.AsyncClient) -> None:
    assert (await client.get("/healthz")).json() == {"ok": True}


async def test_readyz_503_before_ingest(empty_client: httpx.AsyncClient) -> None:
    assert (await empty_client.get("/readyz")).status_code == 503


async def test_readyz_ok_after_ingest(client: httpx.AsyncClient) -> None:
    assert (await client.get("/readyz")).status_code == 200


async def test_request_id_header(client: httpx.AsyncClient) -> None:
    response = await client.get("/healthz", headers={"x-request-id": "abc"})
    assert response.headers["x-request-id"] == "abc"
