import httpx
import respx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KnowledgeGap, TraceRow
from app.domain import Claim
from app.llm.fake import FakeLLM
from app.pipeline.generate import GenerationOut
from app.pipeline.understand import UnderstandOut


def understood(
    intent: str,
    entities: list[str],
    asks_for: str,
    language: str = "en",
    wants_action: str | None = None,
) -> UnderstandOut:
    return UnderstandOut(
        intent=intent,
        language=language,
        entities=entities,  # type: ignore[arg-type]
        asks_for=asks_for,
        wants_action=wants_action,
    )  # type: ignore[arg-type]


async def ask(client: httpx.AsyncClient, message: str, **extra: object) -> dict:  # type: ignore[type-arg]
    response = await client.post("/v1/chat", json={"message": message, **extra})
    assert response.status_code == 200, response.text
    return response.json()  # type: ignore[no-any-return]


async def test_good_answer_project_summary(
    client: httpx.AsyncClient, fake_llm: FakeLLM, ingested: AsyncSession
) -> None:
    fake_llm.script(
        understood("project_summary", ["Comeback"], "Comeback summary"),
        GenerationOut(
            claims=[Claim(text="Comeback is a Persian sports PWA.", evidence=["E1"])],
            missing=["deployment date"],
        ),
    )
    body = await ask(client, "Summarize the Comeback project")

    assert body["capability"] in {"answer_from_record", "answer_from_api"}
    assert body["answer"].startswith("Comeback is a Persian sports PWA.")
    assert "deployment date" in body["answer"]
    trace = body["trace"]
    assert "projects[comeback].summary" in trace["fields_read"]
    assert trace["intent"] == "project_summary"
    assert trace["missing"] == ["deployment date"]
    assert any(t["name"].startswith("link_check") for t in trace["tools_called"])
    assert await ingested.scalar(select(func.count()).select_from(TraceRow)) == 1


async def test_clarify_when_ambiguous(client: httpx.AsyncClient, fake_llm: FakeLLM) -> None:
    fake_llm.script(understood("project_summary", ["project"], "a project summary"))
    body = await ask(client, "Tell me about his project")
    assert body["capability"] == "clarify"
    assert body["clarify_options"] == ["Comeback", "Kanban Board"]
    assert body["answer"].count("?") == 1
    assert not [c for c in fake_llm.calls if c.schema is GenerationOut]


async def test_clarify_followup_ordinal_fa(client: httpx.AsyncClient, fake_llm: FakeLLM) -> None:
    fake_llm.script(understood("project_summary", ["project"], "a project summary", "fa"))
    first = await ask(client, "درباره پروژه‌اش بگو")
    assert first["capability"] == "clarify"
    assert "کدام" in first["answer"]

    fake_llm.script(
        understood("fact_lookup", [], "which one", "fa"),
        GenerationOut(claims=[Claim(text="کانبان یک برد وظایف است.", evidence=["E1"])], missing=[]),
    )
    second = await ask(client, "دومی", conversation_id=first["conversation_id"])
    assert second["capability"] in {"answer_from_record", "answer_from_api"}
    assert second["trace"]["intent"] == "project_summary"
    assert any(p.startswith("projects[kanban-board]") for p in second["trace"]["fields_read"])


async def test_policy_refusal_for_limited_topic_is_not_a_gap(
    client: httpx.AsyncClient, fake_llm: FakeLLM, ingested: AsyncSession
) -> None:
    fake_llm.script(understood("fact_lookup", [], "salary expectations"))
    body = await ask(client, "What is his salary expectation?")
    assert body["capability"] == "refuse_unpublished"
    assert "salary expectations" in body["answer"]
    assert await ingested.scalar(select(func.count()).select_from(KnowledgeGap)) == 0


async def test_unknown_fact_refused_and_recorded_as_gap(
    client: httpx.AsyncClient, fake_llm: FakeLLM, ingested: AsyncSession
) -> None:
    for _ in range(2):
        fake_llm.script(
            understood("fact_lookup", ["Google"], "employment at Google"),
            GenerationOut(claims=[], missing=["employment at Google"]),
        )
        body = await ask(client, "Did he work at Google?")
        assert body["capability"] == "refuse_unpublished"
        assert "Google" not in body["answer"].split("Not in the record:")[0]
    gaps = (await ingested.scalars(select(KnowledgeGap))).all()
    assert len(gaps) == 1
    assert gaps[0].count == 2


async def test_forbidden_action_refused(client: httpx.AsyncClient, fake_llm: FakeLLM) -> None:
    fake_llm.script(understood("fact_lookup", [], "email him", wants_action="send_email"))
    body = await ask(client, "Email him and ask for an interview")
    assert body["capability"] == "refuse_action"


async def test_out_of_scope(client: httpx.AsyncClient, fake_llm: FakeLLM) -> None:
    fake_llm.script(understood("out_of_scope", [], "capital of France"))
    assert (await ask(client, "What's the capital of France?"))["capability"] == "out_of_scope"


async def test_github_down_still_answers(
    client: httpx.AsyncClient, fake_llm: FakeLLM, external: respx.MockRouter
) -> None:
    fake_llm.script(
        understood("project_summary", ["Kanban Board"], "Kanban Board summary"),
        GenerationOut(
            claims=[Claim(text="A drag-and-drop task board.", evidence=["E1"])], missing=[]
        ),
    )
    body = await ask(client, "Summarize Kanban Board")
    assert body["capability"] == "answer_from_record"
    github = [t for t in body["trace"]["tools_called"] if t["name"].startswith("github")]
    assert github and github[0]["ok"] is False


async def test_chat_rejects_empty_message_422(client: httpx.AsyncClient) -> None:
    response = await client.post("/v1/chat", json={"message": "   "})
    assert response.status_code == 422


async def test_clarify_with_many_projects_lists_featured_first_as_examples() -> None:
    from app.pipeline.run import clarify_text
    from app.retrieval.resolve import Candidate

    candidates = [Candidate(f"project:p{i}", "project", f"P{i}", 1.0) for i in range(10)]
    featured_order = {"p7": 1, "p3": 2}
    text, shown = clarify_text(candidates, featured_order, "project_summary", "en")
    assert [c.label for c in shown][:2] == ["P7", "P3"]
    assert len(shown) == 6
    assert text.startswith("Which project do you mean? For example:")
    few, _ = clarify_text(candidates[:2], {}, "project_summary", "en")
    assert few == "Which project do you mean: P0 or P1?"
