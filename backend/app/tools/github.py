"""Live evidence from GitHub, limited to repositories and orgs listed in the record.

Repository metadata, languages, and commits are trusted facts about the repo; the README is
written by anyone with push access, so it is returned as untrusted text.
"""

import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

import httpx

from app.domain import Evidence, Proof, ToolCall
from app.record.schema import Record
from app.tools.base import CircuitBreaker, CircuitOpen, ToolResult, elapsed_ms
from app.tools.cache import Cache

API = "https://api.github.com"
TTL_SECONDS = 6 * 3600
README_CHARS = 2000
_breaker = CircuitBreaker()


def allowed_repos(record: Record) -> set[str]:
    allowed = {p.github_repo.lower() for p in record.projects if p.github_repo}
    allowed |= {f"org:{p.github_org.lower()}" for p in record.projects if p.github_org}
    return allowed


class GitHubError(RuntimeError):
    pass


class GitHubTool:
    def __init__(
        self,
        client: httpx.AsyncClient,
        cache: Cache,
        allowed: set[str],
        token: str | None,
        breaker: CircuitBreaker = _breaker,
    ) -> None:
        self._client = client
        self._cache = cache
        self._allowed = allowed
        self._breaker = breaker
        self._headers = {
            "accept": "application/vnd.github+json",
            "x-github-api-version": "2022-11-28",
        }
        if token:
            self._headers["authorization"] = f"Bearer {token}"

    async def repo(self, repo: str) -> ToolResult:
        if repo.lower() not in self._allowed:
            raise ValueError(f"repository {repo} is not in the record")
        return await self._run(
            f"github.repo:{repo}",
            f"github:repo:{repo.lower()}",
            lambda: self._fetch_repo(repo),
            lambda p: self._repo_evidence(repo, p),
        )

    async def org(self, org: str) -> ToolResult:
        if f"org:{org.lower()}" not in self._allowed:
            raise ValueError(f"organization {org} is not in the record")
        return await self._run(
            f"github.org:{org}",
            f"github:org:{org.lower()}",
            lambda: self._fetch_org(org),
            lambda p: self._org_evidence(org, p),
        )

    async def _run(
        self,
        name: str,
        key: str,
        fetch: Callable[[], Awaitable[dict[str, Any]]],
        to_evidence: Callable[[dict[str, Any]], list[Evidence]],
    ) -> ToolResult:
        start = time.monotonic()
        cached_payload = await self._cache.get(key)
        cached = cached_payload is not None
        payload: dict[str, Any]
        if cached_payload is not None:
            payload = cached_payload
        else:
            try:
                payload = await self._breaker.call(fetch)
            except (GitHubError, CircuitOpen, httpx.HTTPError) as exc:
                return ToolResult(
                    False,
                    [],
                    ToolCall(name=name, ok=False, latency_ms=elapsed_ms(start), detail=str(exc)),
                )
            await self._cache.set(key, "github", payload, TTL_SECONDS)
        return ToolResult(
            True,
            to_evidence(payload),
            ToolCall(
                name=name, ok=True, latency_ms=elapsed_ms(start), detail="cache" if cached else None
            ),
        )

    async def _get(self, path: str, **params: Any) -> httpx.Response:
        response = await self._client.get(
            f"{API}{path}", headers=self._headers, params=params, timeout=5.0
        )
        if (
            response.status_code in (403, 429)
            and response.headers.get("x-ratelimit-remaining") == "0"
        ):
            raise GitHubError("GitHub rate limit reached")
        if response.status_code >= 400:
            raise GitHubError(f"GitHub returned HTTP {response.status_code} for {path}")
        return response

    async def _fetch_repo(self, repo: str) -> dict[str, Any]:
        meta = (await self._get(f"/repos/{repo}")).json()
        languages = (await self._get(f"/repos/{repo}/languages")).json()
        commits = (await self._get(f"/repos/{repo}/commits", per_page=3)).json()
        try:
            readme = (
                await self._client.get(
                    f"{API}/repos/{repo}/readme",
                    headers={**self._headers, "accept": "application/vnd.github.raw+json"},
                    timeout=5.0,
                )
            ).text[:README_CHARS]
        except httpx.HTTPError:
            readme = ""
        return {"meta": meta, "languages": languages, "commits": commits, "readme": readme}

    async def _fetch_org(self, org: str) -> dict[str, Any]:
        repos = (await self._get(f"/orgs/{org}/repos", per_page=30, sort="pushed")).json()
        return {"repos": repos}

    @staticmethod
    def _repo_evidence(repo: str, payload: dict[str, Any]) -> list[Evidence]:
        meta, url = payload["meta"], payload["meta"].get("html_url", f"https://github.com/{repo}")
        now = datetime.now().astimezone()
        proof = Proof(type="github_repo", url=url, status="up", checked_at=now)
        base = f"github[{repo}]"
        items = [
            Evidence(
                id="",
                path=f"{base}.summary",
                source="github",
                trusted=True,
                proof=proof,
                value=f"{repo}: {meta.get('description') or 'no description'}; "
                f"created {meta.get('created_at', '')[:10]}, "
                f"last push {meta.get('pushed_at', '')[:10]}, "
                f"{meta.get('stargazers_count', 0)} stars",
            )
        ]
        languages: dict[str, int] = payload["languages"]
        total = sum(languages.values())
        if total:
            share = ", ".join(
                f"{name} {round(100 * size / total)}%"
                for name, size in sorted(languages.items(), key=lambda kv: -kv[1])
            )
            items.append(
                Evidence(
                    id="",
                    path=f"{base}.languages",
                    value=share,
                    source="github",
                    trusted=True,
                    proof=proof,
                )
            )
        if payload["commits"]:
            commit = payload["commits"][0]
            items.append(
                Evidence(
                    id="",
                    path=f"{base}.latest_commit",
                    source="github",
                    trusted=True,
                    value=f"{commit['commit']['author']['date'][:10]}: "
                    f"{commit['commit']['message'].splitlines()[0]}",
                    proof=Proof(
                        type="github_commit", url=commit["html_url"], status="up", checked_at=now
                    ),
                )
            )
        if payload["readme"]:
            items.append(
                Evidence(
                    id="",
                    path=f"{base}.readme",
                    value=payload["readme"],
                    source="github",
                    trusted=False,
                    proof=proof,
                )
            )
        return items

    @staticmethod
    def _org_evidence(org: str, payload: dict[str, Any]) -> list[Evidence]:
        repos = payload["repos"]
        if not repos:
            return []
        listing = "; ".join(
            f"{r['name']} ({r.get('language') or 'n/a'}, "
            f"last push {(r.get('pushed_at') or '')[:10]})"
            for r in repos
        )
        proof = Proof(
            type="github_repo",
            url=f"https://github.com/{org}",
            status="up",
            checked_at=datetime.now().astimezone(),
        )
        return [
            Evidence(
                id="",
                path=f"github[{org}].repos",
                value=f"{org} repositories: {listing}",
                source="github",
                trusted=True,
                proof=proof,
            )
        ]
