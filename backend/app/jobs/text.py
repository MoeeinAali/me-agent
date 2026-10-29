"""Job postings the visitor pastes or uploads."""

import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.config import get_settings
from app.jobs.base import JobInputError, JobPosting


def job_from_text(text: str) -> JobPosting:
    text = text.strip()
    limit = get_settings().max_job_chars
    if not text:
        raise JobInputError("The job text is empty.")
    if len(text) > limit:
        raise JobInputError(f"The job text is longer than {limit} characters.")
    return JobPosting(source="pasted", description_text=text)


def job_from_pdf(data: bytes) -> JobPosting:
    limit = get_settings().max_pdf_bytes
    if len(data) > limit:
        raise JobInputError(f"The PDF is larger than {limit // 1_000_000} MB.")
    try:
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except (PdfReadError, ValueError, KeyError) as exc:
        raise JobInputError("We could not read that PDF.") from exc
    posting = job_from_text(text[: get_settings().max_job_chars])
    return posting.model_copy(update={"source": "pdf"})
