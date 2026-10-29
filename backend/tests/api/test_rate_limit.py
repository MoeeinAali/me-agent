import httpx
import pytest
from fastapi import FastAPI

from app.api.main import create_app


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    monkeypatch.setenv("RATE_LIMIT", "2/minute")
    return create_app()


@pytest.fixture
def limited(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_api_routes_are_rate_limited(limited: httpx.AsyncClient) -> None:
    async with limited as client:
        codes = [(await client.get("/v1/limits")).status_code for _ in range(3)]
    assert codes[-1] == 429


async def test_mcp_is_rate_limited(app: FastAPI, limited: httpx.AsyncClient) -> None:
    body = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
    headers = {"accept": "application/json, text/event-stream"}
    async with app.state.mcp.session_manager.run(), limited as client:
        codes = [
            (await client.post("/mcp/", json=body, headers=headers)).status_code for _ in range(3)
        ]
    assert codes[-1] == 429


async def test_health_checks_are_not_limited(limited: httpx.AsyncClient) -> None:
    async with limited as client:
        codes = [(await client.get("/healthz")).status_code for _ in range(5)]
    assert codes == [200] * 5
