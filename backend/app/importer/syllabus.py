"""Fetch Sharif BS-CE course facts into ``data/syllabus.json``.

Only the program table (code, title, credits, prerequisites) and each course's «ریز مواد» (topic
list) are kept. References and textbooks are never read: Moeein has not read them, and storing
them would let the agent imply he had. Usage, from ``backend/``::

    uv run python -m app.importer.syllabus
"""

import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

import httpx
from selectolax.lexbor import LexborHTMLParser as HTMLParser
from selectolax.lexbor import LexborNode as Node

from app.record.loader import load_record
from app.record.schema import CourseTaken, SyllabusCourse

BASE_URL = "https://docs.ce.sharif.ir"  # .edu serves a certificate for .ir only
DATA_DIR = Path(__file__).resolve().parents[3] / "data"

# English titles (as on the CV) → Persian titles as they appear on the program page.
TAKEN_TITLE_MAP: dict[str, str] = {
    "Data and Network Security": "امنیت داده و شبکه",
    "Agile Software Development": "ایجاد چابک نرم‌افزار",
    "Software Engineering": "مهندسی نرم‌افزار",
    "Artificial Intelligence": "هوش مصنوعی",
    "Introduction to Machine and Deep Learning": "یادگیری ماشین",
    "Database Design": "طراحی پایگاه داده‌ها",
    "System Analysis and Design": "تحلیل و طراحی سیستم‌ها",
    "Web Programming": "برنامه‌سازی وب",
    "Mobile Programming": "برنامه‌سازی موبایل",
    "Advanced Programming": "برنامه‌سازی پیشرفته",
}

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _text(node: Node) -> str:
    return re.sub(r"\s+", " ", node.text(deep=True)).strip()


def _norm_fa(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("ي", "ی").replace("ك", "ک")
    return re.sub(r"[\s‌]+", "", text)


def parse_program(html: str) -> list[dict[str, Any]]:
    courses: dict[str, dict[str, Any]] = {}
    for row in HTMLParser(html).css("tr"):
        cells = row.css("td")
        link = row.css_first('a[href^="/courses/"]')
        if len(cells) < 5 or link is None:
            continue
        code = (link.attributes.get("href") or "").rsplit("/", 1)[-1]
        prereq_text = _text(cells[4])
        courses.setdefault(
            code,
            {
                "code": code,
                "title_fa": _text(cells[2]),
                "credits": int(_text(cells[3]).translate(_DIGITS) or 0),
                "prereqs": []
                if prereq_text in {"", "–", "-"}
                else [p.strip() for p in re.split(r"[،,]", prereq_text) if p.strip()],
            },
        )
    return list(courses.values())


def parse_course(html: str) -> dict[str, list[str]]:
    """Topics from the «ریز مواد» section: one string per top-level item, subtopics joined."""
    tree = HTMLParser(html)
    heading = next((h for h in tree.css("h2, h3") if "ریز مواد" in _text(h)), None)
    if heading is None:
        return {"topics": []}
    section = heading.next
    while section is not None and section.tag != "div":
        section = section.next
    if section is None:
        return {"topics": []}
    topics: list[str] = []
    top_list = section.css_first("ul, ol")
    for item in top_list.iter() if top_list else []:
        if item.tag != "li":
            continue
        head = item.css_first("div.li")
        title = _text(head) if head else ""
        # Selectors on a node also match through its ancestors, so walk the nested list directly.
        nested = next((c for c in item.iter() if c.tag in {"ul", "ol"}), None)
        subs = [_text(d) for d in nested.css("div.li")] if nested else []
        topics.append(f"{title}: {'؛ '.join(subs)}" if subs else title)
    return {"topics": [t for t in topics if t]}


def match_taken(taken: list[CourseTaken], syllabus: list[SyllabusCourse]) -> dict[str, str | None]:
    by_title = {_norm_fa(c.title_fa): c.code for c in syllabus}
    return {
        course.id: by_title.get(_norm_fa(TAKEN_TITLE_MAP.get(course.title, ""))) for course in taken
    }


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=30, follow_redirects=True) as client:
        program = parse_program(client.get("/programs/bs-ce").text)
        syllabus: list[SyllabusCourse] = []
        for course in program:
            time.sleep(1)
            response = client.get(f"/courses/{course['code']}")
            topics = parse_course(response.text)["topics"] if response.is_success else []
            if not topics:
                print(f"skip {course['code']} {course['title_fa']}: no topics")
                continue
            english = {fa: en for en, fa in TAKEN_TITLE_MAP.items()}.get(course["title_fa"])
            syllabus.append(SyllabusCourse(**course, title_en=english, topics=topics))

    (DATA_DIR / "syllabus.json").write_text(
        json.dumps([c.model_dump() for c in syllabus], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"syllabus: {len(syllabus)} courses with topics")

    record_path = DATA_DIR / "record.json"
    record = load_record(record_path)
    codes = match_taken(record.courses_taken, syllabus)
    raw = json.loads(record_path.read_text(encoding="utf-8"))
    for course in raw["courses_taken"]:
        course["syllabus_code"] = codes[course["id"]]
        if codes[course["id"]] is None:
            print(f"warning: no syllabus match for taken course '{course['title']}'")
    record_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
