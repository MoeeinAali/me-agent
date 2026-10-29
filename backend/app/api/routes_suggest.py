from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_record
from app.domain import Audience, Lang
from app.record.schema import Record
from app.suggestions import suggestions

router = APIRouter(prefix="/v1", tags=["meta"])


@router.get("/suggestions")
async def get_suggestions(
    record: Annotated[Record, Depends(get_record)],
    audience: Audience = "general",
    lang: Lang = "en",
) -> dict[str, list[str]]:
    return {"suggestions": await suggestions(audience, lang, record)}
