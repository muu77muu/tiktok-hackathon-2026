import asyncio
import logging
import threading

from app.core.config import get_settings
from .model_registry import get_active_embedding_model

logger = logging.getLogger(__name__)

# Local embedding via Qwen3-Embedding-0.6B (sentence-transformers).
# Qwen3-Embedding is instruction-aware: queries are encoded with the model's
# built-in "query" prompt, documents without it -- mixing them up degrades
# retrieval quality, hence the explicit is_query flags below.
class Embedder:
    def __init__(
        self,
        model: str | None = None,
        device: str | None = None,
    ):
        settings = get_settings()

        self.model_name = model or get_active_embedding_model().name
        self.device = device or settings.EMBEDDING_DEVICE or None
        self._model = None
        self._lock = threading.Lock()

    def _get_model(self):
        # lazy singleton: loading ~1.2GB of weights at import time would slow
        # every process start (tests, scripts) that never embeds anything
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from sentence_transformers import SentenceTransformer

                    logger.info("loading embedding model %s", self.model_name)
                    self._model = SentenceTransformer(
                        self.model_name, device=self.device
                    )
        return self._model

    def _encode(self, texts: list[str], is_query: bool) -> list[list[float]]:
        model = self._get_model()
        kwargs: dict = {"normalize_embeddings": True}
        if is_query:
            kwargs["prompt_name"] = "query"
        embeddings = model.encode(texts, **kwargs)
        return embeddings.tolist()

    async def embed(self, text: str, *, is_query: bool = True) -> list[float]:
        # to_thread keeps the event loop free during model inference
        [vector] = await asyncio.to_thread(self._encode, [text], is_query)
        return vector

    async def embed_batch(
        self, texts: list[str], *, is_query: bool = False
    ) -> list[list[float]]:
        """Batches into one forward pass rather than N sequential ones --
        mainly for scripts/build_indexes.py embedding a full catalog, but
        any bulk-embedding caller should prefer this over looping embed().
        Defaults to document-style encoding (no query prompt)."""
        if not texts:
            return []
        return await asyncio.to_thread(self._encode, texts, is_query)
