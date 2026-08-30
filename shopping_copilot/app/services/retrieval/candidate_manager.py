
# to manage retrieved candidate pool (incl. deduplication, truncation, and pool-size assessment)
# Before candidates leave the retrieval layer: dedup by product_id (keeping the best-scored occurrence), enforce the requested top_k cap, and attach lightweight retrieval diagnostics. 

from dataclasses import dataclass

@dataclass
class RetrievalDiagnostics:
    total_before_dedup: int
    total_after_dedup: int
    source_counts: dict[str, int]

class CandidateManager:
    async def finalize(
        self, candidates: list[dict], top_k: int
    ) -> tuple[list[dict], RetrievalDiagnostics]:
        deduped = self._dedupe(candidates)
        source_counts = self._count_sources(deduped)

        diagnostics = RetrievalDiagnostics(
            total_before_dedup=len(candidates),
            total_after_dedup=len(deduped),
            source_counts=source_counts,
        )

        return deduped[:top_k], diagnostics

    def _dedupe(self, candidates: list[dict]) -> list[dict]:
        best_by_id: dict[str, dict] = {}

        for c in candidates:
            pid = c.get("product_id")
            if not pid:
                continue
            existing = best_by_id.get(pid)
            if existing is None or c.get("score", 0.0) > existing.get("score", 0.0):
                best_by_id[pid] = c

        return sorted(best_by_id.values(), key=lambda c: c.get("score", 0.0), reverse=True)

    def _count_sources(self, candidates: list[dict]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for c in candidates:
            source = c.get("source", "unknown")
            counts[source] = counts.get(source, 0) + 1
        return counts