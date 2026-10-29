import json
from pathlib import Path

import pytest

from app.domain import Evidence, Proof
from app.record.schema import Record
from tests.record.factories import minimal_record


@pytest.fixture
def record() -> Record:
    payload = minimal_record()
    payload["limits"] = json.loads(
        (Path(__file__).parents[3] / "data" / "record.json").read_text(encoding="utf-8")
    )["limits"]
    return Record.model_validate(payload)


def ev(eid: str, source: str = "record", trusted: bool = True, value: str = "v") -> Evidence:
    return Evidence(
        id=eid,
        path=f"projects[comeback].{eid.lower()}",
        value=value,
        source=source,  # type: ignore[arg-type]
        trusted=trusted,
        proof=Proof(type="record"),
    )
