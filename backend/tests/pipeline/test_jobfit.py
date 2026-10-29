import pytest

from app.domain import ScorecardRow
from app.pipeline.jobfit import RowJudgement, coerce_judgement, coverage, verdict
from tests.pipeline.conftest import ev


def row(category: str, status: str) -> ScorecardRow:
    return ScorecardRow(
        requirement="r",
        category=category,
        kind="skill",  # type: ignore[arg-type]
        status=status,
        evidence=[],
    )  # type: ignore[arg-type]


def test_coverage_weights() -> None:
    rows = [row("must", "matched"), row("must", "partial"), row("nice", "no_evidence")]
    assert coverage(rows) == pytest.approx(0.6)
    assert verdict(coverage(rows)) == "partial"


def test_coverage_of_nothing_is_zero() -> None:
    assert coverage([]) == 0.0


def test_verdict_bands() -> None:
    assert verdict(0.75) == "strong"
    assert verdict(0.4) == "partial"
    assert verdict(0.39) == "weak"


def test_uncited_match_coerced() -> None:
    evidence = [ev("E1"), ev("E2", source="hrcando", trusted=False)]
    assert coerce_judgement(RowJudgement(status="matched", evidence=[]), evidence).status == (
        "no_evidence"
    )
    only_job = coerce_judgement(RowJudgement(status="partial", evidence=["E2"]), evidence)
    assert only_job.status == "no_evidence" and only_job.evidence == []
    kept = coerce_judgement(RowJudgement(status="matched", evidence=["E1", "E9"]), evidence)
    assert kept.status == "matched" and kept.evidence == ["E1"]
    assert (
        coerce_judgement(RowJudgement(status="no_evidence", evidence=["E1"]), evidence).evidence
        == []
    )


async def test_requirements_are_searched_in_english(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.pipeline.jobfit as jobfit
    from app.pipeline.jobfit import Requirement, search_requirement

    seen: list[str] = []

    async def fake_search(_session: object, _llm: object, query: str, **_: object) -> list[object]:
        seen.append(query)
        return []

    monkeypatch.setattr(jobfit, "search", fake_search)
    requirement = Requirement(
        requirement="حداقل مدرک کارشناسی",
        search_query="bachelor's degree",
        category="must",
        kind="education",
    )
    await search_requirement(None, None, requirement, {"education"})  # type: ignore[arg-type]
    assert seen == ["bachelor's degree"]


async def test_every_requirement_keeps_its_evidence_past_the_chat_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.pipeline.jobfit as jobfit
    from app.pipeline.jobfit import Requirement, evidence_for_requirements
    from app.retrieval.hybrid import Hit

    async def long_hits(_s: object, _l: object, query: str, **_: object) -> list[Hit]:
        return [
            Hit(
                f"{query}-{i}",
                "project:x",
                "project",
                f"projects[x].body[{query}-{i}]",
                "x" * 2000,
                1.0,
            )
            for i in range(5)
        ]

    monkeypatch.setattr(jobfit, "search", long_hits)
    requirements = [
        Requirement(requirement=f"r{i}", search_query=f"q{i}", category="must", kind="skill")
        for i in range(15)
    ]
    collector, per_requirement = await evidence_for_requirements(
        None,
        None,
        requirements,
        {"project"},  # type: ignore[arg-type]
    )
    assert [len(items) for items in per_requirement] == [5] * 15
    assert all(len(e.value) <= jobfit.JOBFIT_VALUE_CHARS for e in collector.bundle.evidence)
