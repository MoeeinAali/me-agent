from app.importer.conflicts import Conflict, diff_sources


def site(**project: object) -> dict[str, object]:
    base = {"id": "zerang", "title": "Zerang", "date": "2025-11", "links": {}}
    base.update(project)
    return {"projects": [base], "experience": []}


def test_diff_detects_zerang_date_from_cv_experience() -> None:
    cv = {
        "projects": [],
        "experience": [
            {"company": "Zerang", "role": "Co-Founder", "start": "2026-02", "end": None}
        ],
    }
    assert diff_sources(site(), cv) == [
        Conflict(path="projects[zerang].date", site_value="2025-11", cv_value="2026-02")
    ]


def test_diff_detects_github_url_mismatch_case_insensitively() -> None:
    s = site(
        id="la-noire",
        title="L.A. Noire",
        date="2026-03",
        links={"github": "https://github.com/moeeinaali/la-noire"},
    )
    cv = {
        "projects": [
            {
                "title": "L.A. Noire",
                "date": "2026-03",
                "github": "https://github.com/L-A-Noire/",
                "live": None,
            }
        ],
        "experience": [],
    }
    conflicts = diff_sources(s, cv)
    assert [c.path for c in conflicts] == ["projects[la-noire].links.github"]


def test_diff_ignores_equal_values() -> None:
    s = site(
        id="kanban-board",
        title="Kanban Board",
        date="2026-02",
        links={"github": "https://github.com/moeeinaali/kanban-board"},
    )
    cv = {
        "projects": [
            {
                "title": "Kanban Board",
                "date": "2026-02",
                "github": "https://github.com/MoeeinAali/kanban-board/",
                "live": None,
            }
        ],
        "experience": [],
    }
    assert diff_sources(s, cv) == []
