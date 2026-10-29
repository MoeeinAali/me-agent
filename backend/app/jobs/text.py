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


MAX_PDF_PAGES = 10


def job_from_pdf(data: bytes) -> JobPosting:
    """Extract a posting from a PDF. CPU-bound: call it from a worker thread in async code.

    Bounded three ways so a small but hostile PDF can't exhaust the server: file size, page count,
    and extracted characters (extraction stops as soon as enough text is collected).
    """
    settings = get_settings()
    if len(data) > settings.max_pdf_bytes:
        raise JobInputError(f"The PDF is larger than {settings.max_pdf_bytes // 1_000_000} MB.")
    try:
        reader = PdfReader(io.BytesIO(data))
        if len(reader.pages) > MAX_PDF_PAGES:
            raise JobInputError(f"The PDF has more than {MAX_PDF_PAGES} pages.")
        parts: list[str] = []
        collected = 0
        for page in reader.pages:
            chunk = page.extract_text() or ""
            parts.append(chunk)
            collected += len(chunk) + 1
            if collected >= settings.max_job_chars:
                break
        text = "\n".join(parts)
    except (PdfReadError, ValueError, KeyError) as exc:
        if isinstance(exc, JobInputError):
            raise
        raise JobInputError("We could not read that PDF.") from exc
    posting = job_from_text(text[: settings.max_job_chars])
    return posting.model_copy(update={"source": "pdf"})
