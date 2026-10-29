from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.domain import Audience, Lang
from app.suggestions import suggestions

router = APIRouter(prefix="/v1", tags=["meta"])


@router.get("/suggestions")
async def get_suggestions(
    session: Annotated[AsyncSession, Depends(get_session)],
    audience: Audience = "general",
    lang: Lang = "en",
) -> dict[str, list[str]]:
    return {"suggestions": await suggestions(audience, lang, session)}
