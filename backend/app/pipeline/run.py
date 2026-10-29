"""The question pipeline: understand → resolve → policy → evidence → generate → verify → trace.

The model labels the question and phrases the answer; every decision about *what* may be said
(clarify, refuse, which facts) is made here in code.
"""

import re
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

from app.db.models import Conversation, Message, TraceRow
from app.domain import (
    Capability,
    Channel,
    ChatRequest,
    ChatResponse,
    Claim,
    Evidence,
    Lang,
    Scorecard,
    ToolCall,
    Trace,
)
from app.gaps.store import record_gap
from app.llm.client import Usage
from app.pipeline import messages
from app.pipeline.deps import Deps
from app.pipeline.evidence import EvidenceBundle, gather_evidence
from app.pipeline.generate import generate
from app.pipeline.policy import PolicyDecision, policy
from app.pipeline.understand import Understanding, understand
from app.pipeline.verify import compose_answer, decide_capability, verify
from app.retrieval.normalize import normalize
from app.retrieval.resolve import GENERIC_MENTIONS, Candidate, resolve

EventSink = Callable[[str, dict[str, Any]], Awaitable[None]]
JobFitHandler = Callable[["RunContext"], Awaitable[ChatResponse]]

HISTORY_MESSAGES = 6
MAX_CLARIFY_OPTIONS = 6
MAX_TARGETS_PER_MENTION = 3
_ORDINALS: list[set[str]] = [
    {"first", "1", "1st", "اولی", "اول", "یکمی"},
    {"second", "2", "2nd", "دومی", "دوم"},
    {"third", "3", "3rd", "سومی", "سوم"},
    {"fourth", "4", "4th", "چهارمی", "چهارم"},
    {"fifth", "5", "5th", "پنجمی", "پنجم"},
]
STAGES = ("understand", "resolve", "policy", "evidence", "generate", "verify")


@dataclass
class RunContext:
    """State shared by the chat pipeline and the job-fit pipeline for one request."""

    req: ChatRequest
    channel: Channel
    deps: Deps
    emit: EventSink
    started: float
    conversation: Conversation
    history: list[dict[str, str]]
    u: Understanding
    usage: Usage = field(default_factory=Usage)
    prompt_version: str = ""


async def _noop(_event: str, _data: dict[str, Any]) -> None:
    return None


def match_pending(text: str, options: list[dict[str, str]]) -> int | None:
    """Which clarify option a follow-up picks: by name ("Kanban") or ordinal ("second", "دومی")."""
    wanted = normalize(text)
    for index, option in enumerate(options):
        label = normalize(option["label"])
        if label and (label in wanted or (len(wanted) >= 3 and wanted in label)):
            return index
    tokens = set(re.findall(r"\w+", wanted))
    for index, words in enumerate(_ORDINALS):
        if index < len(options) and tokens & {normalize(w) for w in words}:
            return index
    return None


async def _conversation(deps: Deps, req: ChatRequest) -> Conversation:
    if req.conversation_id is not None:
        found = await deps.session.get(Conversation, req.conversation_id)
        if found is not None:
            return found
    conversation = Conversation(id=uuid.uuid4(), audience=req.audience)
    deps.session.add(conversation)
    await deps.session.flush()
    return conversation


async def _history(
    deps: Deps, conversation: Conversation
) -> tuple[list[dict[str, str]], dict[str, Any] | None]:
    rows = (
        await deps.session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .limit(HISTORY_MESSAGES)
        )
    ).all()
    rows = list(reversed(rows))
    history = [{"role": m.role, "content": m.content} for m in rows]
    pending = rows[-1].pending_clarify if rows and rows[-1].role == "assistant" else None
    return history, pending


@dataclass
class _Resolution:
    targets: list[Candidate] = field(default_factory=list)
    clarify: list[Candidate] = field(default_factory=list)
    unknown: str | None = None


async def _resolve_targets(deps: Deps, u: Understanding) -> _Resolution:
    if u.intent == "project_summary":
        mentions = u.entities or ["project"]
        found: dict[str, Candidate] = {}
        for mention in mentions:
            for candidate in await resolve(deps.session, deps.llm, mention, "project"):
                found[candidate.entity_id] = candidate
        candidates = sorted(found.values(), key=lambda c: c.label.lower())
        if len(candidates) == 1:
            return _Resolution(targets=candidates)
        if candidates:
            return _Resolution(clarify=candidates)
        generic = {normalize(m) for m in GENERIC_MENTIONS["project"]}
        named = [m for m in mentions if normalize(m) not in generic]
        return _Resolution(unknown=named[0] if named else None)

    # Outside project summaries a name may legitimately match a few entities at once (the Zerang
    # project and the Zerang job): read them all. Broad matches are left to hybrid search.
    targets: dict[str, Candidate] = {}
    for mention in u.entities:
        candidates = await resolve(deps.session, deps.llm, mention, None)
        if len(candidates) <= MAX_TARGETS_PER_MENTION:
            targets.update((c.entity_id, c) for c in candidates)
    return _Resolution(targets=list(targets.values()))


async def finish(
    ctx: RunContext,
    *,
    answer: str,
    capability: Capability,
    claims: list[Claim] | None = None,
    bundle: EvidenceBundle | None = None,
    missing: list[str] | None = None,
    clarify: list[Candidate] | None = None,
    scorecard: Scorecard | None = None,
    extra_tools: list[ToolCall] | None = None,
) -> ChatResponse:
    """Persist the turn and its trace, and build the response."""
    deps, u = ctx.deps, ctx.u
    bundle = bundle or EvidenceBundle()
    trace = Trace(
        id=uuid.uuid4(),
        question=ctx.req.message,
        language=u.language,
        intent=u.intent,
        audience=ctx.req.audience,
        channel=ctx.channel,
        fields_read=bundle.fields_read,
        tools_called=[*bundle.tool_calls, *(extra_tools or [])],
        capability=capability,
        answer=answer,
        missing=missing or [],
        latency_ms=int((time.monotonic() - ctx.started) * 1000),
        tokens_in=ctx.usage.tokens_in,
        tokens_out=ctx.usage.tokens_out,
        prompt_version=ctx.prompt_version,
    )
    pending = None
    if clarify:
        pending = {
            "intent": u.intent,
            "options": [
                {"entity_id": c.entity_id, "kind": c.kind, "label": c.label} for c in clarify
            ],
        }
    deps.session.add_all(
        [
            Message(conversation_id=ctx.conversation.id, role="user", content=ctx.req.message),
            Message(
                conversation_id=ctx.conversation.id,
                role="assistant",
                content=answer,
                pending_clarify=pending,
                trace_id=trace.id,
            ),
            TraceRow(
                id=trace.id,
                conversation_id=ctx.conversation.id,
                question=ctx.req.message,
                capability=capability,
                intent=u.intent,
                channel=ctx.channel,
                language=u.language,
                latency_ms=trace.latency_ms,
                data=trace.model_dump(mode="json"),
            ),
        ]
    )
    await deps.session.commit()
    return ChatResponse(
        conversation_id=ctx.conversation.id,
        answer=answer,
        capability=capability,
        claims=claims or [],
        evidence=bundle.evidence,
        scorecard=scorecard,
        clarify_options=[c.label for c in clarify] if clarify else None,
        trace=trace,
    )


def clarify_text(
    candidates: list[Candidate], rank: dict[str, int], intent: str, language: Lang
) -> tuple[str, list[Candidate]]:
    """One follow-up question. Featured items come first; a truncated list says "for example"
    so it never reads as the complete set."""
    ordered = sorted(
        candidates,
        key=lambda c: (rank.get(c.entity_id.split(":", 1)[1], 10_000), c.label.lower()),
    )
    shown = ordered[:MAX_CLARIFY_OPTIONS]
    labels = [c.label for c in shown]
    if intent == "project_summary":
        truncated = len(ordered) > len(shown)
        key = "clarify_project_examples" if truncated else "clarify_project"
        joined = (
            ("، " if language == "fa" else ", ").join(labels)
            if truncated
            else (messages.join_options(labels, language))
        )
    else:
        key, joined = "clarify_entity", messages.join_options(labels, language)
    return messages.message(key, language, options=joined), shown


def _featured_rank(deps: Deps) -> dict[str, int]:
    featured = [p for p in deps.record.projects if p.featured]
    featured.sort(key=lambda p: (0, p.order) if p.order else (1, 0))
    return {p.id: i for i, p in enumerate(featured)}


async def _clarify(ctx: RunContext, options: list[Candidate]) -> ChatResponse:
    answer, shown = clarify_text(options, _featured_rank(ctx.deps), ctx.u.intent, ctx.u.language)
    return await finish(ctx, answer=answer, capability="clarify", clarify=shown)


async def run_chat(
    req: ChatRequest,
    channel: Channel,
    deps: Deps,
    on_event: EventSink | None = None,
    job_fit: JobFitHandler | None = None,
) -> ChatResponse:
    emit = on_event or _noop
    started = time.monotonic()
    conversation = await _conversation(deps, req)
    history, pending = await _history(deps, conversation)

    await emit("stage", {"name": "understand", "status": "start"})
    u, usage, version = await understand(deps.llm, deps.settings, req.message, history)
    await emit("stage", {"name": "understand", "status": "done"})
    ctx = RunContext(req, channel, deps, emit, started, conversation, history, u, usage, version)

    await emit("stage", {"name": "resolve", "status": "start"})
    targets: list[Candidate] = []
    if pending:
        picked = match_pending(req.message, pending["options"])
        if picked is not None:
            option = pending["options"][picked]
            targets = [Candidate(option["entity_id"], option["kind"], option["label"], 1.0)]
            ctx.u = u = u.model_copy(update={"intent": pending["intent"]})
    await emit("stage", {"name": "resolve", "status": "done"})

    await emit("stage", {"name": "policy", "status": "start"})
    decision = await policy(deps.llm, u, deps.record)
    await emit("stage", {"name": "policy", "status": "done"})
    if decision.capability == "refuse_action":
        action = messages.action_name(decision.reason or "", u.language)
        return await finish(
            ctx,
            answer=messages.message("refuse_action", u.language, action=action),
            capability="refuse_action",
        )
    if decision.capability == "refuse_unpublished":
        return await finish(
            ctx,
            answer=messages.message("refuse_topic", u.language, topic=decision.reason or ""),
            capability="refuse_unpublished",
        )
    if decision.capability == "out_of_scope":
        return await finish(
            ctx, answer=messages.message("out_of_scope", u.language), capability="out_of_scope"
        )
    if u.intent == "smalltalk":
        return await finish(
            ctx, answer=messages.message("smalltalk", u.language), capability="clarify"
        )
    if u.intent == "job_fit" or req.job_url or req.job_text:
        if job_fit is not None and (req.job_url or req.job_text):
            return await job_fit(ctx)
        return await finish(
            ctx, answer=messages.message("job_needed", u.language), capability="clarify"
        )

    if not targets:
        resolution = await _resolve_targets(deps, u)
        if resolution.clarify:
            return await _clarify(ctx, resolution.clarify)
        if resolution.unknown:
            missing = [resolution.unknown]
            if channel != "eval":
                await record_gap(deps.session, deps.llm, req.message, u.language, "unknown entity")
            return await finish(
                ctx,
                answer=compose_answer([], missing, u.language),
                capability="refuse_unpublished",
                missing=missing,
            )
        targets = resolution.targets

    await emit("stage", {"name": "evidence", "status": "start"})

    async def on_evidence(item: Evidence) -> None:
        await emit("evidence", item.model_dump(mode="json"))

    bundle = await gather_evidence(deps, u, targets, req.audience, on_evidence)
    await emit("stage", {"name": "evidence", "status": "done"})

    await emit("stage", {"name": "generate", "status": "start"})
    out, gen_usage, ctx.prompt_version = await generate(
        deps.llm, deps.settings, u, req.audience, bundle.evidence, history, deps.record.limits
    )
    ctx.usage += gen_usage
    await emit("stage", {"name": "generate", "status": "done"})

    await emit("stage", {"name": "verify", "status": "start"})
    result = verify(out, bundle.evidence)
    if result.needs_regen:
        dropped = "; ".join(c.text for c in result.dropped)
        out, gen_usage, ctx.prompt_version = await generate(
            deps.llm,
            deps.settings,
            u,
            req.audience,
            bundle.evidence,
            history,
            deps.record.limits,
            feedback=f"these claims cited no trusted evidence and were removed: {dropped}",
        )
        ctx.usage += gen_usage
        result = verify(out, bundle.evidence)
    capability = decide_capability(PolicyDecision(None, None), result.claims_kept, bundle.evidence)
    answer = compose_answer(result.claims_kept, out.missing, u.language)
    await emit("stage", {"name": "verify", "status": "done"})

    if channel != "eval" and (capability == "refuse_unpublished" or out.missing):
        reason = "no supporting evidence" if capability == "refuse_unpublished" else "partial"
        await record_gap(deps.session, deps.llm, req.message, u.language, reason)
    return await finish(
        ctx,
        answer=answer,
        capability=capability,
        claims=result.claims_kept,
        bundle=bundle,
        missing=out.missing,
    )
