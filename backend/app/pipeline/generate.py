"""Step ⑤: phrase an answer from the evidence list, citing evidence ids for every claim."""

from html import escape

from pydantic import BaseModel

from app.config import Settings
from app.domain import Audience, Claim, Evidence
from app.llm.client import LLM, Usage
from app.pipeline.understand import Understanding
from app.prompts.loader import load_prompt
from app.record.schema import Limits

AUDIENCE_STYLE: dict[str, str] = {
    "recruiter": "a recruiter — lead with outcomes, roles, and fit; keep it brief and plain.",
    "tech_lead": "a team lead or CTO — focus on architecture, trade-offs, stack, and scale.",
    "professor": "a professor — focus on courses, syllabus topics, TA work, and academic projects.",
    "general": "a general visitor — balanced and brief.",
}
LANGUAGE_NAME = {"fa": "Persian (Farsi)", "en": "English"}


class GenerationOut(BaseModel):
    answer: str
    claims: list[Claim]
    missing: list[str]


def render_evidence(evidence: list[Evidence]) -> str:
    lines = ["<evidence>"]
    for item in evidence:
        line = (
            f'<item id="{item.id}" path="{escape(item.path)}" source="{item.source}">'
            f"{escape(item.value, quote=False)}</item>"
        )
        lines.append(line if item.trusted else f"<untrusted>{line}</untrusted>")
    lines.append("</evidence>")
    return "\n".join(lines)


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) or "- (none)"


async def generate(
    llm: LLM,
    settings: Settings,
    u: Understanding,
    audience: Audience,
    evidence: list[Evidence],
    history: list[dict[str, str]],
    limits: Limits,
    feedback: str | None = None,
) -> tuple[GenerationOut, Usage, str]:
    system, version = load_prompt(
        "generate",
        language=LANGUAGE_NAME[u.language],
        audience=AUDIENCE_STYLE[audience],
        forbidden_actions=_bullets(list(limits.forbidden_actions)),
        unpublished_topics=_bullets(limits.unpublished_topics),
        guardrails=_bullets(limits.guardrails),
    )
    content = f"{render_evidence(evidence)}\n\nVisitor question: {u.message}"
    if feedback:
        content += f"\n\nYour previous answer was rejected: {feedback}"
    out, usage = await llm.structured(
        settings.llm_model_generate,
        system,
        [*history[-6:], {"role": "user", "content": content}],
        GenerationOut,
    )
    return out, usage, version
