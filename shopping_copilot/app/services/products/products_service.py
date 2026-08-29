from typing import Optional
import logging
import math

from app.core.config import get_supabase_client

logger = logging.getLogger(__name__)



class ProductsService:
    """Service for managing product operations with Supabase."""
    
    def __init__(self):
        self.client = get_supabase_client()

    @staticmethod
    def safe_parse_price(price_val):
        """Helper to parse raw price string or float safely."""
        if price_val is None:
            return None
        try:
            return float(price_val)
        except (ValueError, TypeError):
            return None
    
    async def get_product(self, product_id: str) -> Optional[dict]:
        """
        Retrieve a product by ID from the Catalog table.
        
        Args:
            product_id: The ID of the product to retrieve (ASIN)
            
        Returns:
            Product data as a dictionary, or None if not found
            
        Raises:
            Exception: If the Supabase query fails
        """
        try:
            logger.info(f"Fetching product with ID: {product_id}")
            response = self.client.table("Catalog").select(
                "parent_asin, title, categories, description, price, average_rating, rating_number, store, features, details"
            ).eq("parent_asin", product_id).execute()
            
            logger.info(f"Response data: {response.data}")
            logger.info(f"Response count: {len(response.data) if response.data else 0}")
            
            # response.data is a list, get the first item if it exists
            if response.data and len(response.data) > 0:
                logger.info(f"Found product: {response.data[0].get('parent_asin')}")
                return response.data[0]
            
            logger.warning(f"Product {product_id} not found in Catalog table")
            return None
        except Exception as e:
            # Log the error for debugging
            logger.error(f"Error fetching product {product_id}: {str(e)}", exc_info=True)
            return None

    def get_wishlist(self):
        response = self.client.table("Wishlist").select("parent_asin").execute()
        return response.data

    def update_wishlist(self, product_id: str):
        # 1. Check if product exists in wishlist (No await)
        existing = (
            self.client.table("Wishlist")
            .select("*")
            .eq("parent_asin", product_id)
            .execute()
        )

        # 2. If it exists, delete it
        if existing.data:
            response = (
                self.client.table("Wishlist")
                .delete()
                .eq("parent_asin", product_id)
                .execute()
            )
            return {"action": "removed", "data": response.data}

        # 3. Otherwise, insert it
        response = (
            self.client.table("Wishlist")
            .insert({"parent_asin": product_id})
            .execute()
        )
        return {"action": "added", "data": response.data}
    
    def get_wishlisted_products(self, page: int = 1, page_size: int = 20):
        # 1. Fetch all product IDs from the Wishlist table
        wishlist_resp = self.client.table("Wishlist").select("parent_asin").execute()
        wishlist_items = wishlist_resp.data or []
        
        product_ids = [item["parent_asin"].strip() for item in wishlist_items if item.get("parent_asin")]
        total = len(product_ids)

        if not product_ids:
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 1
            }

        # 2. Paginate the product_ids list locally
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_ids = product_ids[start_idx:end_idx]

        if not page_ids:
            return {
                "items": [],
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": math.ceil(total / page_size) or 1
            }

        # 3. Fetch product details from Catalog table for the paginated IDs
        products_resp = (
            self.client.table("Catalog")
            .select("parent_asin, title, categories, price, average_rating")
            .in_("parent_asin", page_ids)
            .execute()
        )

        catalog_data = products_resp.data or []

        # 4. Map DB fields to match ProductItem schema
        items = []
        for prod in catalog_data:
            items.append({
                "product_id": prod.get("parent_asin"),
                "title": prod.get("title"),
                "category": prod.get("categories"),
                "price": self.safe_parse_price(prod.get("price")),
                "rating": prod.get("average_rating")
            })

        total_pages = math.ceil(total / page_size) or 1

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

