from collections.abc import AsyncIterator

import httpx


async def test_json_endpoint_rejects_oversized_body_413(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/v1/chat", content=b"x" * 200_000, headers={"content-type": "application/json"}
    )
    assert response.status_code == 413


async def test_upload_over_limit_rejected_before_parsing(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/v1/jobs/fit", files={"file": ("big.pdf", b"0" * 3_000_000, "application/pdf")}
    )
    assert response.status_code == 413


async def test_chunked_body_without_length_is_counted(client: httpx.AsyncClient) -> None:
    async def body() -> AsyncIterator[bytes]:
        for _ in range(10):
            yield b"x" * 50_000

    response = await client.post(
        "/v1/chat", content=body(), headers={"content-type": "application/json"}
    )
    assert response.status_code == 413
