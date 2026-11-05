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


async def test_rate_limit_can_key_on_a_cdn_client_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RATE_LIMIT", "2/minute")
    monkeypatch.setenv("RATE_LIMIT_CLIENT_HEADER", "cf-connecting-ip")
    monkeypatch.setenv("RATE_LIMIT_TRUSTED_PROXIES", '["127.0.0.0/8"]')  # the test client's address
    app = create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:

        async def get(ip: str) -> int:
            return (await client.get("/v1/limits", headers={"cf-connecting-ip": ip})).status_code

        codes_a = [await get("1.1.1.1") for _ in range(3)]
        assert codes_a[-1] == 429
        assert await get("2.2.2.2") == 200  # another visitor behind the same edge


async def test_client_header_from_an_untrusted_sender_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A visitor who reaches the API directly can't dodge the limit by inventing the header."""
    monkeypatch.setenv("RATE_LIMIT", "2/minute")
    monkeypatch.setenv("RATE_LIMIT_CLIENT_HEADER", "cf-connecting-ip")
    monkeypatch.setenv("RATE_LIMIT_TRUSTED_PROXIES", '["173.245.48.0/20"]')
    app = create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        codes = [
            (await client.get("/v1/limits", headers={"cf-connecting-ip": f"9.9.9.{i}"})).status_code
            for i in range(3)
        ]
    assert codes[-1] == 429
