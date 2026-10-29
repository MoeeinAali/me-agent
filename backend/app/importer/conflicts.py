"""Find facts the personal site and the résumé disagree on.

The site wins by default (it is more detailed and more recent), but nothing is silently dropped:
every disagreement is reported for Moeein to settle by hand.
"""

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Conflict:
    path: str
    site_value: str | None
    cv_value: str | None


def _norm_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]", "", title.lower())


def _norm_url(url: str | None) -> str | None:
    return url.lower().rstrip("/") if url else None


def diff_sources(site: dict[str, Any], cv: dict[str, Any]) -> list[Conflict]:
    conflicts: list[Conflict] = []
    cv_projects = {_norm_title(p["title"]): p for p in cv["projects"]}
    cv_companies = {_norm_title(e["company"]): e for e in cv["experience"]}

    for project in site["projects"]:
        pid, key = project["id"], _norm_title(project["title"])
        links = project.get("links", {})
        if key in cv_projects:
            other = cv_projects[key]
            if other.get("date") and other["date"] != project["date"]:
                conflicts.append(Conflict(f"projects[{pid}].date", project["date"], other["date"]))
            for link in ("github", "live"):
                mine, theirs = links.get(link), other.get(link)
                if mine and theirs and _norm_url(mine) != _norm_url(theirs):
                    conflicts.append(Conflict(f"projects[{pid}].links.{link}", mine, theirs))
        elif key in cv_companies:
            start = cv_companies[key].get("start")
            if start and start != project["date"]:
                conflicts.append(Conflict(f"projects[{pid}].date", project["date"], start))
    return conflicts


def render_markdown(conflicts: list[Conflict]) -> str:
    lines = [
        "# Site vs CV conflicts",
        "",
        "The record uses the **site** value. Fix `data/record.json` by hand where the CV is right.",
        "",
        "| Path | Site (used) | CV |",
        "|---|---|---|",
    ]
    lines += [f"| `{c.path}` | {c.site_value} | {c.cv_value} |" for c in conflicts]
    if not conflicts:
        lines.append("| — | no conflicts | — |")
    return "\n".join(lines) + "\n"
