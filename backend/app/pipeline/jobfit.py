"""Job fit: a requirement-by-requirement scorecard with proofs.

The posting is untrusted data. Its requirements are extracted by the model, each one is checked
against Moeein's record (hybrid search), and the model's verdict on a requirement survives only
if it cites trusted record evidence. Coverage and the overall verdict are computed in code.
"""

import asyncio
import time
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import (
    Capability,
    ChatResponse,
    Evidence,
    JobSummary,
    Proof,
    Scorecard,
    ScorecardRow,
    ToolCall,
)
from app.jobs.base import JobPosting, resolve_job
from app.llm.client import LLM, Usage
from app.pipeline import messages
from app.pipeline.evidence import EvidenceCollector, search_kinds
from app.pipeline.generate import generate, render_evidence
from app.pipeline.run import JobFitHandler, RunContext, finish
from app.pipeline.verify import compose_answer, verify
from app.prompts.loader import load_prompt
from app.retrieval.hybrid import Hit, search

MAX_REQUIREMENTS = 15
JOBFIT_VALUE_CHARS = 600  # each requirement needs its own evidence; keep items short instead
JOBFIT_MAX_CHARS = MAX_REQUIREMENTS * 5 * (JOBFIT_VALUE_CHARS + 1) + 30_000
HITS_PER_REQUIREMENT = 5
WEIGHT = {"must": 2.0, "nice": 1.0}
CREDIT = {"matched": 1.0, "partial": 0.5, "no_evidence": 0.0}
STRONG_AT, PARTIAL_AT = 0.75, 0.40


class Requirement(BaseModel):
    requirement: str
    search_query: str = Field(description="Short English phrase to search Moeein's record with")
    category: Literal["must", "nice"]
    kind: Literal["skill", "experience", "education", "language", "other"]


class RequirementsOut(BaseModel):
    requirements: list[Requirement]


class RowJudgement(BaseModel):
    status: Literal["matched", "partial", "no_evidence"]
    evidence: list[str]


def coverage(rows: list[ScorecardRow]) -> float:
    total = sum(WEIGHT[r.category] for r in rows)
    if not total:
        return 0.0
    return sum(WEIGHT[r.category] * CREDIT[r.status] for r in rows) / total


def verdict(value: float) -> Literal["strong", "partial", "weak"]:
    if value >= STRONG_AT:
        return "strong"
    return "partial" if value >= PARTIAL_AT else "weak"


def coerce_judgement(judgement: RowJudgement, evidence: list[Evidence]) -> RowJudgement:
    """Keep only trusted, existing citations; a match with none left becomes no_evidence."""
    if judgement.status == "no_evidence":
        return RowJudgement(status="no_evidence", evidence=[])
    trusted = {e.id for e in evidence if e.trusted}
    cited = [eid for eid in judgement.evidence if eid in trusted]
    return RowJudgement(status=judgement.status if cited else "no_evidence", evidence=cited)


def _job_evidence(posting: JobPosting) -> list[Evidence]:
    source = "hrcando" if posting.source == "hrcando" else "job_text"
    proof = Proof(type="record", url=posting.url)
    facts = {
        "title": posting.title,
        "company": posting.company,
        "seniority": posting.seniority,
        "location": posting.location,
        "employment_type": posting.employment_type,
        "remote": None if posting.remote is None else ("yes" if posting.remote else "no"),
        "experience_years": None
        if posting.experience_years is None
        else str(posting.experience_years),
        "description": posting.description_text,
    }
    return [
        Evidence(id="", path=f"job.{name}", value=value, source=source, trusted=False, proof=proof)
        for name, value in facts.items()
        if value
    ]


async def extract_requirements(
    llm: LLM, model: str, posting: JobPosting
) -> tuple[list[Requirement], Usage]:
    system, _ = load_prompt("requirements")
    content = f"<untrusted>\n{posting.description_text}\n</untrusted>"
    out, usage = await llm.structured(
        model, system, [{"role": "user", "content": content}], RequirementsOut
    )
    return out.requirements[:MAX_REQUIREMENTS], usage


async def search_requirement(
    session: AsyncSession, llm: LLM, requirement: Requirement, kinds: set[str]
) -> list[Hit]:
    """The record is in English and Persian syllabus topics would dominate a Persian query, so
    retrieval uses the requirement's English rendering."""
    query = requirement.search_query.strip() or requirement.requirement
    return await search(session, llm, query, kinds=kinds, top_k=HITS_PER_REQUIREMENT)


async def evidence_for_requirements(
    session: AsyncSession, llm: LLM, requirements: list[Requirement], kinds: set[str]
) -> tuple[EvidenceCollector, list[list[Evidence]]]:
    collector = EvidenceCollector(max_chars=JOBFIT_MAX_CHARS, value_chars=JOBFIT_VALUE_CHARS)
    per_requirement: list[list[Evidence]] = []
    for requirement in requirements:
        hits = await search_requirement(session, llm, requirement, kinds)
        ids = {collector.add_record(h.path, h.text) or collector.id_for(h.path) for h in hits}
        per_requirement.append([e for e in collector.bundle.evidence if e.id in ids])
    return collector, per_requirement


async def judge_requirement(
    llm: LLM, model: str, requirement: Requirement, evidence: list[Evidence]
) -> tuple[RowJudgement, Usage]:
    system, _ = load_prompt("jobfit")
    content = (
        f"{render_evidence(evidence)}\n\nRequirement (from the posting):\n"
        f"<untrusted>{requirement.requirement}</untrusted>"
    )
    out, usage = await llm.structured(
        model, system, [{"role": "user", "content": content}], RowJudgement
    )
    return coerce_judgement(out, evidence), usage


async def run_job_fit(
    ctx: RunContext, posting: JobPosting, tool_calls: list[ToolCall]
) -> ChatResponse:
    deps, u = ctx.deps, ctx.u
    model = deps.settings.llm_model_generate
    await ctx.emit("stage", {"name": "evidence", "status": "start"})
    requirements, usage = await extract_requirements(deps.llm, model, posting)
    ctx.usage += usage

    kinds = search_kinds("job_fit", ctx.req.audience)
    collector, per_requirement = await evidence_for_requirements(
        deps.session, deps.llm, requirements, kinds
    )
    for item in _job_evidence(posting):
        collector.add(item, prefix="J")
    collector.bundle.tool_calls.extend(tool_calls)
    for item in collector.bundle.evidence:
        await ctx.emit("evidence", item.model_dump(mode="json"))
    await ctx.emit("stage", {"name": "evidence", "status": "done"})

    await ctx.emit("stage", {"name": "generate", "status": "start"})
    judged = await asyncio.gather(
        *(
            judge_requirement(deps.llm, model, r, ev)
            for r, ev in zip(requirements, per_requirement, strict=True)
        )
    )
    rows = []
    for requirement, (judgement, judge_usage) in zip(requirements, judged, strict=True):
        ctx.usage += judge_usage
        rows.append(
            ScorecardRow(
                requirement=requirement.requirement,
                category=requirement.category,
                kind=requirement.kind,
                status=judgement.status,
                evidence=judgement.evidence,
            )
        )
    score = coverage(rows)
    band = verdict(score)
    # The narrative sees only what the scorecard cited, plus the job facts (untrusted).
    cited = {eid for row in rows for eid in row.evidence}
    narrative_evidence = [
        e for e in collector.bundle.evidence if e.id in cited or e.id.startswith("J")
    ]
    out, gen_usage, ctx.prompt_version = await generate(
        deps.llm,
        deps.settings,
        u,
        ctx.req.audience,
        narrative_evidence,
        ctx.history,
        deps.record.limits,
    )
    ctx.usage += gen_usage
    await ctx.emit("stage", {"name": "generate", "status": "done"})

    await ctx.emit("stage", {"name": "verify", "status": "start"})
    result = verify(out, narrative_evidence)
    summary = messages.message(
        "jobfit_summary",
        u.language,
        title=posting.title or ("this role" if u.language == "en" else "این موقعیت"),
        pct=str(round(score * 100)),
        band=messages.VERDICT_NAMES[band][u.language],
        total=str(len(rows)),
        matched=str(sum(r.status == "matched" for r in rows)),
        partial=str(sum(r.status == "partial" for r in rows)),
        missing=str(sum(r.status == "no_evidence" for r in rows)),
    )
    narrative = compose_answer(result.claims_kept, [], u.language) if result.claims_kept else ""
    answer = f"{summary}\n\n{narrative}".strip()
    await ctx.emit("stage", {"name": "verify", "status": "done"})

    scorecard = Scorecard(
        job=JobSummary(
            source=posting.source, url=posting.url, company=posting.company, title=posting.title
        ),
        rows=rows,
        coverage=round(score, 3),
        verdict=band,
    )
    capability: Capability = (
        "answer_from_api" if posting.source == "hrcando" else "answer_from_record"
    )
    return await finish(
        ctx,
        answer=answer,
        capability=capability,
        claims=result.claims_kept,
        bundle=collector.bundle,
        scorecard=scorecard,
    )


def job_fit_handler(prepared: JobPosting | None = None) -> JobFitHandler:
    """The chat pipeline calls this when a job is attached; fetches the posting if needed."""

    async def handle(ctx: RunContext) -> ChatResponse:
        if prepared is not None:
            return await run_job_fit(ctx, prepared, [])
        start = time.monotonic()
        url = str(ctx.req.job_url) if ctx.req.job_url else None
        posting = await resolve_job(url=url, text=ctx.req.job_text if not url else None, pdf=None)
        calls = []
        if posting.source == "hrcando":
            calls.append(
                ToolCall(name="hrcando", ok=True, latency_ms=int((time.monotonic() - start) * 1000))
            )
        return await run_job_fit(ctx, posting, calls)

    return handle
