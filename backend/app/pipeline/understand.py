"""Step ①: classify the visitor's message. The model only labels; code decides what happens."""

from pydantic import BaseModel, Field

from app.config import Settings
from app.domain import Intent, Lang
from app.llm.client import LLM, Usage
from app.prompts.loader import load_prompt
from app.record.schema import ForbiddenAction


class UnderstandOut(BaseModel):
    intent: Intent
    language: Lang
    entities: list[str]
    asks_for: str
    wants_action: ForbiddenAction | None


class Understanding(UnderstandOut):
    message: str = Field(default="", description="The visitor's message, verbatim")


async def understand(
    llm: LLM, settings: Settings, message: str, history: list[dict[str, str]]
) -> tuple[Understanding, Usage, str]:
    system, version = load_prompt("understand")
    out, usage = await llm.structured(
        settings.llm_model_understand,
        system,
        [*history[-6:], {"role": "user", "content": message}],
        UnderstandOut,
    )
    return Understanding(**out.model_dump(), message=message), usage, version
