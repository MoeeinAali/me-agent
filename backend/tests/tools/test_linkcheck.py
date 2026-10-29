import httpx
import respx

from app.tools.cache import MemoryCache
from app.tools.linkcheck import LinkChecker


@respx.mock
async def test_check_link_up_down() -> None:
    respx.head("https://comeback.top/").mock(return_value=httpx.Response(200))
    respx.head("https://dead.example/").mock(return_value=httpx.Response(405))
    respx.get("https://dead.example/").mock(return_value=httpx.Response(503))
    async with httpx.AsyncClient() as client:
        checker = LinkChecker(client, MemoryCache())
        up = await checker.check("https://comeback.top/", "projects[comeback].links.live")
        down = await checker.check("https://dead.example/", "projects[x].links.live")
    assert up.ok and up.evidence[0].proof.status == "up"
    assert up.evidence[0].source == "link_check"
    assert up.evidence[0].proof.checked_at is not None
    assert down.ok and down.evidence[0].proof.status == "down"
    assert "HTTP 503" in down.evidence[0].value


@respx.mock
async def test_check_link_timeout_is_down_not_error() -> None:
    respx.head("https://slow.example/").mock(side_effect=httpx.ConnectTimeout("t"))
    respx.get("https://slow.example/").mock(side_effect=httpx.ConnectTimeout("t"))
    async with httpx.AsyncClient() as client:
        result = await LinkChecker(client, MemoryCache()).check("https://slow.example/", "p")
    assert result.evidence[0].proof.status == "down"
