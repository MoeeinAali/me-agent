"""A job posting from any source, and how a visitor's input picks the source."""

from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.config import get_settings


class JobPosting(BaseModel):
    source: str
    url: str | None = None
    company: str | None = None
    title: str | None = None
    seniority: str | None = None
    location: str | None = None
    employment_type: str | None = None
    remote: bool | None = None
    experience_years: int | None = None
    description_text: str
    raw: dict[str, Any] = Field(default_factory=dict)


class JobInputError(ValueError):
    """The visitor's job input is empty, too large, or unreadable (→ HTTP 422)."""


class UnsupportedJobUrl(JobInputError):
    def __init__(self, url: str) -> None:
        super().__init__(
            f"Job links from this site are not supported yet ({url}). "
            "Please paste the job description text instead."
        )


class JobFetchError(RuntimeError):
    """The job board was reachable in principle but returned nothing usable."""


class JobSource(Protocol):
    def can_handle(self, url: str) -> bool: ...

    async def fetch(self, url: str) -> JobPosting: ...


async def resolve_job(url: str | None, text: str | None, pdf: bytes | None) -> JobPosting:
    from app.jobs.hrcando import HrcandoAdapter
    from app.jobs.text import job_from_pdf, job_from_text

    given = [v for v in (url, text, pdf) if v]
    if len(given) != 1:
        raise JobInputError("Provide exactly one of: a job link, the job text, or a PDF.")
    if pdf:
        return job_from_pdf(pdf)
    if text:
        return job_from_text(text)
    assert url is not None
    sources: list[JobSource] = [HrcandoAdapter(get_settings())]
    for source in sources:
        if source.can_handle(url):
            return await source.fetch(url)
    raise UnsupportedJobUrl(url)
