"""Everything one request's pipeline run needs, built per request by the API layer."""

from dataclasses import dataclass

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.llm.client import LLM
from app.record.schema import Record
from app.tools.cache import Cache


@dataclass
class Deps:
    session: AsyncSession
    llm: LLM
    record: Record
    settings: Settings
    http: httpx.AsyncClient
    cache: Cache

    @property
    def github_token(self) -> str | None:
        token = self.settings.github_token
        return token.get_secret_value() if token else None
