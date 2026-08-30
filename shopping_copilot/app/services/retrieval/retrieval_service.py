
# to coordinate retrieval across keyword, vector, and category sources
# default "hybrid" strategy runs all applicable sources concurrently and fuses them 
# single-source strategies exist for cases that don't need the full fan-out (eg. cheap typeahead path, or debugging one retriever in isolation)

import asyncio
import logging

from .keyword_retriever import KeywordRetriever
from .vector_retriever import VectorRetriever
from .category_retriever import CategoryRetriever
from .metadata_filter import MetadataFilter
from .candidate_fusion import CandidateFusion
from .candidate_manager import CandidateManager

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 100

class RetrievalService:
    def __init__(
        self,
        keyword_retriever: KeywordRetriever | None = None,
        vector_retriever: VectorRetriever | None = None,
        category_retriever: CategoryRetriever | None = None,
        metadata_filter: MetadataFilter | None = None,
        candidate_fusion: CandidateFusion | None = None,
        candidate_manager: CandidateManager | None = None,
    ):
        self.keyword_retriever = keyword_retriever
        self.vector_retriever = vector_retriever
        self.category_retriever = category_retriever
        self.metadata_filter = metadata_filter or MetadataFilter()
        self.candidate_fusion = candidate_fusion or CandidateFusion()
        self.candidate_manager = candidate_manager or CandidateManager()

    async def retrieve(
        self,
        query: str,
        filters: dict | None = None,
        context: dict | None = None,
        strategy: str = "hybrid",
        top_k: int = DEFAULT_TOP_K,
    ) -> dict:
        context = context or {}
        filters = filters or {}

        try:
            raw_candidates = await self._run_strategy(query, filters, strategy)
        except Exception as exc:
            logger.exception("retrieval strategy %r failed for query=%r", strategy, query)
            return self._result(query, strategy, filters, context, [], 0, f"error: {exc}")

        filtered = await self.metadata_filter.apply(raw_candidates, filters)
        finalized, diagnostics = await self.candidate_manager.finalize(filtered, top_k)

        status = "ok" if finalized else "no_results"
        result = self._result(query, strategy, filters, context, finalized, len(finalized), status)
        result["diagnostics"] = diagnostics.__dict__
        return result

    async def retrieve_by_vector(
        self,
        vector: list[float],
        filters: dict | None = None,
        context: dict | None = None,
        top_k: int = DEFAULT_TOP_K,
    ) -> dict:
        context = context or {}
        filters = filters or {}

        if self.vector_retriever is None:
            return self._result("", "vector_only", filters, context, [], 0, "no_vector_retriever")

        try:
            raw_candidates = await self.vector_retriever.search_by_vector(
                vector, filters=filters, top_k=top_k
            )
        except Exception as exc:
            logger.exception("vector-only retrieval failed")
            return self._result("", "vector_only", filters, context, [], 0, f"error: {exc}")

        filtered = await self.metadata_filter.apply(raw_candidates, filters)
        finalized, diagnostics = await self.candidate_manager.finalize(filtered, top_k)

        status = "ok" if finalized else "no_results"
        result = self._result("", "vector_only", filters, context, finalized, len(finalized), status)
        result["diagnostics"] = diagnostics.__dict__
        return result

    # lower-level than `retrieve` where it takes candidate list the caller already gathered and returns a fused, deduped list
    # return list of dict as there is no single query / strategy to attribute towards
    async def fuse(self, candidate_lists: list[list[dict]]) -> list[dict]:
        fused = await self.candidate_fusion.fuse(candidate_lists)
        deduped, _ = await self.candidate_manager.finalize(fused, top_k=len(fused))
        return deduped

    async def _run_strategy(self, query: str, filters: dict, strategy: str) -> list[dict]:
        if strategy == "keyword":
            return await self._keyword(query, filters)
        if strategy == "vector":
            return await self._vector(query, filters)
        if strategy == "category":
            return await self._category(filters)
        if strategy == "hybrid":
            return await self._hybrid(query, filters)

        logger.warning("unknown retrieval strategy %r, falling back to hybrid", strategy)
        return await self._hybrid(query, filters)

    async def _hybrid(self, query: str, filters: dict) -> list[dict]:
        tasks = [self._keyword(query, filters), self._vector(query, filters)]

        category = self._extract_category(filters)
        if category:
            tasks.append(self._category(filters))

        results = await asyncio.gather(*tasks)
        non_empty = [r for r in results if r]
        if not non_empty:
            return []

        return await self.candidate_fusion.fuse(non_empty)

    async def _keyword(self, query: str, filters: dict) -> list[dict]:
        if self.keyword_retriever is None:
            return []
        return await self.keyword_retriever.search(query, filters=filters)

    async def _vector(self, query: str, filters: dict) -> list[dict]:
        if self.vector_retriever is None:
            return []
        return await self.vector_retriever.search(query, filters=filters)

    async def _category(self, filters: dict) -> list[dict]:
        if self.category_retriever is None:
            return []
        category = self._extract_category(filters)
        return await self.category_retriever.search(category, filters=filters)

    def _extract_category(self, filters: dict) -> str | None:
        for clause in filters.get("must", []):
            if clause.get("field") == "category":
                value = clause.get("value")
                return value if isinstance(value, str) else None
        return None

    def _result(
        self,
        query: str,
        strategy: str,
        filters: dict,
        context: dict,
        candidates: list[dict],
        total: int,
        status: str,
    ) -> dict:
        return {
            "query": query,
            "strategy": strategy,
            "filters": filters,
            "context": context,
            "candidates": candidates,
            "total_candidates": total,
            "status": status,
        }