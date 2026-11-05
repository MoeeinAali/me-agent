"""Server-sent events: the live trace (stages, evidence) while the pipeline runs, then the
verified answer as tokens, then the full response.

Tokens are the *verified* answer cut into pieces after verification — raw model output is never
streamed, so unsupported text can't flash on screen before the verifier removes it.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated, Any

import httpx
import openai
import structlog
from fastapi import APIRouter, Depends
from sse_starlette import EventSourceResponse, ServerSentEvent

from app.api.deps import SessionFactory, build_deps, get_http, get_record, get_session_factory
from app.config import Settings, get_settings
from app.domain import ChatRequest
from app.jobs.base import JobFetchError, JobInputError
from app.llm.client import LLM, LLM_UNAVAILABLE, get_llm
from app.pipeline.jobfit import job_fit_handler
from app.pipeline.run import run_chat
from app.record.schema import Record

router = APIRouter(prefix="/v1", tags=["chat"])
log = structlog.get_logger()
TOKEN_CHARS = 20


def chunk_text(text: str, size: int = TOKEN_CHARS) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]


def _event(name: str, data: dict[str, Any]) -> ServerSentEvent:
    return ServerSentEvent(event=name, data=json.dumps(data, ensure_ascii=False))


@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    sessions: Annotated[SessionFactory, Depends(get_session_factory)],
    llm: Annotated[LLM, Depends(get_llm)],
    record: Annotated[Record, Depends(get_record)],
    settings: Annotated[Settings, Depends(get_settings)],
    http: Annotated[httpx.AsyncClient, Depends(get_http)],
) -> EventSourceResponse:
    queue: asyncio.Queue[ServerSentEvent | None] = asyncio.Queue()

    async def emit(name: str, data: dict[str, Any]) -> None:
        await queue.put(_event(name, data))

    async def run() -> None:
        try:
            async with sessions() as session:
                deps = build_deps(session, llm, record, settings, http)
                response = await run_chat(
                    req, "sse", deps, on_event=emit, job_fit=job_fit_handler()
                )
            for piece in chunk_text(response.answer):
                await emit("token", {"text": piece})
            await emit("final", response.model_dump(mode="json"))
        except (JobInputError, JobFetchError) as exc:
            await emit("error", {"message": str(exc)})
        except openai.APIError as exc:
            log.error("llm_unavailable", error=type(exc).__name__, detail=str(exc)[:300])
            await emit("error", {"message": LLM_UNAVAILABLE})
        except Exception:
            log.exception("stream_failed")
            await emit("error", {"message": "Something went wrong while answering. Please retry."})
        finally:
            await queue.put(None)

    async def events() -> AsyncIterator[ServerSentEvent]:
        task = asyncio.create_task(run())
        try:
            while (item := await queue.get()) is not None:
                yield item
        finally:
            if not task.done():
                task.cancel()

    return EventSourceResponse(events(), ping=15)
