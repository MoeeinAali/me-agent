import json
import math
from collections.abc import Callable

import httpx2 as httpx
import pytest
from pydantic import BaseModel

from app.config import get_settings
from app.llm.client import OpenAICompatLLM, strict_schema
from app.llm.fake import FakeLLM

BASE = "https://api.gapgpt.app/v1"


class Answer(BaseModel):
    answer: str
    note: str | None = None


def completion(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "c1",
            "object": "chat.completion",
            "created": 0,
            "model": "gpt-4.1-mini",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
            "usage": {"prompt_tokens": 11, "completion_tokens": 3, "total_tokens": 14},
        },
    )


class Recorder:
    """An httpx transport that answers from a handler and remembers each request."""

    def __init__(self, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        self.requests: list[httpx.Request] = []
        self._handler = handler

    def client(self) -> httpx.AsyncClient:
        def handle(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return self._handler(request)

        return httpx.AsyncClient(transport=httpx.MockTransport(handle))


def sequence(*responses: httpx.Response) -> Callable[[httpx.Request], httpx.Response]:
    pending = list(responses)
    return lambda _request: pending.pop(0) if len(pending) > 1 else pending[0]


def test_strict_schema_requires_every_property() -> None:
    schema = strict_schema(Answer)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"answer", "note"}


async def test_structured_parses_json_schema() -> None:
    rec = Recorder(sequence(completion(json.dumps({"answer": "سلام", "note": None}))))
    llm = OpenAICompatLLM(get_settings(), rec.client())
    out, usage = await llm.structured(
        "gpt-4.1-mini", "sys", [{"role": "user", "content": "hi"}], Answer
    )
    assert out.answer == "سلام"
    assert (usage.tokens_in, usage.tokens_out) == (11, 3)
    assert str(rec.requests[0].url) == f"{BASE}/chat/completions"
    sent = json.loads(rec.requests[0].content)
    assert sent["response_format"]["type"] == "json_schema"
    assert sent["response_format"]["json_schema"]["strict"] is True
    assert sent["messages"][0] == {"role": "system", "content": "sys"}


async def test_structured_retries_once_on_invalid_json() -> None:
    rec = Recorder(
        sequence(completion("not json"), completion(json.dumps({"answer": "ok", "note": None})))
    )
    llm = OpenAICompatLLM(get_settings(), rec.client())
    out, usage = await llm.structured("m", "sys", [{"role": "user", "content": "hi"}], Answer)
    assert out.answer == "ok"
    assert len(rec.requests) == 2
    assert usage.tokens_in == 22
    retry_messages = json.loads(rec.requests[1].content)["messages"]
    assert "did not match the schema" in retry_messages[-1]["content"]


async def test_structured_gives_up_after_one_retry() -> None:
    rec = Recorder(sequence(completion("still not json")))
    llm = OpenAICompatLLM(get_settings(), rec.client())
    with pytest.raises(ValueError, match="schema"):
        await llm.structured("m", "sys", [{"role": "user", "content": "hi"}], Answer)


async def test_embed_batches() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        inputs = json.loads(request.content)["input"]
        data = [
            {"object": "embedding", "index": i, "embedding": [0.1] * 4} for i in range(len(inputs))
        ]
        return httpx.Response(
            200,
            json={
                "object": "list",
                "data": data,
                "model": "m",
                "usage": {"prompt_tokens": 1, "total_tokens": 1},
            },
        )

    rec = Recorder(respond)
    vectors = await OpenAICompatLLM(get_settings(), rec.client()).embed(
        [f"t{i}" for i in range(200)]
    )
    assert len(vectors) == 200
    assert len(rec.requests) == 3


async def test_fake_embed_deterministic_and_similarity_aware() -> None:
    fake = FakeLLM()
    a, b, c = await fake.embed(["Comeback sports PWA", "Comeback sports PWA", "Kafka queue"])
    assert a == b
    assert len(a) == 1536
    assert math.isclose(sum(x * x for x in a), 1.0, rel_tol=1e-6)
    assert sum(x * y for x, y in zip(a, c, strict=True)) < 0.5


async def test_fake_structured_returns_scripted_in_order() -> None:
    fake = FakeLLM({Answer: [Answer(answer="one"), Answer(answer="two")]})
    first, _ = await fake.structured("m", "s", [], Answer)
    second, _ = await fake.structured("m", "s", [], Answer)
    assert (first.answer, second.answer) == ("one", "two")
    assert fake.calls[0].schema is Answer
    with pytest.raises(AssertionError, match="no scripted Answer"):
        await fake.structured("m", "s", [], Answer)


async def test_structured_accepts_code_fenced_json() -> None:
    fenced = '```json\n{"answer": "ok", "note": null}\n```'
    rec = Recorder(sequence(completion(fenced)))
    out, _ = await OpenAICompatLLM(get_settings(), rec.client()).structured(
        "claude-sonnet-4-6", "sys", [{"role": "user", "content": "hi"}], Answer
    )
    assert out.answer == "ok"
    assert len(rec.requests) == 1
