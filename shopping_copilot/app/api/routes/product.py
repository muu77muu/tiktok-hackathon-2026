from pydantic import BaseModel, Field, field_validator
from fastapi import APIRouter, HTTPException, Depends
import logging

from app.services.products.products_service import ProductsService

logger = logging.getLogger(__name__)


def safe_parse_price(price_value) -> float | None:
    """
    Safely parse price from various formats.
    
    Handles:
    - None values
    - Already float/int values
    - String numbers
    - Invalid strings (returns None)
    """
    if price_value is None:
        return None
    
    # If already a number, return it
    if isinstance(price_value, (int, float)):
        return float(price_value)
    
    # If string, try to convert
    if isinstance(price_value, str):
        try:
            return float(price_value)
        except (ValueError, TypeError):
            # Invalid price format, return None
            logger.debug(f"Could not parse price value: {price_value}")
            return None
    
    return None


class ProductResponse(BaseModel):
    product_id: str
    title: str | None = None
    category: str | None = None
    description: str | None = None
    price: float | None = None
    rating: float | None = None
    metadata: dict = Field(default_factory=dict)


class ProductListItem(BaseModel):
    """Simplified product response for list endpoints."""
    product_id: str
    title: str | None = None
    price: float | None = None
    category: str | None = None


class PaginatedProductList(BaseModel):
    """Paginated product list response with metadata."""
    items: list[ProductListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


router = APIRouter(prefix="/products", tags=["Products"])


def get_products_service() -> ProductsService:
    """Dependency provider for ProductsService."""
    return ProductsService()


@router.get("/list", response_model=PaginatedProductList)
async def list_products(
    page: int = 1,
    page_size: int = 20,
    products_service: ProductsService = Depends(get_products_service),
) -> PaginatedProductList:
    """
    Retrieve a paginated list of products with limited fields.
    
    Args:
        page: Page number (1-indexed, default 1)
        page_size: Number of products per page (default 20, max 100)
        
    Returns:
        PaginatedProductList with items, total count, and pagination metadata
    """
    # Validate pagination parameters
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    
    # Cap page_size at 100 for performance
    page_size = min(page_size, 100)
    
    try:
        # Get total count
        count_response = products_service.client.table("Catalog").select(
            "parent_asin", count="exact"
        ).execute()
        total = count_response.count or 0
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Fetch paginated results
        response = products_service.client.table("Catalog").select(
            "parent_asin, title, price, categories"
        ).range(offset, offset + page_size - 1).execute()
        
        products = []
        if response.data:
            for product in response.data:
                products.append(
                    ProductListItem(
                        product_id=product.get("parent_asin"),
                        title=product.get("title"),
                        price=safe_parse_price(product.get("price")),
                        category=product.get("categories"),
                    )
                )
        
        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size
        
        return PaginatedProductList(
            items=products,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except Exception as e:
        logger.error(f"Error fetching products list: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch products"
        )


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
        price=safe_parse_price(product.get("price")),
        rating=product.get("average_rating"),  # Note: DB column is average_rating
        metadata={
            "rating_number": product.get("rating_number"),
            "store": product.get("store"),
            "features": product.get("features"),
            "details": product.get("details"),
        },
    )
