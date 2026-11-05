"""Traces in the assignment's report format (Question / Intent / Fields read / Capability /
Answer), exported from the traces table."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TraceRow
from app.text import indented, one_line, printable


def format_trace(data: dict[str, Any]) -> str:
    return printable(_format(data))


def _format(data: dict[str, Any]) -> str:
    fields = ", ".join(one_line(f) for f in data["fields_read"]) or "(none)"
    lines = [
        f"Question: {one_line(data['question'])}",
        f"Intent: {one_line(data['intent'])}",
        f"Fields read: {fields}",
        f"Capability: {one_line(data['capability'])}",
    ]
    if data.get("tools_called"):
        tools = ", ".join(
            f"{t['name']} ({'ok' if t['ok'] else 'failed'})" for t in data["tools_called"]
        )
        lines.append(f"Tools: {tools}")
    if data.get("missing"):
        lines.append(f"Missing: {', '.join(one_line(m) for m in data['missing'])}")
    answer = indented(data["answer"], "        ")
    lines.append(f"Answer: {answer}")
    if data.get("id"):
        lines.append(f"Trace id: {one_line(str(data['id']))}")
    return "\n".join(lines)


async def latest_traces(
    session: AsyncSession, capability: str | None, limit: int
) -> list[dict[str, Any]]:
    query = select(TraceRow).where(TraceRow.channel != "eval").order_by(TraceRow.created_at.desc())
    if capability:
        query = query.where(TraceRow.capability == capability)
    return [row.data for row in await session.scalars(query.limit(limit))]
