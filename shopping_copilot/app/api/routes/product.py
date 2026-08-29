from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends
import logging

from app.services.products.products_service import ProductsService

logger = logging.getLogger(__name__)


class ProductResponse(BaseModel):
    product_id: str
    title: str | None = None
    category: str | None = None
    description: str | None = None
    price: float | None = None
    rating: float | None = None
    metadata: dict = Field(default_factory=dict)


router = APIRouter(prefix="/products", tags=["Products"])


def get_products_service() -> ProductsService:
    """Dependency provider for ProductsService."""
    return ProductsService()


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    products_service: ProductsService = Depends(get_products_service),
) -> ProductResponse:
    """
    Retrieve a product by ID from Supabase Catalog table.
    
    Args:
        product_id: The ID of the product to retrieve
        
    Returns:
        ProductResponse with product details
        
    Raises:
        HTTPException: If product not found (404)
    """
    product = await products_service.get_product(product_id)
    
    if product is None:
        raise HTTPException(
            status_code=404,
            detail=f"Product with ID '{product_id}' not found"
        )
    
    # Map database fields to response model
    # Supabase columns: parent_asin, title, categories (not category), description, 
    # price, average_rating (not rating), rating_number, store, features, details
    return ProductResponse(
        product_id=product.get("parent_asin"),
        title=product.get("title"),
        category=product.get("categories"),  # Note: DB column is plural
        description=product.get("description"),
        price=product.get("price"),
        rating=product.get("average_rating"),  # Note: DB column is average_rating
        metadata={
            "rating_number": product.get("rating_number"),
            "store": product.get("store"),
            "features": product.get("features"),
            "details": product.get("details"),
        },
    )


@router.get("/debug/catalog", tags=["Debug"])
async def debug_catalog(
    products_service: ProductsService = Depends(get_products_service),
):
    """
    DEBUG ENDPOINT: List first 5 products in Catalog to verify connection and schema.
    """
    try:
        response = products_service.client.table("Catalog").select("*").limit(5).execute()
        logger.info(f"Catalog sample data: {response.data}")
        return {
            "status": "success",
            "count": len(response.data) if response.data else 0,
            "sample_data": response.data,
            "columns": list(response.data[0].keys()) if response.data else []
        }
    except Exception as e:
        logger.error(f"Debug query failed: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }