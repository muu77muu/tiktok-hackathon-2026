from pydantic import BaseModel, Field
from fastapi import APIRouter

class ProductResponse(BaseModel):
    product_id: str
    title: str | None = None
    category: str | None = None
    description: str | None = None
    price: float | None = None
    rating: float | None = None
    metadata: dict = Field(default_factory=dict)



router = APIRouter(prefix="/products", tags=["Products"])

@router.get("/{product_id}", response_model=ProductResponse,)
async def get_product(product_id: str,) -> ProductResponse:
    raise NotImplementedError("Product service integration pending.")