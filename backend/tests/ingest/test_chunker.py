from app.ingest.chunker import explode, split_markdown
from app.record.schema import Record, SyllabusCourse
from tests.record.factories import minimal_record


def record_with_body() -> Record:
    payload = minimal_record()
    payload["projects"][0].update(
        highlights=["1M users", "WebSocket chat"],
        body_md="Intro paragraph.\n\n## Architecture\n\nNext.js and Go.\n\n## Delivery\n\nBazel.",
    )
    payload["books"] = [
        {"id": "clean-code", "title": "Clean Code", "author": "R. Martin", "status": "read"}
    ]
    return Record.model_validate(payload)


def test_explode_paths() -> None:
    drafts = {d.id: d for d in explode(record_with_body(), [], {"comeback": ["کامبک"]})}
    comeback = drafts["project:comeback"]
    assert comeback.path == "projects[comeback]"
    assert comeback.aliases == ["comeback", "Comeback", "کامبک"]
    chunks = {c.path: c.text for c in comeback.chunks}
    assert chunks["projects[comeback].summary"] == "Comeback — A Persian sports PWA."
    assert chunks["projects[comeback].highlights[1]"] == "Comeback — WebSocket chat"
    assert "projects[comeback].tech" in chunks
    assert drafts["book:clean-code"].chunks[0].text.startswith("Clean Code — ")
    assert "person:moeein" in drafts
    assert "contact:moeein" in drafts


def test_body_md_split_on_headings() -> None:
    sections = split_markdown("Intro.\n\n## Architecture\n\nNext.js.\n\n## Delivery\n\nBazel.")
    assert sections == [
        ("overview", "Intro."),
        ("architecture", "Architecture\n\nNext.js."),
        ("delivery", "Delivery\n\nBazel."),
    ]


def test_split_markdown_caps_long_sections() -> None:
    long = "## Big\n\n" + "\n\n".join(f"Paragraph {i} " + "word " * 120 for i in range(6))
    parts = split_markdown(long)
    assert len(parts) > 1
    assert all(len(text) <= 2000 for _, text in parts)
    assert parts[0][0] == "big" and parts[1][0] == "big-2"


def test_explode_syllabus_topics() -> None:
    course = SyllabusCourse(
        code="40384",
        title_fa="طراحی پایگاه داده‌ها",
        title_en="Database Design",
        credits=3,
        topics=["نرمال‌سازی: 1NF؛ 2NF", "تراکنش"],
    )
    payload = record_with_body().model_dump(mode="json")
    payload["courses_taken"] = [
        {
            "id": "database-design",
            "title": "Database Design",
            "instructor": "M",
            "grade": "20/20",
            "syllabus_code": "40384",
        }
    ]
    taken = Record.model_validate(payload)
    drafts = {d.id: d for d in explode(taken, [course], {})}
    syllabus = drafts["syllabus:40384"]
    assert syllabus.path == "syllabus[40384]"
    assert [c.path for c in syllabus.chunks] == [
        "syllabus[40384].topics[0]",
        "syllabus[40384].topics[1]",
    ]
    assert syllabus.chunks[0].lang == "fa"
    assert "Database Design" in syllabus.aliases


def test_syllabus_of_courses_not_taken_is_not_ingested() -> None:
    course = SyllabusCourse(code="40354", title_fa="طراحی الگوریتم‌ها", credits=3, topics=["x"])
    drafts = {d.id for d in explode(record_with_body(), [course], {})}
    assert "syllabus:40354" not in drafts
