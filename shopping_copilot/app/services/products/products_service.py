from typing import Optional
import logging

from app.core.config import get_supabase_client

logger = logging.getLogger(__name__)


class ProductsService:
    """Service for managing product operations with Supabase."""
    
    def __init__(self):
        self.client = get_supabase_client()
    
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
