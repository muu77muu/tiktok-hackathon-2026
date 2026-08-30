
# to combine candidate sets produced by multiple retrieval strategies
# Service-layer wrapper around rrf.py
# kept as a separate class  so the fusion algorithm can be swapped or made configurable per strategy without changing every call site
# eg. buying might want a lower k (sharper top-rank influence) than browsing's broader fan-out.

from .rrf import reciprocal_rank_fusion, DEFAULT_K

class CandidateFusion:
    def __init__(self, k: int = DEFAULT_K):
        self.k = k

    async def fuse(self, candidate_lists: list[list[dict]], k: int | None = None) -> list[dict]:
        non_empty = [lst for lst in candidate_lists if lst]
        if not non_empty:
            return []
        if len(non_empty) == 1:
            return non_empty[0]

        return reciprocal_rank_fusion(non_empty, k=k if k is not None else self.k)