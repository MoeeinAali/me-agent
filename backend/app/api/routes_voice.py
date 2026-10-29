"""Ask by voice: speech → text → the same grounded pipeline → optional speech back."""

import asyncio
import base64
import io
import time
from typing import Annotated
from uuid import UUID

import mutagen
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.api.deps import DepsDep
from app.config import get_settings
from app.domain import Audience, ChatRequest, ChatResponse, ToolCall
from app.pipeline.jobfit import job_fit_handler
from app.pipeline.run import run_chat

router = APIRouter(prefix="/v1", tags=["chat"])

AUDIO_TYPES = {
    "audio/webm",
    "audio/ogg",
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
}


def _duration_seconds(data: bytes) -> float | None:
    """Best effort; formats mutagen can't read (e.g. webm) fall back to the byte limit."""
    try:
        parsed = mutagen.File(io.BytesIO(data))
    except Exception:
        return None
    length = getattr(getattr(parsed, "info", None), "length", None)
    return float(length) if length else None


@router.post("/voice", response_model=ChatResponse)
async def voice(
    deps: DepsDep,
    audio: Annotated[UploadFile, File()],
    conversation_id: Annotated[UUID | None, Form()] = None,
    audience: Annotated[Audience, Form()] = "general",
    tts: Annotated[bool, Form()] = False,
) -> ChatResponse:
    settings = get_settings()
    content_type = (audio.content_type or "").split(";")[0].strip().lower()
    if content_type not in AUDIO_TYPES:
        raise HTTPException(422, f"Unsupported audio type: {content_type or 'unknown'}.")
    data = await audio.read(settings.max_audio_bytes + 1)
    if len(data) > settings.max_audio_bytes:
        raise HTTPException(
            422, f"Audio is larger than {settings.max_audio_bytes // 1_000_000} MB."
        )
    duration = await asyncio.to_thread(_duration_seconds, data)
    if duration is not None and duration > settings.max_audio_seconds:
        raise HTTPException(422, f"Audio is longer than {settings.max_audio_seconds} seconds.")

    started = time.monotonic()
    transcript = (await deps.llm.transcribe(data, audio.filename or "audio")).strip()
    stt_call = ToolCall(name="stt", ok=True, latency_ms=int((time.monotonic() - started) * 1000))
    if not transcript:
        raise HTTPException(422, "We couldn't make out any speech in that recording.")

    req = ChatRequest(message=transcript, audience=audience, conversation_id=conversation_id)
    response = await run_chat(req, "voice", deps, job_fit=job_fit_handler())
    calls = [stt_call]
    audio_b64 = None
    if tts:
        started = time.monotonic()
        try:
            audio_b64 = base64.b64encode(await deps.llm.speak(response.answer)).decode()
            calls.append(
                ToolCall(name="tts", ok=True, latency_ms=int((time.monotonic() - started) * 1000))
            )
        except Exception as exc:  # the text answer still stands without speech
            calls.append(
                ToolCall(
                    name="tts",
                    ok=False,
                    latency_ms=int((time.monotonic() - started) * 1000),
                    detail=f"tts_unavailable: {type(exc).__name__}",
                )
            )
    trace = response.trace.model_copy(
        update={"tools_called": [*calls, *response.trace.tools_called]}
    )
    return response.model_copy(
        update={"transcript": transcript, "audio_b64": audio_b64, "trace": trace}
    )
