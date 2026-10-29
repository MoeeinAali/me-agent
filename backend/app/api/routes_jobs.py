import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, UploadFile

from app.api.deps import DepsDep
from app.config import get_settings
from app.domain import Audience, ChatRequest, ChatResponse
from app.jobs.base import JobInputError, resolve_job
from app.jobs.text import job_from_pdf
from app.pipeline.jobfit import job_fit_handler
from app.pipeline.run import run_chat

router = APIRouter(prefix="/v1", tags=["jobs"])
DEFAULT_QUESTION = "Does Moeein fit this role?"


@router.post("/jobs/fit", response_model=ChatResponse)
async def job_fit(
    deps: DepsDep,
    url: Annotated[str | None, Form()] = None,
    text: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
    message: Annotated[str, Form()] = DEFAULT_QUESTION,
    audience: Annotated[Audience, Form()] = "general",
    conversation_id: Annotated[UUID | None, Form()] = None,
) -> ChatResponse:
    """Job-fit scorecard for a job link, pasted text, or a PDF (exactly one)."""
    limit = get_settings().max_pdf_bytes
    pdf = await file.read(limit + 1) if file is not None else None
    if pdf is not None and len(pdf) > limit:
        raise JobInputError(f"The PDF is larger than {limit // 1_000_000} MB.")
    if pdf is not None:
        if url or text:
            raise JobInputError("Provide exactly one of: a job link, the job text, or a PDF.")
        posting = await asyncio.to_thread(job_from_pdf, pdf)
    else:
        posting = await resolve_job(url=url, text=text, pdf=None)
    req = ChatRequest(
        message=message,
        audience=audience,
        conversation_id=conversation_id,
        job_text=posting.description_text[: get_settings().max_job_chars],
    )
    return await run_chat(req, "http", deps, job_fit=job_fit_handler(posting))
