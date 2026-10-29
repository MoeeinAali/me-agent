from pathlib import Path

from app.importer.build_record import build_record, slugify
from app.record.schema import Record

CV = Path(__file__).parents[1] / "fixtures" / "cv"


def site_payload() -> dict[str, object]:
    return {
        "profile": {
            "headline": "Full-Stack Software Engineer",
            "positioning": "Moeein Aali builds production systems.",
            "about": ["I'm a CE student at Sharif."],
        },
        "projects": [
            {
                "id": "arcadia",
                "title": "Arcadia",
                "summary": "A Steam-like platform.",
                "date": "2026-07",
                "tags": ["course-project"],
                "tech": ["Go"],
                "links": {"github": "https://github.com/orgs/MS-Arcadia/repositories"},
                "featured": True,
                "contentSlug": "arcadia",
            },
            {
                "id": "kanban-board",
                "title": "Kanban Board",
                "summary": "A board.",
                "date": "2026-02",
                "tags": ["react"],
                "tech": ["React"],
                "links": {"github": "https://github.com/moeeinaali/kanban-board"},
                "featured": False,
            },
        ],
        "experience": [
            {
                "company": "Yektanet",
                "location": "Tehran, Iran",
                "roles": [
                    {
                        "title": "Software Engineer, Comeback",
                        "employment": "Full-time",
                        "start": "June 2026",
                        "end": "Present",
                        "bullets": [{"text": "Owned the client.", "links": []}, "Drove perf."],
                        "tech": ["Next.js"],
                    }
                ],
            }
        ],
        "teaching": [
            {
                "organizationId": "sharif",
                "courses": [
                    {
                        "course": "Database Design",
                        "instructor": "Dr. R",
                        "period": "Spring 2025",
                        "head": True,
                    }
                ],
            }
        ],
        "education": [
            {
                "organizationId": "sharif",
                "institution": "Sharif University of Technology",
                "degree": "B.Sc. in Computer Engineering",
                "location": "Tehran, Iran",
                "start": "September 2022",
                "end": "January 2027 (Expected)",
                "grade": "18.01 / 20.00",
                "coursework": ["Software Engineering"],
            }
        ],
        "honors": [{"title": "Konkur", "year": "2022", "detail": "Ranked 34th."}],
        "skills": [{"id": "languages", "label": "Languages", "items": ["Go"]}],
        "books": [
            {
                "id": "clean-code",
                "title": "Clean Code",
                "author": "Robert C. Martin",
                "cover": "/x.webp",
                "initials": "CC",
                "isPlaceholderCover": False,
                "status": "read",
                "year": 2008,
            }
        ],
        "service": [
            {
                "organizationId": "wss",
                "roles": [
                    {
                        "role": "Head of Technical Team",
                        "edition": "11th WSS",
                        "period": "2025 – 2026",
                        "team": "technical",
                        "head": True,
                    }
                ],
            }
        ],
        "organizations": [
            {"id": "sharif", "name": "Sharif University of Technology"},
            {"id": "wss", "name": "Winter Seminar Series"},
        ],
    }


def test_slugify() -> None:
    assert slugify("L.A. Noire") == "l-a-noire"
    assert slugify("Software Engineer, Comeback") == "software-engineer-comeback"


def test_build_record_validates_and_merges(tmp_path: Path) -> None:
    content = tmp_path / "content"
    content.mkdir()
    (content / "arcadia.md").write_text(
        "---\ntitle: Arcadia\nrole: Backend lead\nhighlights:\n  - 14 microservices\n---\n\n"
        "## Overview\n\nArcadia is a platform.\n",
        encoding="utf-8",
    )
    record, conflicts = build_record(site_payload(), CV, content, today="2026-10-29")
    Record.model_validate(record.model_dump(mode="json"))

    by_id = {p.id: p for p in record.projects}
    assert by_id["arcadia"].role == "Backend lead"
    assert by_id["arcadia"].highlights == ["14 microservices"]
    assert by_id["arcadia"].body_md is not None and "## Overview" in by_id["arcadia"].body_md
    assert by_id["arcadia"].github_repo is None
    assert by_id["arcadia"].github_org == "MS-Arcadia"
    assert by_id["kanban-board"].github_repo == "moeeinaali/kanban-board"
    assert "tictactoe" in by_id  # CV-only project is kept
    assert len(record.courses_taken) == 11
    assert record.teaching[0].head_ta is True
    assert record.service[0].org == "Winter Seminar Series"
    assert record.education[0].gpa == "18.01 / 20.00"
    assert record.contact.phone == "+989351090753"
    assert "salary expectations" in record.limits.unpublished_topics
    assert record.experience[0].bullets == ["Owned the client.", "Drove perf."]
    assert all(c.path.startswith("projects[") for c in conflicts)
