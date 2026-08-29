from pydantic import BaseModel, Field, field_validator
from fastapi import APIRouter, HTTPException, Depends
import logging
import json

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


@router.get("/wishlisted", response_model=PaginatedProductList)
def get_wishlisted_products(
    page: int = 1,
    page_size: int = 20,
    products_service: ProductsService = Depends(get_products_service)
) -> PaginatedProductList:
    """
    Retrieve paginated products that have been added to the wishlist.
    """
    try:
        data = products_service.get_wishlisted_products(page=page, page_size=page_size)
        return PaginatedProductList(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch wishlisted products: {str(e)}")

@router.get("/list", response_model=PaginatedProductList)
async def list_products(
    page: int = 1,
    page_size: int = 20,
    category: str | None = None,
    products_service: ProductsService = Depends(get_products_service),
) -> PaginatedProductList:
    """
    Retrieve a paginated list of products with limited fields.
    
    Args:
        page: Page number (1-indexed, default 1)
        page_size: Number of products per page (default 20, max 100)
        category: Optional category filter - matches any category in the product's category array
        
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
        # Build count query
        count_query = products_service.client.table("Catalog").select(
            "parent_asin", count="exact"
        )
        
        # Apply category filter if provided
        # Categories are stored as text strings (e.g., "['Clothing', 'Women']")
        # Use ILIKE for case-insensitive text search
        if category:
            # Search for the category name within the categories text field
            count_query = count_query.filter("categories", "ilike", f"%{category}%")
        
        count_response = count_query.execute()
        total = count_response.count or 0
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Build data query
        data_query = products_service.client.table("Catalog").select(
            "parent_asin, title, price, categories"
        )
        
        # Apply category filter if provided
        # Categories are stored as text strings (e.g., "['Clothing', 'Women']")
        if category:
            # Search for the category name within the categories text field
            data_query = data_query.filter("categories", "ilike", f"%{category}%")
        
        # Apply pagination
        data_query = data_query.range(offset, offset + page_size - 1)
        
        response = data_query.execute()
        
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


def _build_category_tree(category_chains: list[list[str]]) -> dict:
    """
    Build a hierarchical tree structure from category chains.
    
    Example input: [['Clothing', 'Women', 'Shoes'], ['Clothing', 'Men', 'Shoes']]
    Example output: {
        'Clothing': {
            'Women': {'Shoes': {}},
            'Men': {'Shoes': {}}
        }
    }
    """
    tree = {}
    
    for chain in category_chains:
        current_level = tree
        for category in chain:
            if category not in current_level:
                current_level[category] = {}
            current_level = current_level[category]
    
    return tree


def _tree_to_list_format(tree: dict) -> list[dict]:
    """
    Convert tree structure to a list format with nested children.
    
    Example output: [
        {
            "name": "Clothing",
            "children": [
                {
                    "name": "Women",
                    "children": [{"name": "Shoes", "children": []}]
                }
            ]
        }
    ]
    """
    result = []
    
    for name, subtree in tree.items():
        node = {
            "name": name,
            "children": _tree_to_list_format(subtree)
        }
        result.append(node)
    
    return result


@router.get("/debug/categories", tags=["Debug"])
async def get_available_categories(
    products_service: ProductsService = Depends(get_products_service),
    flat: bool = False,
) -> dict:
    """
    Get available categories from all products in hierarchical format.
    Debug endpoint to help with category filtering.
    
    Args:
        flat: If True, return categories as a flat list. If False (default), return hierarchical structure.
    
    Returns:
        Dictionary with categories in hierarchical tree format (or flat list if flat=True).
        Hierarchical format shows parent-child relationships based on category chains in products.
    """
    try:
        # Fetch all products with their categories
        response = products_service.client.table("Catalog").select(
            "categories"
        ).execute()
        
        category_chains = []
        
        if response.data:
            for product in response.data:
                categories = product.get("categories")
                chain = None
                
                if isinstance(categories, list):
                    # Already a list
                    chain = categories
                elif isinstance(categories, str):
                    # Try to parse as JSON/Python list string
                    try:
                        # Handle Python list format with single quotes
                        categories_str = categories.replace("'", '"')
                        parsed = json.loads(categories_str)
                        if isinstance(parsed, list):
                            chain = parsed
                    except (json.JSONDecodeError, ValueError):
                        logger.debug(f"Could not parse categories string: {categories}")
                
                # Only add non-empty chains
                if chain:
                    category_chains.append(chain)
        
        # If flat=True, return flat list like before
        if flat:
            all_categories = set()
            for chain in category_chains:
                all_categories.update(chain)
            return {
                "format": "flat",
                "categories": sorted(list(all_categories)),
                "total_unique": len(all_categories)
            }
        
        # Otherwise return hierarchical structure
        tree = _build_category_tree(category_chains)
        category_list = _tree_to_list_format(tree)
        
        return {
            "format": "hierarchical",
            "categories": category_list,
            "total_chains": len(category_chains)
        }
    except Exception as e:
        logger.error(f"Error fetching categories: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch categories"
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
