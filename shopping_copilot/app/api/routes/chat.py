from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends

from ..dependencies import get_copilot_service
from app.services.copilot.copilot_service import CopilotService


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

@router.post("", response_model=ChatResponse,)
async def chat(
    request: ChatRequest,
    copilot: CopilotService = Depends(get_copilot_service),
) -> ChatResponse:

    result = await copilot.process(
        session_id=request.session_id,
        message=request.message,
    )

    return ChatResponse(**result)