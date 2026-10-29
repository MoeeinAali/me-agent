import copy

import pytest
from pydantic import ValidationError

from app.record.schema import Book, Record, SyllabusCourse, public_view
from tests.record.factories import minimal_record


def test_minimal_record_is_valid() -> None:
    record = Record.model_validate(minimal_record())
    assert record.projects[0].id == "comeback"


def test_syllabus_rejects_references() -> None:
    with pytest.raises(ValidationError):
        SyllabusCourse.model_validate(
            {
                "code": "40254",
                "title_fa": "ساختمان داده‌ها و الگوریتم‌ها",
                "title_en": "Data Structures and Algorithms",
                "credits": 3,
                "prereqs": [],
                "topics": ["Trees"],
                "references": ["CLRS"],
            }
        )


def test_book_status_enum() -> None:
    with pytest.raises(ValidationError):
        Book.model_validate({"id": "x", "title": "X", "author": "Y", "status": "skimmed"})


def test_ids_unique() -> None:
    payload = minimal_record()
    payload["projects"].append(copy.deepcopy(payload["projects"][0]))
    with pytest.raises(ValidationError, match="duplicate id 'comeback' in projects"):
        Record.model_validate(payload)


def test_ids_are_slugs() -> None:
    payload = minimal_record()
    payload["projects"][0]["id"] = "Comeback App"
    with pytest.raises(ValidationError):
        Record.model_validate(payload)


def test_github_repo_shape() -> None:
    payload = minimal_record()
    payload["projects"][0]["github_repo"] = "https://github.com/a/b"
    with pytest.raises(ValidationError):
        Record.model_validate(payload)


def test_public_view_drops_internal() -> None:
    view = public_view(Record.model_validate(minimal_record()))
    assert "sources" not in view["meta"]
    assert view["contact"]["phone"] == "+98 935 1090 753"


def test_schema_export_marks_visibility() -> None:
    schema = Record.model_json_schema()
    contact = schema["$defs"]["Contact"]["properties"]
    assert contact["phone"]["x-visibility"] == "public"
    assert schema["$defs"]["Meta"]["properties"]["sources"]["x-visibility"] == "internal"


def test_load_record_and_syllabus_roundtrip(tmp_path: pytest.TempPathFactory) -> None:
    import json
    from pathlib import Path

    from app.record.loader import load_record, load_syllabus

    base = Path(str(tmp_path))
    (base / "record.json").write_text(json.dumps(minimal_record()), encoding="utf-8")
    (base / "syllabus.json").write_text(
        json.dumps([{"code": "40254", "title_fa": "ساختمان داده", "credits": 3, "topics": ["x"]}]),
        encoding="utf-8",
    )
    assert load_record(base / "record.json").person.name == "Moeein Aali"
    assert load_syllabus(base / "syllabus.json")[0].code == "40254"
