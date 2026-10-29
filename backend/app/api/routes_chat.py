from fastapi import APIRouter

from app.api.deps import DepsDep
from app.domain import ChatRequest, ChatResponse
from app.pipeline.run import run_chat

router = APIRouter(prefix="/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, deps: DepsDep) -> ChatResponse:
    """Ask one question. The response carries the answer, its claims and evidence, and the trace."""
    return await run_chat(req, "http", deps)
