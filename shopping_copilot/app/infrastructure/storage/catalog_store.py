
# Single in-memory copy of the frozen catalog, loaded once from
# CATALOG_PATH (starter/catalog.jsonl). Shared by ProductsService, the
# keyword index, and the vector index so the 50k records exist in memory
# exactly once.

import json
import logging
import threading
from functools import lru_cache

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class CatalogStore:
    def __init__(self, path: str | None = None, id_field: str = "parent_asin"):
        self.path = path or get_settings().CATALOG_PATH
        self.id_field = id_field
        self._records: dict[str, dict] | None = None
        self._lock = threading.Lock()

    @property
    def records(self) -> dict[str, dict]:
        # lazy singleton, same pattern as Embedder._get_model
        if self._records is None:
            with self._lock:
                if self._records is None:
                    self._records = self._load()
        return self._records

    def _load(self) -> dict[str, dict]:
        logger.info("loading catalog from %s", self.path)
        records: dict[str, dict] = {}
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                product_id = record.get(self.id_field)
                if product_id:
                    records[product_id] = record
        logger.info("catalog loaded: %d products", len(records))
        return records

    def get(self, product_id: str) -> dict | None:
        return self.records.get(product_id)

    @property
    def size(self) -> int:
        return len(self.records)


@lru_cache()
def get_catalog_store() -> CatalogStore:
    return CatalogStore()
