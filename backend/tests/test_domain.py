import pytest
from pydantic import ValidationError

from app.domain import ChatRequest, ChatResponse


@pytest.mark.parametrize("message", ["", "   ", "x" * 2001])
def test_chat_request_rejects_bad_message(message: str) -> None:
    with pytest.raises(ValidationError):
        ChatRequest(message=message)


def test_chat_request_rejects_long_job_text() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(message="fit?", job_text="x" * 20_001)


def test_chat_request_strips_and_defaults() -> None:
    req = ChatRequest(message="  Summarize Comeback  ")
    assert req.message == "Summarize Comeback"
    assert req.audience == "general"
    assert req.conversation_id is None


def test_chat_request_limit_follows_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_MESSAGE_CHARS", "10")
    with pytest.raises(ValidationError):
        ChatRequest(message="x" * 11)


def test_chat_response_schema_names_capabilities() -> None:
    schema = ChatResponse.model_json_schema()
    capability = schema["properties"]["capability"]
    assert set(capability["enum"]) == {
        "answer_from_record",
        "answer_from_api",
        "clarify",
        "refuse_unpublished",
        "refuse_action",
        "out_of_scope",
    }
