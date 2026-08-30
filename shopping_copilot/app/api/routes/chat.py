from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_orchestration_service, get_session_service
from app.services.orchestration.orchestration_service import OrchestrationService
from app.services.sessions.sessions_service import SessionService

class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)

class ChatResponse(BaseModel):
    session_id: str
    message: str | None = None
    intent: str | None = None
    response: str | None = None
    recommendations: list[dict] = Field(default_factory=list)
    status: str = "ok"



router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    orchestration: OrchestrationService = Depends(get_orchestration_service),
    sessions: SessionService = Depends(get_session_service),
) -> ChatResponse:
    if sessions.exists(request.session_id):
        ok, reason = sessions.check_limits(request.session_id)
        if not ok:
            raise HTTPException(status_code=410, detail=f"session_unavailable: {reason}")

    try:
        turn = await orchestration.handle_turn(
            session_id=request.session_id,
            message=request.message,
        )
    except Exception:
        raise HTTPException(status_code=500, detail="something went wrong processing that message")

    payload = turn.get("result", {})

    return ChatResponse(
        session_id=turn["session_id"],
        intent=turn.get("intent"),
        message=payload.get("message"),
        response=payload.get("message"),
        recommendations=payload.get("products", []),
        status=payload.get("status", "ok"),
    )