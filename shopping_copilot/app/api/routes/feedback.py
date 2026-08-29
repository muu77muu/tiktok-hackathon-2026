from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/feedback", tags=["Feedback"])

class FeedbackRequest(BaseModel):
    session_id: str
    product_id: str | None = None
    feedback: str
    metadata: dict = {}

@router.post("")
async def submit_feedback(
    request: FeedbackRequest,
) -> dict:

    return {
        "session_id": request.session_id,
        "product_id": request.product_id,
        "feedback": request.feedback,
        "status": "accepted",
    }