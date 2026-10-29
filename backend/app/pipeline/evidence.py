"""Step ④: collect the numbered evidence list the model may cite.

Structured reads of the resolved entities come first (highest precision), then hybrid search,
then live tool results (GitHub, link checks) for the resolved projects.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from app.domain import Audience, Evidence, Intent, Proof, ToolCall
from app.pipeline.deps import Deps
from app.pipeline.understand import Understanding
from app.retrieval.hybrid import read_fields, search
from app.retrieval.resolve import Candidate
from app.tools.base import ToolResult
from app.tools.github import GitHubTool, allowed_repos
from app.tools.linkcheck import LinkChecker

MAX_EVIDENCE_CHARS = 24_000  # ~6000 tokens
SEARCH_TOP_K = 10
SYLLABUS_URL = "https://docs.ce.sharif.ir/courses/{code}"

AUDIENCE_BOOSTS: dict[str, dict[str, float]] = {
    "recruiter": {"experience": 1.3, "project": 1.1},
    "tech_lead": {"project": 1.3},
    "professor": {"course": 1.4, "teaching": 1.3, "syllabus": 1.2},
    "general": {},
}
_ALL_KINDS = {
    "person",
    "contact",
    "education",
    "honor",
    "course",
    "teaching",
    "experience",
    "project",
    "service",
    "skills",
    "book",
    "faq",
}


@dataclass
class EvidenceBundle:
    evidence: list[Evidence] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def fields_read(self) -> list[str]:
        return [e.path for e in self.evidence]


def search_kinds(intent: Intent, audience: Audience) -> set[str]:
    """Syllabus topics are Persian and dominate Persian queries, so they are only searched when
    the academic angle matters."""
    kinds = set(_ALL_KINDS)
    if audience == "professor" or intent in {"reading_suggestion", "job_fit"}:
        kinds.add("syllabus")
    return kinds


def _proof_for(path: str) -> Proof:
    if path.startswith("syllabus["):
        code = path.split("[", 1)[1].split("]", 1)[0]
        return Proof(type="syllabus", url=SYLLABUS_URL.format(code=code))
    return Proof(type="record")


class _Collector:
    def __init__(self) -> None:
        self.bundle = EvidenceBundle()
        self._paths: set[str] = set()
        self._chars = 0

    def add(self, item: Evidence) -> bool:
        if item.path in self._paths or self._chars + len(item.value) > MAX_EVIDENCE_CHARS:
            return False
        self._paths.add(item.path)
        self._chars += len(item.value)
        self.bundle.evidence.append(
            item.model_copy(update={"id": f"E{len(self.bundle.evidence) + 1}"})
        )
        return True

    def add_record(self, path: str, value: str) -> bool:
        return self.add(
            Evidence(
                id="", path=path, value=value, source="record", trusted=True, proof=_proof_for(path)
            )
        )

    def add_tool(self, result: ToolResult) -> None:
        self.bundle.tool_calls.append(result.call)
        for item in result.evidence:
            self.add(item)


async def gather_evidence(
    deps: Deps,
    u: Understanding,
    targets: list[Candidate],
    audience: Audience,
    on_evidence: Callable[[Evidence], Awaitable[None]] | None = None,
) -> EvidenceBundle:
    collector = _Collector()

    for target in targets:
        for path, value in await read_fields(deps.session, target.entity_id):
            collector.add_record(path, value)

    if u.intent == "reading_suggestion":
        for book in deps.record.books:
            status = "has read" if book.status == "read" else "is currently reading"
            collector.add_record(
                f"books[{book.id}]", f"{book.title} by {book.author}; Moeein {status} it"
            )

    query = " ".join([u.asks_for, *u.entities]).strip() or u.message
    hits = await search(
        deps.session,
        deps.llm,
        query,
        kinds=search_kinds(u.intent, audience),
        top_k=SEARCH_TOP_K,
        boost_kinds=AUDIENCE_BOOSTS[audience],
    )
    for hit in hits:
        collector.add_record(hit.path, hit.text)

    await _live_tools(deps, targets, collector)

    if on_evidence:
        for item in collector.bundle.evidence:
            await on_evidence(item)
    return collector.bundle


async def _live_tools(deps: Deps, targets: list[Candidate], collector: _Collector) -> None:
    projects = {p.id: p for p in deps.record.projects}
    github = GitHubTool(deps.http, deps.cache, allowed_repos(deps.record), deps.github_token)
    links = LinkChecker(deps.http, deps.cache)
    # Sequential on purpose: the DB-backed cache shares this request's AsyncSession, which is not
    # safe for concurrent use. Results are cached, so most calls are cache hits.
    for target in targets:
        project = projects.get(target.entity_id.removeprefix("project:"))
        if target.kind != "project" or project is None:
            continue
        if project.github_repo:
            collector.add_tool(await github.repo(project.github_repo))
        elif project.github_org:
            collector.add_tool(await github.org(project.github_org))
        for name, url in (("live", project.links.live), ("marketplace", project.links.marketplace)):
            if url:
                collector.add_tool(
                    await links.check(str(url), f"projects[{project.id}].links.{name}")
                )
