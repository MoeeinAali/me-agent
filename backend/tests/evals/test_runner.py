import uuid

from app.domain import ChatResponse, Trace
from app.evals.runner import EvalCase, score_case


def response(
    answer: str,
    capability: str = "answer_from_record",
    intent: str = "fact_lookup",
    fields: list[str] | None = None,
) -> ChatResponse:
    trace = Trace(
        id=uuid.uuid4(),
        question="q",
        language="en",
        intent=intent,  # type: ignore[arg-type]
        audience="general",
        channel="eval",
        fields_read=fields or [],
        tools_called=[],
        capability=capability,
        answer=answer,
        missing=[],
        latency_ms=1,  # type: ignore[arg-type]
        tokens_in=1,
        tokens_out=1,
        prompt_version="x",
    )
    return ChatResponse(
        conversation_id=uuid.uuid4(),
        answer=answer,
        capability=capability,  # type: ignore[arg-type]
        claims=[],
        evidence=[],
        trace=trace,
    )


def case(**overrides: object) -> EvalCase:
    base: dict[str, object] = {
        "id": "c1",
        "category": "good",
        "question": "q",
        "lang": "en",
        "expected_capability": ["answer_from_record"],
    }
    base.update(overrides)
    return EvalCase.model_validate(base)


def test_runner_passes_matching_case() -> None:
    result = score_case(
        case(
            expected_intent="project_summary",
            must_read_paths=["projects[comeback]"],
            must_contain=["PWA"],
        ),
        response("A PWA.", intent="project_summary", fields=["projects[comeback].summary"]),
    )
    assert result.passed, result.failures


def test_runner_fails_forbidden_string() -> None:
    result = score_case(case(forbidden_strings=["Google"]), response("He worked at Google."))
    assert not result.passed
    assert result.failures == ["forbidden string present: Google"]


def test_runner_fails_wrong_capability_and_missing_read() -> None:
    result = score_case(
        case(expected_capability=["refuse_unpublished"], must_read_paths=["books["]), response("x")
    )
    assert len(result.failures) == 2


def test_expected_capability_accepts_single_string() -> None:
    assert case(expected_capability="clarify").expected_capability == ["clarify"]
