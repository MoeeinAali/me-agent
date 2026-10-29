"""Parse the LaTeX résumé (``cv/sections/*.tex``) into plain dictionaries.

The résumé uses a small set of custom macros (``\\resumeItem{..}``,
``\\resumeProjectHeading{..}{..}`` ...). We parse balanced brace arguments instead of
regex-matching whole macros, because arguments nest (``\\textbf{..}`` inside ``\\resumeItem{..}``).
"""

import re
from collections.abc import Iterator
from typing import Any

_MONTHS = {
    m: i
    for i, names in enumerate(
        [
            ("jan", "january"),
            ("feb", "february"),
            ("mar", "march"),
            ("apr", "april"),
            ("may",),
            ("jun", "june"),
            ("jul", "july"),
            ("aug", "august"),
            ("sep", "sept", "september"),
            ("oct", "october"),
            ("nov", "november"),
            ("dec", "december"),
        ],
        start=1,
    )
    for m in names
}

_COMMENT = re.compile(r"(?<!\\)%.*$", re.MULTILINE)


def strip_comments(tex: str) -> str:
    return _COMMENT.sub("", tex)


def _read_group(tex: str, i: int) -> tuple[str, int] | None:
    """Read one ``{...}`` group starting at or after ``i`` (whitespace allowed before it)."""
    while i < len(tex) and tex[i].isspace():
        i += 1
    if i >= len(tex) or tex[i] != "{":
        return None
    depth, start = 0, i + 1
    while i < len(tex):
        ch = tex[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return tex[start:i], i + 1
        i += 1
    return None


def macro_args(tex: str, name: str, n: int) -> Iterator[tuple[list[str], int, int]]:
    """Yield ``(args, start, end)`` for each ``\\name`` followed by ``n`` brace groups."""
    pattern = re.compile(rf"\\{re.escape(name)}(?![A-Za-z])")
    for match in pattern.finditer(tex):
        args: list[str] = []
        pos = match.end()
        for _ in range(n):
            group = _read_group(tex, pos)
            if group is None:
                break
            args.append(group[0])
            pos = group[1]
        if len(args) == n:
            yield args, match.start(), pos


def clean(tex: str) -> str:
    """Reduce inline TeX to plain text."""
    text = re.sub(r"\$\^\{(\w+)\}\$", r"\1", tex)
    text = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\(?:textbf|textit|emph|underline|small)\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\fa[A-Za-z]+\\?", "", text)
    text = text.replace(r"\%", "%").replace(r"\&", "&").replace(r"\$", "$")
    text = text.replace("---", "—").replace("--", "–").replace("$|$", "|")
    text = re.sub(r"\\[A-Za-z]+\s?", "", text)
    text = text.replace("{", "").replace("}", "").replace("’", "'")
    return re.sub(r"\s+", " ", text).strip()


def parse_month(text: str) -> str | None:
    """``"March 2026"`` → ``"2026-03"``; anything without a month and year → ``None``."""
    match = re.search(r"([A-Za-z]+)\.?\s+(\d{4})", text)
    if not match or match.group(1).lower() not in _MONTHS:
        return None
    return f"{match.group(2)}-{_MONTHS[match.group(1).lower()]:02d}"


def _split_range(text: str) -> tuple[str | None, str | None]:
    parts = re.split(r"\s*(?:--|–|-)\s*", clean(text), maxsplit=1)
    start = parse_month(parts[0])
    end = parse_month(parts[1]) if len(parts) > 1 else None
    return start, end


def parse_courses(tex: str) -> list[dict[str, str]]:
    rows = re.findall(
        r"\\textbf\{([^}]*)\}\s*&\s*\\textit\{([^}]*)\}\s*&\s*([^\\\n]+?)\s*\\\\",
        strip_comments(tex),
    )
    return [{"title": clean(t), "instructor": clean(i), "grade": g.strip()} for t, i, g in rows]


def parse_honors(tex: str) -> list[dict[str, str]]:
    tex = strip_comments(tex)
    honors = []
    headings = list(macro_args(tex, "resumeSubSubheading", 2))
    for idx, (args, _, end) in enumerate(headings):
        stop = headings[idx + 1][1] if idx + 1 < len(headings) else len(tex)
        items = [clean(a[0]) for a, _, _ in macro_args(tex[end:stop], "resumeItem", 1)]
        honors.append({"title": clean(args[0]), "year": clean(args[1]), "detail": " ".join(items)})
    return honors


def parse_languages(tex: str) -> list[dict[str, str]]:
    pairs = re.findall(r"\\textbf\{([^}]*)\}\{:\s*([^}]*)\}", strip_comments(tex))
    return [{"name": clean(n), "level": clean(level)} for n, level in pairs]


def parse_contact(tex: str) -> dict[str, str]:
    tex = strip_comments(tex)
    hrefs = re.findall(r"\\href\{([^}]*)\}", tex)
    contact: dict[str, str] = {}
    for href in hrefs:
        if href.startswith("mailto:"):
            contact["email"] = href.removeprefix("mailto:")
        elif href.startswith("tel:"):
            contact["phone"] = href.removeprefix("tel:")
        elif "github.com" in href:
            contact["github"] = href
        elif "linkedin.com" in href:
            contact["linkedin"] = href.rstrip("/")
        elif "maps" not in href:
            contact.setdefault("website", href.rstrip("/"))
    return contact


def _links(heading: str) -> dict[str, str | None]:
    found = dict(
        (label.lower(), url) for url, label in re.findall(r"\\href\{([^}]*)\}\{([^}]*)\}", heading)
    )
    return {"github": found.get("github"), "live": found.get("website")}


def parse_projects(tex: str) -> list[dict[str, Any]]:
    tex = strip_comments(tex)
    headings = list(macro_args(tex, "resumeProjectHeading", 2))
    projects = []
    for idx, (args, _, end) in enumerate(headings):
        stop = headings[idx + 1][1] if idx + 1 < len(headings) else len(tex)
        head = args[0]
        title_match = re.search(r"\\textbf\{([^}]*)\}", head)
        tech_match = re.search(r"\\emph\{([^}]*)\}", head)
        projects.append(
            {
                "title": clean(title_match.group(1)) if title_match else clean(head),
                "date": parse_month(clean(args[1])),
                "tech": [t.strip() for t in tech_match.group(1).split(",")] if tech_match else [],
                **_links(head),
                "bullets": [clean(a[0]) for a, _, _ in macro_args(tex[end:stop], "resumeItem", 1)],
            }
        )
    return projects


def parse_experience(tex: str) -> list[dict[str, Any]]:
    """One entry per role: ``{company, role, start, end, bullets}`` (dates as ``YYYY-MM``)."""
    tex = strip_comments(tex)
    companies = [
        (start, clean(args[0])) for args, start, _ in macro_args(tex, "resumeSubheading", 2)
    ]
    roles_raw = list(macro_args(tex, "resumeSubSubheading", 2))
    roles = []
    for idx, (args, start, end) in enumerate(roles_raw):
        stop = roles_raw[idx + 1][1] if idx + 1 < len(roles_raw) else len(tex)
        nxt_company = next((s for s, _ in companies if s > start), len(tex))
        company = next((name for s, name in reversed(companies) if s < start), "")
        role_start, role_end = _split_range(args[1])
        roles.append(
            {
                "company": company.removesuffix(" Company"),
                "role": clean(args[0].split("$|$")[0]),
                "start": role_start,
                "end": role_end,
                "bullets": [
                    clean(a[0])
                    for a, _, _ in macro_args(tex[end : min(stop, nxt_company)], "resumeItem", 1)
                ],
            }
        )
    return roles
