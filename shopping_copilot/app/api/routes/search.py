from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..dependencies import get_search_service

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    filters: dict = Field(default_factory=dict)
    top_k: int = Field(
        default=10,
        ge=1,
        le=100,
    )

class SearchResult(BaseModel):
    product_id: str
    score: float | None = None
    metadata: dict = Field(default_factory=dict)

class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult] = Field(default_factory=list)
    count: int = 0



router = APIRouter(prefix="/search", tags=["Search"])

@router.post("", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    search_service=Depends(get_search_service),
) -> SearchResponse:

    result = await search_service.search(
        query=request.query,
        filters=request.filters,
        top_k=request.top_k,
    )

    return SearchResponse(**result)