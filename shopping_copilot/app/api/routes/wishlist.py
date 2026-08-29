from pydantic import BaseModel, Field, field_validator
from fastapi import APIRouter, HTTPException, Depends
import logging
import json

from app.services.products.products_service import ProductsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wishlists", tags=["Wishlist"])


def get_products_service() -> ProductsService:
    """Dependency provider for ProductsService."""
    return ProductsService()

@router.get("/")
async def get_all(
    products_service: ProductsService = Depends(get_products_service)
):
    # Remove 'await' here
    response = products_service.get_wishlist()

    if not response:
        raise HTTPException(
            status_code=500, 
            detail="Wishlist retrieval not working"
        )

    return response

@router.post("/{product_id}")
async def add_to_wishlist(
    product_id: str, 
    products_service: ProductsService = Depends(get_products_service)
):
    # Remove 'await' here
    response = products_service.update_wishlist(product_id)

    if not response:
        raise HTTPException(
            status_code=404, 
            detail="Product not found or could not be updated in wishlist"
        )

    return response

