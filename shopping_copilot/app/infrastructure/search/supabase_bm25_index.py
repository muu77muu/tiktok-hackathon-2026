
# rank-bm25 keyword index whose corpus is loaded once from the Supabase
# Catalog table, replacing keyword_index.py's JSONL loader. Same call
# contract KeywordRetriever expects -- search(query=..., filters=...,
# top_k=...) -- but async. True Okapi BM25 scoring; RRF fuses by rank, so
# these scores never need to be comparable with the vector side's.

import asyncio
import logging
import threading

from rank_bm25 import BM25Okapi

from .catalog_records import normalize_record
from .filtering import record_matches, to_metadata
from .keyword_index import tokenize, _product_text

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 50
PAGE_SIZE = 1000

COLUMNS = (
    "parent_asin,title,features,description,categories,"
    "price,average_rating,rating_number,store"
)


class SupabaseBM25Index:
    def __init__(self, client):
        self.client = client
        self._bm25: BM25Okapi | None = None
        self._ids: list[str] = []
        self._records: dict[str, dict] = {}
        self._lock = threading.Lock()

    def _get_bm25(self) -> BM25Okapi:
        # lazy singleton, same pattern as Embedder._get_model: the full-catalog
        # fetch + build takes ~a minute and shouldn't block process startup
        if self._bm25 is None:
            with self._lock:
                if self._bm25 is None:
                    self._build()
        return self._bm25

    def _build(self) -> None:
        logger.info("loading BM25 corpus from Supabase Catalog")
        records: dict[str, dict] = {}
        offset = 0
        while True:
            rows = (
                self.client.table("Catalog")
                .select(COLUMNS)
                .order("parent_asin")
                .range(offset, offset + PAGE_SIZE - 1)
                .execute()
                .data
                or []
            )
            for row in rows:
                pid = row.get("parent_asin")
                if pid:
                    records[pid] = normalize_record(row)
            if len(rows) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

        self._records = records
        self._ids = list(records)
        corpus = [tokenize(_product_text(records[pid])) for pid in self._ids]
        self._bm25 = BM25Okapi(corpus)
        logger.info("BM25 index built over %d products", len(self._ids))

    async def search(
        self, query: str, filters: dict | None = None, top_k: int = DEFAULT_TOP_K
    ) -> list[dict]:
        return await asyncio.to_thread(self._search_sync, query, filters, top_k)

    def _search_sync(self, query: str, filters: dict | None, top_k: int) -> list[dict]:
        bm25 = self._get_bm25()
        tokens = tokenize(query)
        if not tokens or not self._ids:
            return []

        scores = bm25.get_scores(tokens)

        results = []
        for i in scores.argsort()[::-1]:
            if scores[i] <= 0:
                break
            record = self._records[self._ids[i]]
            if not record_matches(record, filters):
                continue
            results.append({
                "product_id": self._ids[i],
                "score": float(scores[i]),
                "metadata": to_metadata(record),
            })
            if len(results) >= top_k:
                break
        return results

    @property
    def size(self) -> int:
        return len(self._ids)
