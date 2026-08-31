from typing import Optional
import logging
import math

from app.infrastructure.storage.catalog_store import get_catalog_store
from app.infrastructure.storage.wishlist_store import get_wishlist_store

logger = logging.getLogger(__name__)


class ProductsService:
    """Product operations over the local catalog (catalog.jsonl) and the
    local JSON wishlist. Method names and response shapes match the old
    Supabase-backed implementation so routes and the frontend don't change."""

    def __init__(self, catalog_store=None, wishlist_store=None):
        self.catalog = catalog_store or get_catalog_store()
        self.wishlist = wishlist_store or get_wishlist_store()

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
        """Retrieve a product record by ID (ASIN), or None if not found."""
        record = self.catalog.get(product_id)
        if record is None:
            logger.warning(f"Product {product_id} not found in catalog")
        return record

    def get_wishlist(self):
        return [{"parent_asin": pid} for pid in self.wishlist.ids()]

    def update_wishlist(self, product_id: str):
        return self.wishlist.toggle(product_id)

    def get_wishlisted_products(self, page: int = 1, page_size: int = 20):
        product_ids = [pid.strip() for pid in self.wishlist.ids() if pid]
        total = len(product_ids)

        start_idx = (page - 1) * page_size
        page_ids = product_ids[start_idx:start_idx + page_size]

        items = []
        for pid in page_ids:
            record = self.catalog.get(pid)
            if record is None:
                continue
            items.append({
                "product_id": record.get("parent_asin"),
                "title": record.get("title"),
                "category": str(record.get("categories")) if record.get("categories") else None,
                "price": self.safe_parse_price(record.get("price")),
                "rating": record.get("average_rating"),
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size) or 1,
        }

    def list_products(self, page: int = 1, page_size: int = 20, category: str | None = None):
        """Paginated product listing with optional case-insensitive category
        match anywhere in the category chain. Iterates the in-memory catalog
        in stable insertion (file) order."""
        needle = category.casefold() if category else None

        matching = []
        for record in self.catalog.records.values():
            if needle is not None:
                chain = record.get("categories") or []
                if not any(needle in str(c).casefold() for c in chain):
                    continue
            matching.append(record)

        total = len(matching)
        start_idx = (page - 1) * page_size
        page_records = matching[start_idx:start_idx + page_size]

        items = [{
            "product_id": r.get("parent_asin"),
            "title": r.get("title"),
            "price": self.safe_parse_price(r.get("price")),
            "category": str(r.get("categories")) if r.get("categories") else None,
        } for r in page_records]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    def get_all_category_chains(self) -> list[list[str]]:
        """Every product's category chain (a list of category names)."""
        chains = []
        for record in self.catalog.records.values():
            chain = record.get("categories")
            if isinstance(chain, list) and chain:
                chains.append(chain)
        return chains
