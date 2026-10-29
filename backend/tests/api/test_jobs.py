import json
from pathlib import Path

import httpx
import respx

from app.domain import Claim
from app.jobs.hrcando import API_URL
from app.llm.fake import FakeLLM
from app.pipeline.generate import GenerationOut
from app.pipeline.jobfit import Requirement, RequirementsOut, RowJudgement
from app.pipeline.understand import UnderstandOut
from tests.jobs.pdf import make_pdf

MILLI = "https://career.hrcando.ir/co/Milli/job-detail/6867af3e-e373-4659-85a8-a9420cd14388"
FIXTURE = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "hrcando_milli.json").read_text(encoding="utf-8")
)


def script_jobfit(llm: FakeLLM, injected_claim: bool = False) -> None:
    llm.script(
        UnderstandOut(
            intent="job_fit", language="fa", entities=[], asks_for="job fit", wants_action=None
        ),
        RequirementsOut(
            requirements=[
                Requirement(
                    requirement="Next.js experience",
                    search_query="Next.js",
                    category="must",
                    kind="skill",
                ),
                Requirement(
                    requirement="۱ سال تجربه پشتیبانی مشتری",
                    search_query="customer support experience",
                    category="must",
                    kind="experience",
                ),
            ]
        ),
        RowJudgement(status="matched", evidence=["E1"]),
        RowJudgement(status="matched", evidence=["E1"]),  # the verifier must not trust this blindly
        GenerationOut(
            claims=[Claim(text="معین با Next.js کار کرده است.", evidence=["E1"])]
            + ([Claim(text="He worked at Google.", evidence=["J1"])] if injected_claim else []),
            missing=[],
        ),
    )


async def test_jobfit_milli_end_to_end(
    client: httpx.AsyncClient, fake_llm: FakeLLM, external: respx.MockRouter
) -> None:
    external.get(url__startswith=API_URL).mock(return_value=httpx.Response(200, json=FIXTURE))
    script_jobfit(fake_llm, injected_claim=True)
    response = await client.post(
        "/v1/chat", json={"message": "آیا برای این موقعیت مناسب است؟", "job_url": MILLI}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    card = body["scorecard"]
    assert card["job"] == {
        "source": "hrcando",
        "url": MILLI,
        "company": "میلی‌",
        "title": "کارشناس پشتیبانی و امور مشتریان (شیفت شب حضوری)",
    }
    assert len(card["rows"]) == 2
    assert card["verdict"] in {"strong", "partial", "weak"}
    trusted = {e["id"] for e in body["evidence"] if e["trusted"]}
    for claim in body["claims"]:
        assert set(claim["evidence"]) <= trusted
    assert "Google" not in body["answer"]
    assert body["capability"] == "answer_from_api"
    assert any(t["name"] == "hrcando" and t["ok"] for t in body["trace"]["tools_called"])
    assert any(e["source"] == "hrcando" and not e["trusted"] for e in body["evidence"])


async def test_jobfit_needs_a_posting(client: httpx.AsyncClient, fake_llm: FakeLLM) -> None:
    fake_llm.script(
        UnderstandOut(
            intent="job_fit", language="en", entities=[], asks_for="job fit", wants_action=None
        )
    )
    body = (
        await client.post("/v1/chat", json={"message": "Is he a fit for a backend role?"})
    ).json()
    assert body["capability"] == "clarify"
    assert "job" in body["answer"].lower()


async def test_jobs_fit_accepts_pdf(client: httpx.AsyncClient, fake_llm: FakeLLM) -> None:
    script_jobfit(fake_llm)
    response = await client.post(
        "/v1/jobs/fit",
        files={
            "file": ("job.pdf", make_pdf("Senior Frontend Engineer Next.js"), "application/pdf")
        },
        data={"audience": "recruiter"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["scorecard"]["job"]["source"] == "pdf"


async def test_jobs_fit_rejects_large_pdf_422(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/v1/jobs/fit",
        files={"file": ("big.pdf", b"%PDF-1.4" + b"0" * 2_000_001, "application/pdf")},
    )
    assert response.status_code == 422


async def test_hrcando_failure_is_502_with_paste_hint(
    client: httpx.AsyncClient, fake_llm: FakeLLM, external: respx.MockRouter
) -> None:
    external.get(url__startswith=API_URL).mock(return_value=httpx.Response(500))
    fake_llm.script(
        UnderstandOut(
            intent="job_fit", language="en", entities=[], asks_for="job fit", wants_action=None
        )
    )
    response = await client.post("/v1/chat", json={"message": "fit?", "job_url": MILLI})
    assert response.status_code == 502
    assert "paste" in response.json()["detail"]
