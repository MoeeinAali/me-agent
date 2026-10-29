from app.llm.fake import FakeLLM
from app.pipeline.policy import policy
from app.pipeline.understand import Understanding
from app.record.schema import Record


def u(
    asks_for: str, intent: str = "fact_lookup", wants_action: str | None = None, message: str = ""
) -> Understanding:
    return Understanding(
        intent=intent,
        language="en",
        entities=[],
        asks_for=asks_for,
        wants_action=wants_action,
        message=message or asks_for,
    )  # type: ignore[arg-type]


async def test_policy_salary_refused_fa(record: Record) -> None:
    decision = await policy(FakeLLM(), u("حقوق درخواستی", message="حقوق درخواستیش چقدره؟"), record)
    assert decision.capability == "refuse_unpublished"
    assert decision.reason == "salary expectations"


async def test_policy_email_action(record: Record) -> None:
    decision = await policy(FakeLLM(), u("contact him", wants_action="send_email"), record)
    assert decision.capability == "refuse_action"


async def test_policy_email_address_is_not_home_address(record: Record) -> None:
    decision = await policy(FakeLLM(), u("his email address"), record)
    assert decision.capability is None


async def test_policy_out_of_scope(record: Record) -> None:
    decision = await policy(FakeLLM(), u("capital of France", intent="out_of_scope"), record)
    assert decision.capability == "out_of_scope"


async def test_policy_semantic_match_on_topic(record: Record) -> None:
    decision = await policy(FakeLLM(), u("political views"), record)
    assert decision.capability == "refuse_unpublished"


async def test_policy_lets_ordinary_question_through(record: Record) -> None:
    assert (await policy(FakeLLM(), u("Comeback tech stack"), record)).capability is None
