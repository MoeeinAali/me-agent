"""Turn job-description HTML into readable text that keeps its structure."""

import html
import re

from selectolax.lexbor import LexborHTMLParser, LexborNode

_BLOCK_PREFIX = {"h1": "# ", "h2": "## ", "h3": "## ", "h4": "### ", "li": "- "}


def html_to_text(markup: str) -> str:
    root = LexborHTMLParser(f"<div>{markup}</div>").css_first("div")
    lines: list[str] = []

    def walk(node: LexborNode) -> None:
        for child in node.iter():
            tag = child.tag
            if tag in _BLOCK_PREFIX:
                text = _inline(child)
                if text:
                    if tag.startswith("h") and lines and lines[-1] != "":
                        lines.append("")
                    lines.append(_BLOCK_PREFIX[tag] + text)
            elif tag in {"p", "div"}:
                if _has_block_child(child):
                    walk(child)
                elif text := _inline(child):
                    lines.append(text)
                    lines.append("")
            elif tag in {"ul", "ol", "section", "article"}:
                walk(child)

    walk(root) if root else None
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _has_block_child(node: LexborNode) -> bool:
    # Not node.css_first(...): lexbor selectors also match the node itself and its ancestors.
    return any(c.tag in _BLOCK_PREFIX or c.tag in {"p", "ul", "ol"} for c in node.iter())


def _inline(node: LexborNode) -> str:
    text = html.unescape(node.text(deep=True, separator=" "))
    return re.sub(r"[ \t\r\n]+", " ", text).strip()
