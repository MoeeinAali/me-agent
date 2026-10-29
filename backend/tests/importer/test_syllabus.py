from pathlib import Path

from app.importer.syllabus import match_taken, parse_course, parse_program
from app.record.schema import CourseTaken, SyllabusCourse

FIX = Path(__file__).parents[1] / "fixtures"


def test_parse_program_has_40254() -> None:
    courses = {c["code"]: c for c in parse_program((FIX / "bs_ce_program.html").read_text())}
    dsa = courses["40254"]
    assert dsa["title_fa"] == "ساختمان داده‌ها و الگوریتم‌ها"
    assert dsa["credits"] == 3
    assert dsa["prereqs"] == ["ساختمان‌های گسسته", "برنامه‌سازی پیشرفته (هم‌نیاز)"]
    assert courses["40212"]["prereqs"] == []


def test_parse_course_topics_only() -> None:
    parsed = parse_course((FIX / "syllabus_40254.html").read_text())
    assert set(parsed) == {"topics"}
    assert parsed["topics"][0].startswith("مقدمات")
    assert "سطوح انتزاع" in parsed["topics"][0]
    assert not any("Cormen" in t or "مراجع" in t for t in parsed["topics"])


def test_match_taken_by_title_map() -> None:
    syllabus = [
        SyllabusCourse(code="40384", title_fa="طراحی پایگاه داده‌ها", credits=3, topics=["x"]),
        SyllabusCourse(code="40244", title_fa="برنامه‌سازی پیشرفته", credits=3, topics=["y"]),
    ]
    taken = [
        CourseTaken(id="database-design", title="Database Design", instructor="M", grade="20/20"),
        CourseTaken(id="unknown-course", title="Unknown Course", instructor="M", grade="20/20"),
    ]
    assert match_taken(taken, syllabus) == {"database-design": "40384", "unknown-course": None}


def test_parse_course_topic_does_not_repeat_its_title() -> None:
    first = parse_course((FIX / "syllabus_40254.html").read_text())["topics"][0]
    title, _, subtopics = first.partition(": ")
    assert title == "مقدمات (۱ جلسه)"
    assert not subtopics.startswith(title)
    assert subtopics.split("؛ ")[0] == "سطوح انتزاع"
