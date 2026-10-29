"""Eval suite: run every case in evals/cases.yaml through the real pipeline and score it.

A prompt or model change is accepted only if the pass rate does not regress.
"""

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EvalResult, EvalRun
from app.domain import Audience, ChatRequest, ChatResponse, Evidence, Intent, Lang
from app.evals.judge import judge_claims
from app.pipeline.deps import Deps
from app.pipeline.jobfit import job_fit_handler
from app.pipeline.run import run_chat
from app.prompts.loader import load_prompt

EVALS_DIR = Path(__file__).resolve().parents[3] / "evals"


class EvalCase(BaseModel):
    id: str
    category: str
    question: str
    lang: Lang
    audience: Audience = "general"
    job_fixture: str | None = None
    followup_of: str | None = None
    expected_intent: Intent | None = None
    expected_capability: list[str]
    must_read_paths: list[str] = []
    forbidden_strings: list[str] = []
    must_contain: list[str] = []
    subset: list[str] = []

    @field_validator("expected_capability", mode="before")
    @classmethod
    def _one_or_many(cls, value: Any) -> Any:
        return [value] if isinstance(value, str) else value


@dataclass
class CaseResult:
    case: EvalCase
    passed: bool
    failures: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


def score_case(case: EvalCase, response: ChatResponse) -> CaseResult:
    failures: list[str] = []
    if response.capability not in case.expected_capability:
        failures.append(f"capability {response.capability} not in {case.expected_capability}")
    if case.expected_intent and response.trace.intent != case.expected_intent:
        failures.append(f"intent {response.trace.intent} != {case.expected_intent}")
    for prefix in case.must_read_paths:
        if not any(path.startswith(prefix) for path in response.trace.fields_read):
            failures.append(f"did not read {prefix}")
    lowered = response.answer.lower()
    failures += [
        f"forbidden string present: {s}" for s in case.forbidden_strings if s.lower() in lowered
    ]
    failures += [
        f"missing expected text: {s}" for s in case.must_contain if s.lower() not in lowered
    ]
    details = {
        "answer": response.answer,
        "capability": response.capability,
        "intent": response.trace.intent,
        "fields_read": response.trace.fields_read,
    }
    return CaseResult(case, not failures, failures, details)


def load_cases(subset: str | None = None) -> list[EvalCase]:
    raw = yaml.safe_load((EVALS_DIR / "cases.yaml").read_text(encoding="utf-8"))
    cases = [EvalCase.model_validate(item) for item in raw["cases"]]
    return [c for c in cases if subset is None or subset in c.subset]


async def run_case(deps: Deps, case: EvalCase, conversation: uuid.UUID | None) -> ChatResponse:
    job_text = None
    if case.job_fixture:
        job_text = (EVALS_DIR / "fixtures" / case.job_fixture).read_text(encoding="utf-8")
    req = ChatRequest(
        message=case.question,
        audience=case.audience,
        job_text=job_text,
        conversation_id=conversation,
    )
    return await run_chat(req, "eval", deps, job_fit=job_fit_handler())


async def run_suite(
    deps: Deps, session: AsyncSession, subset: str | None, use_judge: bool
) -> tuple[EvalRun, list[CaseResult]]:
    cases = load_cases(subset)
    conversations: dict[str, uuid.UUID] = {}
    results: list[CaseResult] = []
    for case in cases:
        started = time.monotonic()
        try:
            response = await run_case(deps, case, conversations.get(case.followup_of or ""))
        except Exception as exc:  # a crash is a failed case, not a failed run
            results.append(CaseResult(case, False, [f"error: {type(exc).__name__}: {exc}"]))
            await session.rollback()
            continue
        conversations[case.id] = response.conversation_id
        result = score_case(case, response)
        if use_judge and response.claims:
            verdicts = await judge_claims(
                deps.llm, deps.settings.llm_model_judge, response.claims, response.evidence
            )
            unsupported = [
                c.text for c, ok in zip(response.claims, verdicts, strict=True) if not ok
            ]
            result.details["judge_unsupported"] = unsupported
            if unsupported:
                result.passed = False
                result.failures.append(f"judge: {len(unsupported)} unsupported claim(s)")
        result.details["seconds"] = round(time.monotonic() - started, 2)
        results.append(result)

    by_category: dict[str, list[bool]] = defaultdict(list)
    for r in results:
        by_category[r.case.category].append(r.passed)
    summary = {k: {"passed": sum(v), "total": len(v)} for k, v in sorted(by_category.items())}
    _, version = load_prompt(
        "generate",
        language="",
        audience="",
        forbidden_actions="",
        unpublished_topics="",
        guardrails="",
    )
    run = EvalRun(
        prompt_version=version,
        model=deps.settings.llm_model_generate,
        subset=subset,
        total=len(results),
        passed=sum(r.passed for r in results),
        summary=summary,
    )
    run.results = [
        EvalResult(
            case_id=r.case.id,
            category=r.case.category,
            passed=r.passed,
            details={**r.details, "failures": r.failures},
        )
        for r in results
    ]
    session.add(run)
    await session.commit()
    return run, results


def evidence_text(evidence: list[Evidence], ids: list[str]) -> str:
    by_id = {e.id: e for e in evidence}
    return "\n".join(f"[{i}] {by_id[i].value}" for i in ids if i in by_id)
