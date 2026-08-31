
# Local, in-process retrieval indexes over the frozen catalog -- no external
# DB in the retrieval path. The vector index is the numpy VectorIndex loaded
# from data/vector_index.npz (built by scripts/build_indexes.py); the keyword
# index is the hand-rolled Okapi BM25 built from the shared CatalogStore.
#
# Both are heavy to load (~2s npz load, ~20s BM25 build over 50k docs), so
# LazyIndex defers loading to the first search; main.py also warms them in a
# background thread at startup so the first user query usually finds them hot.

import logging
from functools import lru_cache

from app.core.config import get_settings
from app.infrastructure.storage.catalog_store import get_catalog_store
from .vector_index import VectorIndex
from .keyword_index import KeywordIndex

logger = logging.getLogger(__name__)


@lru_cache()
def load_vector_index() -> VectorIndex:
    path = get_settings().VECTOR_INDEX_PATH
    logger.info("loading vector index from %s", path)
    index = VectorIndex.load(path)
    # drop the npz's embedded records copy and share the CatalogStore's,
    # so the 50k records exist in memory once
    index._records = get_catalog_store().records
    logger.info("vector index ready: %d vectors, dim=%d", index.size, index.dim)
    return index


@lru_cache()
def load_keyword_index() -> KeywordIndex:
    logger.info("building BM25 keyword index")
    index = KeywordIndex.build_from_records(get_catalog_store().records)
    logger.info("keyword index ready: %d products", index.size)
    return index


class LazyIndex:
    """Defers a heavy index load to the first search call. Search signatures
    pass through unchanged (vector index takes vector=, keyword takes query=)."""

    def __init__(self, loader):
        self._loader = loader

    def search(self, *args, **kwargs):
        return self._loader().search(*args, **kwargs)


def warm_indexes() -> None:
    """Blocking warm-up of both indexes; call from a background thread."""
    try:
        load_vector_index()
        load_keyword_index()
        logger.info("retrieval indexes warmed")
    except FileNotFoundError as exc:
        logger.error(
            "vector index file missing (%s) -- run: python -m scripts.build_indexes",
            exc,
        )
    except Exception:
        logger.exception("index warm-up failed")
