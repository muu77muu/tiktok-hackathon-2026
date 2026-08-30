from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_session_service

class SessionCreateRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    user_id: str | None = None

class SessionResponse(BaseModel):
    session_id: str
    user_id: str | None = None
    turn_count: int
    remaining_turns: int
    intent: str | None = None
    status: str

router = APIRouter(
    prefix="/sessions",
    tags=["Sessions"],
)

def _to_response(session, session_service) -> SessionResponse:
    remaining_turns = max(
        0,
        session_service.limits.max_turns - session.turn_count,
    )

    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        turn_count=session.turn_count,
        intent=session.intent,
        status=session.status,
        remaining_turns=remaining_turns,
    )

@router.post("", response_model=SessionResponse)
async def create_session(
    request: SessionCreateRequest,
    session_service=Depends(get_session_service),
) -> SessionResponse:
    if session_service.exists(request.session_id):
        raise HTTPException(
            status_code=409,
            detail="Session already exists",
        )

    session = session_service.create(
        session_id=request.session_id,
        user_id=request.user_id,
    )

    return _to_response(session, session_service)

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    session_service=Depends(get_session_service),
) -> SessionResponse:
    session = session_service.get(session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    return _to_response(session, session_service)
