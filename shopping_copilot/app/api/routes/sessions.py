from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_session_service

class SessionCreateRequest(BaseModel):
    session_id: str = Field(..., min_length=1)

class SessionResponse(BaseModel):
    session_id: str
    turn_count: int
    remaining_turns: int
    intent: str | None = None
    status: str



router = APIRouter(prefix="/sessions", tags=["Sessions"])

@router.post("", response_model=SessionResponse)
async def create_session(
    request: SessionCreateRequest,
    session_service=Depends(get_session_service),
) -> SessionResponse:

    session = session_service.create(request.session_id)

    return SessionResponse(
        session_id=session.session_id,
        turn_count=session.turn_count,
        intent=session.intent,
        status=session.status,
        remaining_turns=10,
    )

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

    return SessionResponse(
        session_id=session.session_id,
        turn_count=session.turn_count,
        intent=session.intent,
        status=session.status,
        remaining_turns=max(
            0,
            10 - session.turn_count,
        ),
    )