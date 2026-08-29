from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends

from ..dependencies import get_evaluation_service

class EvaluationRequest(BaseModel):
    purchased_product_id: str
    retrieval_results: list[list[str]] = Field(default_factory=list)
    recommendation_results: list[list[str]] = Field(default_factory=list)
    turn_count: int = Field(
        ge=0,
        le=10,
    )
    k: int = Field(
        default=10,
        ge=1,
    )

class EvaluationResponse(BaseModel):
    purchased_product_id: str
    turn_count: int
    k: int
    coverage: dict = Field(default_factory=dict)
    precision: dict = Field(default_factory=dict)
    efficiency: dict = Field(default_factory=dict)



router = APIRouter(prefix="/evaluation", tags=["Evaluation"])

@router.post("/session", response_model=EvaluationResponse,)
async def evaluate_session(
    request: EvaluationRequest,
    evaluation_service=Depends(get_evaluation_service),
) -> EvaluationResponse:

    result = evaluation_service.evaluate_session(
        purchased_product_id=(request.purchased_product_id),
        retrieval_results=(request.retrieval_results),
        recommendation_results=(request.recommendation_results),
        turn_count=request.turn_count,
        k=request.k,
    )

    return EvaluationResponse(**result)