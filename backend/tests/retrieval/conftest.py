import json
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.ingest import ingest
from app.llm.fake import FakeLLM
from tests.record.factories import minimal_record


def two_project_record() -> dict[str, object]:
    payload = minimal_record()
    payload["projects"][0].update(
        tech=["Next.js", "Bazel", "Kubernetes"], highlights=["Served over one million users"]
    )
    payload["projects"].append(
        {
            "id": "kanban-board",
            "title": "Kanban Board",
            "summary": "A drag-and-drop task board.",
            "date": "2026-02",
            "tags": ["react"],
            "tech": ["React", "DnDKit"],
        }
    )
    payload["experience"] = [
        {
            "id": "yektanet-uranus",
            "company": "Yektanet",
            "role": "Software Engineer, Uranus Business Line",
            "employment": "Full-time",
            "start": "January 2025",
            "end": "May 2026",
            "bullets": ["Built the Uranus website."],
        }
    ]
    payload["books"] = [
        {"id": "clean-code", "title": "Clean Code", "author": "Robert C. Martin", "status": "read"}
    ]
    return payload


@pytest.fixture
async def ingested(session: AsyncSession, tmp_path: Path) -> AsyncSession:
    (tmp_path / "record.json").write_text(json.dumps(two_project_record()), encoding="utf-8")
    (tmp_path / "syllabus.json").write_text("[]", encoding="utf-8")
    (tmp_path / "aliases.json").write_text('{"comeback": ["کامبک"]}', encoding="utf-8")
    await ingest(
        session,
        FakeLLM(),
        tmp_path / "record.json",
        tmp_path / "syllabus.json",
        tmp_path / "aliases.json",
    )
    return session
