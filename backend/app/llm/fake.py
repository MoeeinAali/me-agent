"""A deterministic stand-in for the model, for tests.

Structured calls return scripted outputs per schema, in order. Embeddings are hashed
bag-of-words vectors: identical text → identical vector, and texts sharing words are close, which
is enough to exercise retrieval and gap merging without a network.
"""

import hashlib
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, TypeVar

from pydantic import BaseModel

from app.llm.client import Usage

T = TypeVar("T", bound=BaseModel)


@dataclass
class FakeCall:
    model: str
    system: str
    messages: list[dict[str, str]]
    schema: type[BaseModel]


@dataclass
class FakeLLM:
    scripted: dict[type[BaseModel], list[Any]] = field(default_factory=dict)
    dim: int = 1536
    transcript: str = ""
    speech: bytes | Exception = b"ID3fake"
    calls: list[FakeCall] = field(default_factory=list)
    _queues: dict[type[BaseModel], list[Any]] = field(default_factory=lambda: defaultdict(list))
    _failures: list[Exception] = field(default_factory=list)

    def __post_init__(self) -> None:
        for schema, outputs in self.scripted.items():
            self._queues[schema].extend(outputs)

    def script(self, *outputs: BaseModel | Exception) -> None:
        """Queue outputs per schema; an exception is raised by the next structured call."""
        for output in outputs:
            if isinstance(output, Exception):
                self._failures.append(output)
            else:
                self._queues[type(output)].append(output)

    async def structured(
        self, model: str, system: str, messages: list[dict[str, str]], schema: type[T]
    ) -> tuple[T, Usage]:
        self.calls.append(FakeCall(model, system, messages, schema))
        if self._failures:
            raise self._failures.pop(0)
        queue = self._queues.get(schema)
        assert queue, f"no scripted {schema.__name__} left"
        output = queue.pop(0)
        if isinstance(output, Exception):
            raise output
        return schema.model_validate(output.model_dump()), Usage(10, 5)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    async def transcribe(self, audio: bytes, filename: str) -> str:
        return self.transcript

    async def speak(self, text: str) -> bytes:
        if isinstance(self.speech, Exception):
            raise self.speech
        return self.speech

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for token in re.findall(r"\w+", text.lower()) or [text]:
            digest = hashlib.sha256(token.encode()).digest()
            vector[int.from_bytes(digest[:4], "big") % self.dim] += 1.0
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norm for x in vector]
