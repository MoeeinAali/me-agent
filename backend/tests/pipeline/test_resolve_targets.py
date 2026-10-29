from types import SimpleNamespace

import pytest

import app.pipeline.run as run_module
from app.pipeline.run import _resolve_targets
from app.pipeline.understand import Understanding
from app.retrieval.resolve import Candidate

DEPS = SimpleNamespace(session=None, llm=None)


async def test_same_name_across_kinds_targets_all(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_resolve(
        _s: object, _l: object, mention: str, kind: str | None
    ) -> list[Candidate]:
        return [
            Candidate("project:zerang", "project", "Zerang", 1.0),
            Candidate("experience:zerang-cofounder", "experience", "Co-Founder at Zerang", 1.0),
        ]

    monkeypatch.setattr(run_module, "resolve", fake_resolve)
    u = Understanding(
        intent="fact_lookup",
        language="en",
        entities=["Zerang"],
        asks_for="role at Zerang",
        wants_action=None,
        message="What did he do?",
    )
    resolution = await _resolve_targets(DEPS, u)  # type: ignore[arg-type]
    assert {t.entity_id for t in resolution.targets} == {
        "project:zerang",
        "experience:zerang-cofounder",
    }


async def test_too_many_matches_are_left_to_search(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_resolve(
        _s: object, _l: object, mention: str, kind: str | None
    ) -> list[Candidate]:
        return [Candidate(f"teaching:t{i}", "teaching", f"TA {i}", 1.0) for i in range(6)]

    monkeypatch.setattr(run_module, "resolve", fake_resolve)
    u = Understanding(
        intent="fact_lookup",
        language="en",
        entities=["TA"],
        asks_for="TA",
        wants_action=None,
        message="TA?",
    )
    assert (await _resolve_targets(DEPS, u)).targets == []  # type: ignore[arg-type]
