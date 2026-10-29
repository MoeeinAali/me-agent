"""One client for every model call: chat (structured), embeddings, speech-to-text, text-to-speech.

GapGPT is OpenAI-compatible, so any provider with the same API works by changing the base URL.
"""

import copy
import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Protocol, TypeVar

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.config import Settings, get_settings

T = TypeVar("T", bound=BaseModel)

EMBED_BATCH = 96


@dataclass(frozen=True)
class Usage:
    tokens_in: int = 0
    tokens_out: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(self.tokens_in + other.tokens_in, self.tokens_out + other.tokens_out)


class LLM(Protocol):
    async def structured(
        self, model: str, system: str, messages: list[dict[str, str]], schema: type[T]
    ) -> tuple[T, Usage]: ...

    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    async def transcribe(self, audio: bytes, filename: str) -> str: ...

    async def speak(self, text: str) -> bytes: ...


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    """The model's JSON Schema in the shape OpenAI's ``strict`` structured output requires:
    every object closed (``additionalProperties: false``) and every property required."""
    schema = copy.deepcopy(model.model_json_schema())

    def close(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"])
            node.pop("default", None)
            for value in node.values():
                close(value)
        elif isinstance(node, list):
            for value in node:
                close(value)

    close(schema)
    return schema


class OpenAICompatLLM:
    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key.get_secret_value(),
            timeout=settings.llm_timeout_seconds,
            max_retries=2,
            http_client=http_client,
        )

    async def structured(
        self, model: str, system: str, messages: list[dict[str, str]], schema: type[T]
    ) -> tuple[T, Usage]:
        conversation: list[dict[str, str]] = [{"role": "system", "content": system}, *messages]
        response_format: Any = {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "strict": True,
                "schema": strict_schema(schema),
            },
        }
        usage = Usage()
        last_error = ""
        for _attempt in range(2):
            response = await self._client.chat.completions.create(
                model=model,
                messages=conversation,  # type: ignore[arg-type]
                response_format=response_format,
                temperature=0,
            )
            if response.usage:
                usage += Usage(response.usage.prompt_tokens, response.usage.completion_tokens)
            content = response.choices[0].message.content or ""
            try:
                return schema.model_validate_json(content), usage
            except ValidationError as exc:
                last_error = str(exc)
                conversation = [
                    *conversation,
                    {"role": "assistant", "content": content},
                    {
                        "role": "user",
                        "content": "Your reply did not match the schema. Errors:\n"
                        f"{last_error}\nReply again with only valid JSON for the schema.",
                    },
                ]
        raise ValueError(f"model output did not match the {schema.__name__} schema: {last_error}")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), EMBED_BATCH):
            batch = texts[start : start + EMBED_BATCH]
            response = await self._client.embeddings.create(
                model=self._settings.llm_model_embed, input=batch
            )
            vectors += [item.embedding for item in sorted(response.data, key=lambda d: d.index)]
        return vectors

    async def transcribe(self, audio: bytes, filename: str) -> str:
        response = await self._client.audio.transcriptions.create(
            model=self._settings.llm_model_stt, file=(filename, audio)
        )
        return response.text.strip()

    async def speak(self, text: str) -> bytes:
        response = await self._client.audio.speech.create(
            model=self._settings.llm_model_tts, voice="alloy", input=text, response_format="mp3"
        )
        return response.content


@lru_cache
def _default_llm() -> OpenAICompatLLM:
    return OpenAICompatLLM(get_settings())


def get_llm() -> LLM:
    """FastAPI dependency; tests override it with :class:`app.llm.fake.FakeLLM`."""
    return _default_llm()


async def _smoke() -> None:
    llm = _default_llm()

    class Hello(BaseModel):
        answer: str

    out, usage = await llm.structured(
        get_settings().llm_model_understand,
        "Reply in Persian.",
        [{"role": "user", "content": "Say hello."}],
        Hello,
    )
    vector = (await llm.embed(["سلام"]))[0]
    print(
        json.dumps(
            {"answer": out.answer, "usage": usage.__dict__, "dim": len(vector)}, ensure_ascii=False
        )
    )


if __name__ == "__main__":
    import asyncio
    import sys

    if "--smoke" in sys.argv:
        asyncio.run(_smoke())
