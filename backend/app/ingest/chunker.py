"""Explode the record into addressable entities and retrievable chunks.

Every chunk keeps the record path it came from (``projects[comeback].highlights[1]``) so answers
can name the exact fields they read. Chunk text is prefixed with the entity name, so a chunk such
as a single highlight still says what it is about.
"""

import re
from dataclasses import dataclass, field
from typing import Any

from app.record.schema import Record, SyllabusCourse

MAX_CHUNK_CHARS = 2000  # ~500 tokens
_PERSIAN = re.compile(r"[؀-ۿ]")


@dataclass
class ChunkDraft:
    path: str
    text: str
    lang: str = "en"


@dataclass
class EntityDraft:
    id: str
    kind: str
    record_id: str
    path: str
    name: str
    aliases: list[str]
    data: dict[str, Any]
    chunks: list[ChunkDraft] = field(default_factory=list)


def _lang(text: str) -> str:
    return "fa" if len(_PERSIAN.findall(text)) > len(text) / 4 else "en"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"


def split_markdown(markdown: str) -> list[tuple[str, str]]:
    """Split on ``## `` headings; sections longer than MAX_CHUNK_CHARS split on paragraphs."""
    sections: list[tuple[str, str]] = []
    heading, lines = "overview", list[str]()
    for line in markdown.strip().splitlines():
        if line.startswith("## "):
            if "\n".join(lines).strip():
                sections.append((heading, "\n".join(lines).strip()))
            heading, lines = _slug(line[3:]), [line[3:].strip()]
        else:
            lines.append(line)
    if "\n".join(lines).strip():
        sections.append((heading, "\n".join(lines).strip()))

    out: list[tuple[str, str]] = []
    for name, text in sections:
        pieces, current = [], ""
        for paragraph in text.split("\n\n"):
            candidate = f"{current}\n\n{paragraph}" if current else paragraph
            if len(candidate) > MAX_CHUNK_CHARS and current:
                pieces.append(current)
                current = paragraph[:MAX_CHUNK_CHARS]
            else:
                current = candidate[:MAX_CHUNK_CHARS]
        if current:
            pieces.append(current)
        out += [(name if i == 0 else f"{name}-{i + 1}", piece) for i, piece in enumerate(pieces)]
    return out


class _Builder:
    def __init__(self, aliases: dict[str, list[str]]) -> None:
        self.drafts: list[EntityDraft] = []
        self._aliases = aliases

    def entity(
        self,
        kind: str,
        record_id: str,
        path: str,
        name: str,
        data: Any,
        extra: tuple[str, ...] | list[str] = (),
    ) -> EntityDraft:
        names = [record_id, *extra, *self._aliases.get(record_id, [])]
        draft = EntityDraft(
            id=f"{kind}:{record_id}",
            kind=kind,
            record_id=record_id,
            path=path,
            name=name,
            aliases=list(dict.fromkeys(a for a in names if a)),
            data=data.model_dump(mode="json") if hasattr(data, "model_dump") else data,
        )
        self.drafts.append(draft)
        return draft


def _add(draft: EntityDraft, field_path: str, text: str | None) -> None:
    if text and text.strip():
        body = text.strip()
        draft.chunks.append(
            ChunkDraft(f"{draft.path}.{field_path}", f"{draft.name} — {body}", _lang(body))
        )


def explode(
    record: Record, syllabus: list[SyllabusCourse], aliases: dict[str, list[str]]
) -> list[EntityDraft]:
    b = _Builder(aliases)

    person = b.entity("person", "moeein", "person", record.person.name, record.person)
    _add(person, "headline", record.person.headline)
    _add(person, "positioning", record.person.positioning)
    for i, paragraph in enumerate(record.person.about):
        _add(person, f"about[{i}]", paragraph)
    _add(person, "location", f"based in {record.person.location}")
    _add(person, "languages", "; ".join(f"{x.name}: {x.level}" for x in record.person.languages))

    contact = b.entity("contact", "moeein", "contact", "Contact", record.contact)
    for key, value in record.contact.model_dump(mode="json").items():
        _add(contact, key, f"{key}: {value}")

    for e in record.education:
        d = b.entity("education", e.id, f"education[{e.id}]", e.institution, e)
        _add(d, "degree", f"{e.degree}, {e.start} – {e.end}" + (f", GPA {e.gpa}" if e.gpa else ""))
        _add(d, "coursework", f"coursework: {', '.join(e.coursework)}" if e.coursework else None)

    for h in record.honors:
        d = b.entity("honor", h.id, f"honors[{h.id}]", h.title, h)
        _add(d, "detail", f"{h.year}: {h.detail}")

    for c in record.courses_taken:
        d = b.entity("course", c.id, f"courses_taken[{c.id}]", c.title, c, [c.syllabus_code or ""])
        _add(d, "summary", f"course Moeein took; instructor {c.instructor}; grade {c.grade}")

    for t in record.teaching:
        d = b.entity("teaching", t.id, f"teaching[{t.id}]", f"TA: {t.course}", t, [t.course])
        role = "head teaching assistant" if t.head_ta else "teaching assistant"
        _add(d, "summary", f"{role} for {t.course} ({t.instructor}), {t.term}, {t.institution}")

    for x in record.experience:
        d = b.entity(
            "experience", x.id, f"experience[{x.id}]", f"{x.role} at {x.company}", x, [x.company]
        )
        _add(
            d,
            "summary",
            f"{x.employment}, {x.start} – {x.end}" + (f", {x.location}" if x.location else ""),
        )
        for i, bullet in enumerate(x.bullets):
            _add(d, f"bullets[{i}]", bullet)
        _add(d, "tech", f"tech: {', '.join(x.tech)}" if x.tech else None)

    for p in record.projects:
        d = b.entity("project", p.id, f"projects[{p.id}]", p.title, p, [p.title])
        _add(d, "summary", p.summary)
        _add(d, "role", p.role and f"Moeein's role: {p.role}")
        _add(d, "date", f"date: {p.date}")
        _add(d, "tech", f"tech: {', '.join(p.tech)}")
        for i, highlight in enumerate(p.highlights):
            _add(d, f"highlights[{i}]", highlight)
        for name, text in split_markdown(p.body_md or ""):
            _add(d, f"body[{name}]", text)

    for s in record.service:
        label = f"{s.role}, {s.edition}" if s.edition else s.role
        d = b.entity("service", s.id, f"service[{s.id}]", label, s, [s.org])
        _add(d, "summary", f"{s.org}" + (f", {s.period}" if s.period else ""))

    for g in record.skills:
        d = b.entity("skills", g.id, f"skills[{g.id}]", f"Skills: {g.label}", g)
        _add(d, "items", ", ".join(g.items))

    for book in record.books:
        d = b.entity("book", book.id, f"books[{book.id}]", book.title, book, [book.title])
        status = "has read" if book.status == "read" else "is currently reading"
        _add(
            d,
            "summary",
            f"by {book.author}; Moeein {status} it" + (f". Note: {book.note}" if book.note else ""),
        )

    for f in record.faq:
        d = b.entity("faq", f.id, f"faq[{f.id}]", f.question, f)
        _add(d, "answer", f.answer)

    # Only courses Moeein took: a syllabus topic is evidence about him only through a course he
    # passed. The rest of the program stays out of retrieval entirely.
    taken = {c.syllabus_code for c in record.courses_taken if c.syllabus_code}
    for course in (c for c in syllabus if c.code in taken):
        d = b.entity(
            "syllabus",
            course.code,
            f"syllabus[{course.code}]",
            course.title_fa,
            course,
            [course.title_en or ""],
        )
        for i, topic in enumerate(course.topics):
            _add(d, f"topics[{i}]", topic)

    return b.drafts
