import json

import httpx
import httpx2
import openai

from app.domain import Claim
from app.llm.client import LLM_UNAVAILABLE
from app.llm.fake import FakeLLM
from app.pipeline.generate import GenerationOut
from app.pipeline.understand import UnderstandOut


def parse_sse(raw: str) -> list[tuple[str, dict]]:  # type: ignore[type-arg]
    events = []
    for block in raw.replace("\r\n", "\n").split("\n\n"):
        name, data = "message", []
        for line in block.split("\n"):
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].strip())
        if data:
            events.append((name, json.loads("\n".join(data))))
    return events


async def stream(client: httpx.AsyncClient, message: str) -> list[tuple[str, dict]]:  # type: ignore[type-arg]
    async with client.stream("POST", "/v1/chat/stream", json={"message": message}) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        return parse_sse("".join([chunk async for chunk in response.aiter_text()]))


async def test_stream_event_order(client: httpx.AsyncClient, fake_llm: FakeLLM) -> None:
    fake_llm.script(
        UnderstandOut(
            intent="project_summary",
            language="en",
            entities=["Comeback"],
            asks_for="Comeback summary",
            wants_action=None,
        ),
        GenerationOut(
            claims=[Claim(text="Comeback is a Persian sports PWA serving fans.", evidence=["E1"])],
            missing=[],
        ),
    )
    events = await stream(client, "Summarize Comeback")
    names = [name for name, _ in events]
    started = [d["name"] for n, d in events if n == "stage" and d["status"] == "start"]
    assert started == ["understand", "resolve", "policy", "evidence", "generate", "verify"]
    assert "evidence" in names
    assert names[-1] == "final"
    tokens = "".join(d["text"] for n, d in events if n == "token")
    assert tokens == events[-1][1]["answer"]
    assert names.index("token") > max(i for i, n in enumerate(names) if n == "stage")


async def test_stream_error_event_on_llm_failure(
    client: httpx.AsyncClient, fake_llm: FakeLLM
) -> None:
    fake_llm.script(RuntimeError("upstream exploded with secret details"))
    events = await stream(client, "Summarize Comeback")
    assert events[-1][0] == "error"
    assert "secret" not in events[-1][1]["message"]


def provider_error() -> openai.APIError:
    request = httpx2.Request("POST", "https://llm.example/v1/chat/completions")
    return openai.PermissionDeniedError(
        "request failed (secret request id)",
        response=httpx2.Response(403, request=request),
        body=None,
    )


async def test_stream_says_the_ai_service_is_down(
    client: httpx.AsyncClient, fake_llm: FakeLLM
) -> None:
    fake_llm.script(provider_error())
    events = await stream(client, "Summarize Comeback")
    assert events[-1] == ("error", {"message": LLM_UNAVAILABLE})


async def test_chat_returns_503_when_the_ai_service_is_down(
    client: httpx.AsyncClient, fake_llm: FakeLLM
) -> None:
    fake_llm.script(provider_error())
    response = await client.post("/v1/chat", json={"message": "Summarize Comeback"})
    assert response.status_code == 503
    assert response.json() == {"detail": LLM_UNAVAILABLE}
