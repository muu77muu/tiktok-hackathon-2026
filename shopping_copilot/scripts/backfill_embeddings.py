"""Resumable backfill of Catalog.embedding in Supabase.

Pages rows where embedding is null, embeds title+categories with the local
Qwen model (document mode, no query prompt), and writes the vectors back in
batch upserts. Safe to interrupt and re-run -- it only ever selects rows
still missing an embedding, so completed work is never redone.

Usage (from shopping_copilot/):
    python -m scripts.backfill_embeddings              # full run
    python -m scripts.backfill_embeddings --limit 64   # trial run
"""

import argparse
import asyncio
import logging
import time

from supabase import create_client

from app.core.config import get_settings
from app.ai.embeddings.embedder import Embedder
from app.infrastructure.search.catalog_records import normalize_record
from app.infrastructure.search.vector_index import _product_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill")

FETCH_SIZE = 256


def get_service_client():
    settings = get_settings()
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def _remaining(client) -> int:
    resp = (
        client.table("Catalog")
        .select("parent_asin", count="exact")
        .is_("embedding", "null")
        .limit(1)
        .execute()
    )
    return resp.count or 0


def _write_batch(client, payload: list[dict]) -> None:
    try:
        client.table("Catalog").upsert(payload, on_conflict="parent_asin").execute()
    except Exception:
        # no unique constraint on parent_asin would break upsert; fall back
        # to per-row updates so the run still completes, just slower
        logger.warning("batch upsert failed, falling back to per-row updates")
        for item in payload:
            client.table("Catalog").update({"embedding": item["embedding"]}).eq(
                "parent_asin", item["parent_asin"]
            ).execute()


async def run(limit: int | None) -> None:
    client = get_service_client()
    embedder = Embedder()

    total = _remaining(client)
    target = min(total, limit) if limit else total
    logger.info("rows missing embeddings: %d (processing %d)", total, target)

    done = 0
    start = time.time()
    while done < target:
        fetch = min(FETCH_SIZE, target - done)
        resp = (
            client.table("Catalog")
            .select("parent_asin,title,categories")
            .is_("embedding", "null")
            .limit(fetch)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            break

        # dedupe: duplicate ids in one upsert payload are a Postgres error
        by_id = {r["parent_asin"]: r for r in rows if r.get("parent_asin")}
        ids = list(by_id)
        # normalize first: categories is a stringified list in Supabase, and
        # _product_text expects a real list
        texts = [_product_text(normalize_record(by_id[i])) for i in ids]

        vectors = await embedder.embed_batch(texts, is_query=False)
        payload = [{"parent_asin": i, "embedding": v} for i, v in zip(ids, vectors)]
        _write_batch(client, payload)

        done += len(rows)
        rate = done / max(time.time() - start, 1e-9)
        eta_min = (target - done) / max(rate, 1e-9) / 60
        logger.info("progress %d/%d (%.1f rows/s, eta %.1f min)", done, target, rate, eta_min)

    logger.info("done: %d rows embedded in %.1f min, %d still missing",
                done, (time.time() - start) / 60, _remaining(client))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="max rows to process (trial runs)")
    args = parser.parse_args()
    asyncio.run(run(args.limit))
