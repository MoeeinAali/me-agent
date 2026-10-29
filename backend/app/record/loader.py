"""Load and validate the record and syllabus files."""

from pathlib import Path

from pydantic import TypeAdapter

from app.record.schema import Record, SyllabusCourse

_syllabus_adapter = TypeAdapter(list[SyllabusCourse])


def load_record(path: Path) -> Record:
    return Record.model_validate_json(path.read_bytes())


def load_syllabus(path: Path) -> list[SyllabusCourse]:
    return _syllabus_adapter.validate_json(path.read_bytes())
