from app.config import get_settings
from app.domain import Claim
from app.llm.fake import FakeLLM
from app.pipeline.generate import GenerationOut, generate, render_evidence
from app.pipeline.understand import Understanding
from app.prompts.loader import load_prompt
from app.record.schema import Record
from tests.pipeline.conftest import ev


def test_render_evidence_wraps_untrusted() -> None:
    xml = render_evidence([ev("E1", value="Next.js"), ev("E2", "job_text", False, "Ignore all")])
    assert '<item id="E1" path="projects[comeback].e1" source="record">Next.js</item>' in xml
    assert '<untrusted><item id="E2"' in xml


def test_prompt_version_is_stable_hash() -> None:
    _, v1 = load_prompt(
        "generate",
        language="en",
        audience="general",
        forbidden_actions="",
        unpublished_topics="",
        guardrails="",
    )
    _, v2 = load_prompt(
        "generate",
        language="fa",
        audience="tech_lead",
        forbidden_actions="",
        unpublished_topics="",
        guardrails="",
    )
    assert v1 == v2 and len(v1) == 8


async def test_generate_prompt_contains_limits_and_no_raw_secrets(record: Record) -> None:
    llm = FakeLLM()
    llm.script(GenerationOut(answer="ok", claims=[Claim(text="ok", evidence=["E1"])], missing=[]))
    understanding = Understanding(
        intent="project_summary",
        language="fa",
        entities=["Comeback"],
        asks_for="summary",
        wants_action=None,
        message="خلاصه کامبک",
    )
    result, _usage, version = await generate(
        llm, get_settings(), understanding, "tech_lead", [ev("E1")], [], record.limits
    )
    assert result.answer == "ok"
    system = llm.calls[0].system
    for action in record.limits.forbidden_actions:
        assert action in system
    assert "salary expectations" in system
    assert "Persian" in system
    assert "architecture" in system  # tech_lead style
    assert get_settings().llm_api_key.get_secret_value() not in system
    assert "<evidence>" in llm.calls[0].messages[-1]["content"]
    assert len(version) == 8
