
# RRF (Reciprocal Rank Fusion) implementation for combining ranked retrieval results
# Reciprocal Rank Fusion (RRF): combines multiple ranked candidate lists into one, using each item's *rank position* per list rather than raw scores.
# score(item) = sum over lists containing item of  1 / (k + rank_in_list)
# Higher k dampens the influence of any single list's top rank; lower k makes a #1 ranking in one list count for more.

DEFAULT_K = 60

def reciprocal_rank_fusion(
    candidate_lists: list[list[dict]], k: int = DEFAULT_K
) -> list[dict]:
    scores: dict[str, float] = {}
    best_candidate: dict[str, dict] = {}
    sources: dict[str, set[str]] = {}

    for candidate_list in candidate_lists:
        for rank, candidate in enumerate(candidate_list, start=1):
            pid = candidate.get("product_id")
            if not pid:
                continue

            scores[pid] = scores.get(pid, 0.0) + 1.0 / (k + rank)
            sources.setdefault(pid, set()).add(candidate.get("source", "unknown"))

            # Keep the richest metadata seen for this product_id; later lists (lower-priority source) shouldnt overwrite a candidate with fuller metadata from an earlier list.
            existing = best_candidate.get(pid)
            if existing is None or len(candidate.get("metadata", {})) > len(existing.get("metadata", {})):
                best_candidate[pid] = candidate

    fused = []
    for pid, score in scores.items():
        base = best_candidate[pid]
        fused.append(
            {
                **base,
                "score": score,
                "source": "fused",
                "fusion_sources": sorted(sources[pid]),
            }
        )

    fused.sort(key=lambda c: c["score"], reverse=True)
    return fused