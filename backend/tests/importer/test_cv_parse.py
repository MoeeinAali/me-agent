from pathlib import Path

from app.importer.cv_parse import (
    parse_contact,
    parse_courses,
    parse_experience,
    parse_honors,
    parse_languages,
    parse_month,
    parse_projects,
)

CV = Path(__file__).parents[1] / "fixtures" / "cv"


def read(name: str) -> str:
    return (CV / name).read_text(encoding="utf-8")


def test_parse_courses_fixture() -> None:
    courses = parse_courses(read("10_courses.tex"))
    assert len(courses) == 11
    assert courses[0] == {
        "title": "Data and Network Security",
        "instructor": "Dr. M. Kharrazi and Dr. M. Amini",
        "grade": "20/20",
    }
    assert courses[-1]["title"] == "Advanced Programming"


def test_parse_honors() -> None:
    honors = parse_honors(read("03_honors.tex"))
    assert honors == [
        {
            "title": "National University Entrance Exam of Iran (Konkur)",
            "year": "2022",
            "detail": "Ranked 34th among more than 140,000 participants (top 0.03%)",
        }
    ]


def test_parse_languages() -> None:
    assert parse_languages(read("08_languages.tex")) == [
        {"name": "Persian (Farsi)", "level": "Native"},
        {"name": "English", "level": "Professional Working Proficiency"},
    ]


def test_parse_contact() -> None:
    contact = parse_contact(read("01_header.tex"))
    assert contact["email"] == "moeeeinaali@gmail.com"
    assert contact["phone"] == "+989351090753"
    assert contact["github"] == "https://github.com/moeeinaali"


def test_parse_month() -> None:
    assert parse_month("March 2026") == "2026-03"
    assert parse_month("Sep 2023") == "2023-09"
    assert parse_month("Present") is None


def test_parse_projects_includes_cv_only_tictactoe() -> None:
    projects = {p["title"]: p for p in parse_projects(read("05_projects.tex"))}
    assert "TicTacToe" in projects
    ttt = projects["TicTacToe"]
    assert ttt["date"] == "2024-05"
    assert ttt["tech"] == ["Kotlin"]
    assert ttt["github"] == "https://github.com/MoeeinAali/Android-TicTacToe"
    assert any("Kotlin" in b for b in ttt["bullets"])
    assert "\\textbf" not in " ".join(projects["L.A. Noire"]["bullets"])


def test_parse_experience_roles() -> None:
    roles = parse_experience(read("04_professional_experience.tex"))
    zerang = next(r for r in roles if r["company"] == "Zerang")
    assert zerang["start"] == "2026-02"
    assert zerang["end"] == "2026-08"
    comeback = next(r for r in roles if r["role"].startswith("Software Engineer, Comeback"))
    assert comeback["end"] is None
