
# Local JSON-file wishlist, replacing the Supabase "Wishlist" table.
# Stores a flat list of parent_asin strings at WISHLIST_PATH
# (data/wishlist.json). Response shapes in ProductsService stay identical
# to the old table-backed ones so routes and the frontend don't change.

import json
import os
import threading
from functools import lru_cache

from app.core.config import get_settings


class WishlistStore:
    def __init__(self, path: str | None = None):
        self.path = path or get_settings().WISHLIST_PATH
        self._lock = threading.Lock()

    def _read(self) -> list[str]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [str(p) for p in data] if isinstance(data, list) else []
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _write(self, ids: list[str]) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(ids, f, indent=2)

    def ids(self) -> list[str]:
        with self._lock:
            return self._read()

    def toggle(self, product_id: str) -> dict:
        """Add if absent, remove if present -- mirrors the old
        ProductsService.update_wishlist behavior and return shape."""
        with self._lock:
            ids = self._read()
            if product_id in ids:
                ids = [p for p in ids if p != product_id]
                self._write(ids)
                return {"action": "removed", "data": [{"parent_asin": product_id}]}
            ids.append(product_id)
            self._write(ids)
            return {"action": "added", "data": [{"parent_asin": product_id}]}


@lru_cache()
def get_wishlist_store() -> WishlistStore:
    return WishlistStore()
