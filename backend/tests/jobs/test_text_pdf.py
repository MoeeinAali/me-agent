import pytest

from app.jobs.base import JobInputError, resolve_job
from app.jobs.text import job_from_pdf, job_from_text
from tests.jobs.pdf import make_pdf


def test_job_from_text() -> None:
    posting = job_from_text("Senior Go engineer. Must know Kubernetes.")
    assert posting.source == "pasted"
    assert posting.description_text.startswith("Senior Go engineer")


def test_job_from_text_rejects_empty_and_huge() -> None:
    with pytest.raises(JobInputError):
        job_from_text("   ")
    with pytest.raises(JobInputError, match="20000"):
        job_from_text("x" * 20_001)


def test_job_from_pdf_extracts_text() -> None:
    posting = job_from_pdf(make_pdf("Backend Engineer Python Kubernetes"))
    assert posting.source == "pdf"
    assert "Backend Engineer Python Kubernetes" in posting.description_text


def test_pdf_too_large_rejected() -> None:
    with pytest.raises(JobInputError, match="2 MB"):
        job_from_pdf(b"%PDF-1.4" + b"0" * 2_000_001)


def test_pdf_garbage_rejected() -> None:
    with pytest.raises(JobInputError, match="could not read"):
        job_from_pdf(b"not a pdf at all")


async def test_resolve_job_requires_exactly_one_input() -> None:
    with pytest.raises(JobInputError):
        await resolve_job(url=None, text=None, pdf=None)


def test_pdf_with_too_many_pages_rejected() -> None:
    import io

    from pypdf import PdfReader, PdfWriter

    page = PdfReader(io.BytesIO(make_pdf("Engineer"))).pages[0]
    writer = PdfWriter()
    for _ in range(11):
        writer.add_page(page)
    buffer = io.BytesIO()
    writer.write(buffer)
    with pytest.raises(JobInputError, match="10 pages"):
        job_from_pdf(buffer.getvalue())


def test_pdf_extraction_stops_at_char_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.jobs.text as text_module

    calls: list[int] = []

    class Page:
        def extract_text(self) -> str:
            calls.append(1)
            return "x" * 15_000

    class Reader:
        def __init__(self, _stream: object) -> None:
            self.pages = [Page() for _ in range(5)]

    monkeypatch.setattr(text_module, "PdfReader", Reader)
    posting = job_from_pdf(b"%PDF-1.4 tiny")
    assert len(calls) == 2  # stopped once 20 000 chars were collected
    assert len(posting.description_text) == 20_000
