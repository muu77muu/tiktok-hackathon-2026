"""One-time build of the dense vector index from the local catalog JSONL.

Reads CATALOG_PATH (starter/catalog.jsonl), embeds every product's
title+categories text with the local Qwen model (document mode), and saves
the result to VECTOR_INDEX_PATH (data/vector_index.npz). The app loads that
file at startup; re-run this script whenever the catalog or the embedding
model changes.

Usage (from shopping_copilot/):
    python -m scripts.build_indexes
"""

import logging
import os
import time

import numpy as np

from app.core.config import get_settings
from app.ai.embeddings.embedder import Embedder
from app.infrastructure.search.vector_index import VectorIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("build_indexes")

LOG_EVERY = 1280  # rows


def main() -> None:
    settings = get_settings()
    catalog_path = settings.CATALOG_PATH
    out_path = settings.VECTOR_INDEX_PATH
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    logger.info("catalog: %s", catalog_path)
    embedder = Embedder()
    state = {"done": 0, "t0": time.time()}

    # build_from_jsonl wants a sync list[str] -> ndarray fn; _encode is the
    # Embedder's sync core (async embed_batch just wraps it in a thread)
    def embed_fn(texts: list[str]) -> np.ndarray:
        vectors = np.asarray(embedder._encode(texts, is_query=False), dtype=np.float32)
        state["done"] += len(texts)
        if state["done"] % LOG_EVERY < len(texts):
            rate = state["done"] / max(time.time() - state["t0"], 1e-9)
            logger.info("embedded %d rows (%.1f rows/s)", state["done"], rate)
        return vectors

    index = VectorIndex.build_from_jsonl(catalog_path, embed_fn=embed_fn)

    logger.info("saving %d vectors (dim=%d) to %s", index.size, index.dim, out_path)
    index.save(out_path)
    size_mb = os.path.getsize(out_path) / 1048576
    logger.info(
        "done in %.1f min, index file %.0f MB",
        (time.time() - state["t0"]) / 60,
        size_mb,
    )


if __name__ == "__main__":
    main()
