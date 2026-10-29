"""The personal record: the only source of facts about Moeein the agent may state.

Every field is visible to visitors unless declared ``internal``; the exported JSON Schema carries
that as ``x-visibility`` on each property, and :func:`public_view` strips internal fields.
"""

from collections import Counter
from datetime import date
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, model_validator

Visibility = Literal["public", "internal"]

Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
YearMonth = Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}$")]
GithubRepo = Annotated[str, StringConstraints(pattern=r"^[\w.-]+/[\w.-]+$")]
NonEmpty = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]

ForbiddenAction = Literal[
    "send_email", "book_meeting", "apply_to_job", "speak_for_sharif", "contact_third_party"
]


def internal(**kwargs: Any) -> Any:
    """A field hidden from visitors (``x-visibility: internal``)."""
    return Field(json_schema_extra={"x-visibility": "internal"}, **kwargs)


def _mark_visibility(schema: dict[str, Any], cls: type) -> None:
    for prop in schema.get("properties", {}).values():
        prop.setdefault("x-visibility", "public")


class RecordModel(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra=_mark_visibility, frozen=True)


class Meta(RecordModel):
    version: NonEmpty
    owner: NonEmpty
    sources: list[str] = internal(default_factory=list)


class Language(RecordModel):
    name: NonEmpty
    level: NonEmpty


class Person(RecordModel):
    name: NonEmpty
    headline: NonEmpty
    positioning: NonEmpty
    about: list[NonEmpty]
    location: NonEmpty
    languages: list[Language]


class Contact(RecordModel):
    email: NonEmpty
    phone: NonEmpty
    website: HttpUrl
    github: HttpUrl
    linkedin: HttpUrl


class Education(RecordModel):
    id: Slug
    institution: NonEmpty
    degree: NonEmpty
    location: str | None = None
    start: NonEmpty
    end: NonEmpty
    gpa: str | None = None
    coursework: list[NonEmpty] = Field(default_factory=list)


class Honor(RecordModel):
    id: Slug
    title: NonEmpty
    year: NonEmpty
    detail: NonEmpty


class CourseTaken(RecordModel):
    """A course Moeein took and passed. TA'd courses live in ``teaching``, never here."""

    id: Slug
    title: NonEmpty
    instructor: NonEmpty
    grade: NonEmpty
    syllabus_code: str | None = None


class Teaching(RecordModel):
    id: Slug
    institution: NonEmpty
    course: NonEmpty
    instructor: NonEmpty
    term: NonEmpty
    head_ta: bool


class Link(RecordModel):
    label: NonEmpty
    href: HttpUrl


class Experience(RecordModel):
    id: Slug
    company: NonEmpty
    role: NonEmpty
    employment: NonEmpty
    location: str | None = None
    start: NonEmpty
    end: NonEmpty
    bullets: list[NonEmpty]
    tech: list[NonEmpty] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)


class ProjectLinks(RecordModel):
    github: HttpUrl | None = None
    live: HttpUrl | None = None
    marketplace: HttpUrl | None = None


class Project(RecordModel):
    id: Slug
    title: NonEmpty
    summary: NonEmpty
    role: str | None = None
    date: YearMonth
    tags: list[NonEmpty]
    tech: list[NonEmpty]
    highlights: list[NonEmpty] = Field(default_factory=list)
    body_md: str | None = None
    links: ProjectLinks = Field(default_factory=ProjectLinks)
    github_repo: GithubRepo | None = None
    github_org: str | None = None
    course: str | None = None
    featured: bool = False


class Service(RecordModel):
    id: Slug
    org: NonEmpty
    role: NonEmpty
    edition: str | None = None
    period: str | None = None
    team: str | None = None
    head: bool = False


class SkillGroup(RecordModel):
    id: Slug
    label: NonEmpty
    items: list[NonEmpty]


class Book(RecordModel):
    """A book Moeein has read (or is reading). The only books the agent may say he read."""

    id: Slug
    title: NonEmpty
    author: NonEmpty
    status: Literal["read", "reading"]
    year: int | None = None
    finished: YearMonth | None = None
    note: str | None = None
    link: HttpUrl | None = None


class Faq(RecordModel):
    id: Slug
    question: NonEmpty
    answer: NonEmpty
    added: date
    source: NonEmpty


class Limits(RecordModel):
    forbidden_actions: list[ForbiddenAction]
    unpublished_topics: list[NonEmpty]
    guardrails: list[NonEmpty]


_ID_SECTIONS = (
    "education",
    "honors",
    "courses_taken",
    "teaching",
    "experience",
    "projects",
    "service",
    "skills",
    "books",
    "faq",
)


class Record(RecordModel):
    meta: Meta
    person: Person
    contact: Contact
    education: list[Education]
    honors: list[Honor]
    courses_taken: list[CourseTaken]
    teaching: list[Teaching]
    experience: list[Experience]
    projects: list[Project]
    service: list[Service]
    skills: list[SkillGroup]
    books: list[Book]
    faq: list[Faq]
    limits: Limits

    @model_validator(mode="after")
    def _unique_ids(self) -> "Record":
        for section in _ID_SECTIONS:
            counts = Counter(item.id for item in getattr(self, section))
            dupes = [i for i, n in counts.items() if n > 1]
            if dupes:
                raise ValueError(f"duplicate id '{dupes[0]}' in {section}")
        return self


class SyllabusCourse(RecordModel):
    """Official Sharif BS-CE course facts. Topics only: references are never stored."""

    code: NonEmpty
    title_fa: NonEmpty
    title_en: str | None = None
    credits: int
    prereqs: list[str] = Field(default_factory=list)
    topics: list[NonEmpty]


def public_view(record: Record) -> dict[str, Any]:
    """The record as visitors may see it: every ``internal`` field removed."""
    view: dict[str, Any] = _strip_internal(record)
    return view


def _strip_internal(value: Any) -> Any:
    if isinstance(value, BaseModel):
        out: dict[str, Any] = {}
        for name, field in type(value).model_fields.items():
            extra = field.json_schema_extra
            if isinstance(extra, dict) and extra.get("x-visibility") == "internal":
                continue
            out[name] = _strip_internal(getattr(value, name))
        return out
    if isinstance(value, list):
        return [_strip_internal(v) for v in value]
    if isinstance(value, HttpUrl):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value
