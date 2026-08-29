from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends

from ..dependencies import get_recommendation_service

class RecommendationRequest(BaseModel):
    query: str
    candidates: list[dict] = Field(default_factory=list)
    context: dict = Field(default_factory=dict)
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
    )

class RecommendationResponse(BaseModel):
    query: str
    products: list[dict] = Field(default_factory=list)
    count: int = 0



router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

@router.post("", response_model=RecommendationResponse)
async def recommend(
    request: RecommendationRequest,
    recommendation_service=Depends(get_recommendation_service),
) -> RecommendationResponse:

    result = await recommendation_service.recommend(
        query=request.query,
        candidates=request.candidates,
        context=request.context,
        top_k=request.top_k,
    )

    return RecommendationResponse(
        query=request.query,
        products=result.get(
            "products",
            [],
        ),
        count=result.get(
            "count",
            0,
        ),
    )