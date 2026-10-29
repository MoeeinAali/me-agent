from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_record
from app.db.session import get_session
from app.record.schema import Limits, Record, public_view

router = APIRouter()


@router.get("/v1/limits", response_model=Limits, tags=["meta"])
async def limits(record: Annotated[Record, Depends(get_record)]) -> Limits:
    """What the page will not do or discuss — shown on the page and given to the model."""
    return record.limits


@router.get("/v1/record", tags=["meta"])
async def public_record(record: Annotated[Record, Depends(get_record)]) -> dict[str, Any]:
    """The record's visitor-visible fields."""
    return public_view(record)


@router.get("/healthz", tags=["ops"])
async def healthz() -> dict[str, bool]:
    return {"ok": True}


@router.get("/readyz", tags=["ops"])
async def readyz(
    response: Response, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict[str, Any]:
    """Ready when the DB answers, migrations ran, and the record has been ingested."""
    try:
        version = await session.scalar(text("select version_num from alembic_version"))
        entities = await session.scalar(text("select count(*) from entities"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"ready": False, "reason": "database unavailable"}
    if not entities:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"ready": False, "reason": "record not ingested", "migration": version}
    return {"ready": True, "migration": version, "entities": entities}
