"""Smoke test for the local hybrid retrieval stack.

Verifies, against the real service wiring (same objects the API uses):
  1. hybrid search fuses BM25 + vector via RRF and finds the target product
  2. keyword-only and vector-only strategies work in isolation
  3. category-filtered retrieval works
  4. the HyDE path (retrieve by precomputed embedding) works

Usage (from shopping_copilot/):
    python -m scripts.smoke_retrieval
"""

import asyncio
import time

from app.api.dependencies import get_retrieval_service, get_embedder
from app.infrastructure.storage.catalog_store import get_catalog_store


async def main():
    store = get_catalog_store()
    target_id, target = next(iter(store.records.items()))
    query = (target.get("title") or "")[:60]
    print(f"query : {query}")
    print(f"target: {target_id}")

    svc = get_retrieval_service()

    t0 = time.time()
    result = await svc.retrieve(query, strategy="hybrid", top_k=10)
    print(f"\n[1] hybrid: {result['status']}, {result['total_candidates']} candidates "
          f"(cold {time.time() - t0:.1f}s -- includes model+index load)")

    sources: set[str] = set()
    for c in result["candidates"]:
        sources.update(c.get("fusion_sources") or [c.get("source")])
    for c in result["candidates"][:5]:
        title = (c["metadata"].get("title") or "")[:55]
        print(f"    {c.get('fusion_sources', c.get('source'))} {c['product_id']} {title}")

    assert result["candidates"], "hybrid returned nothing"
    assert "keyword" in sources, "BM25 contributed nothing"
    assert "vector" in sources, "vector index contributed nothing"
    assert any(c["product_id"] == target_id for c in result["candidates"]), \
        "target product missing from fused results"

    t0 = time.time()
    await svc.retrieve("cozy winter hoodie for men", strategy="hybrid", top_k=10)
    print(f"    warm hybrid query: {(time.time() - t0) * 1000:.0f}ms")

    kw = await svc.retrieve(query, strategy="keyword", top_k=5)
    vec = await svc.retrieve(query, strategy="vector", top_k=5)
    print(f"\n[2] keyword-only: {kw['status']} ({kw['total_candidates']}) | "
          f"vector-only: {vec['status']} ({vec['total_candidates']})")
    assert kw["candidates"] and vec["candidates"]

    filt = await svc.retrieve(
        query,
        filters={"must": [{"field": "category", "value": "Women"}]},
        strategy="hybrid",
        top_k=5,
    )
    print(f"\n[3] filtered (category=Women): {filt['status']} ({filt['total_candidates']})")
    assert filt["candidates"], "filtered query returned nothing"

    hyde_vec = await get_embedder().embed("elegant gold hoop earrings", is_query=True)
    byvec = await svc.retrieve_by_vector(hyde_vec, top_k=5)
    print(f"\n[4] retrieve_by_vector (HyDE path): {byvec['status']} ({byvec['total_candidates']})")
    assert byvec["candidates"], "vector-by-embedding returned nothing"

    print("\nALL CHECKS PASSED: hybrid RRF (BM25 + vector) is working")


if __name__ == "__main__":
    asyncio.run(main())
