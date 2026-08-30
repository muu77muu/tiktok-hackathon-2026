import asyncio
import logging

from openai import AsyncOpenAI, APIError, APITimeoutError

from app.core.config import get_settings
from .model_registry import get_active_embedding_model

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 2

class Embedder:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        settings = get_settings()

        if not (api_key or settings.LLM_API_KEY):
            raise ValueError("No embedding API key configured. Set LLM_API_KEY.")

        self.model = model or get_active_embedding_model().name
        self.max_retries = max_retries

        self._client = AsyncOpenAI(
            api_key=api_key or settings.LLM_API_KEY,
            base_url=base_url or settings.LLM_BASE_URL,
            timeout=timeout or settings.LLM_TIMEOUT_SECONDS,
        )

    async def embed(self, text: str) -> list[float]:
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.embeddings.create(model=self.model, input=text)
                return response.data[0].embedding
            except (APIError, APITimeoutError) as exc:
                last_error = exc
                logger.warning(
                    "embedding call failed (attempt %d/%d): %s",
                    attempt + 1,
                    self.max_retries + 1,
                    exc,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep((2 ** attempt) * 0.5)

        raise RuntimeError(
            f"embedding failed after {self.max_retries + 1} attempts"
        ) from last_error

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batches into one API call rather than N sequential ones --
        mainly for scripts/build_indexes.py embedding a full catalog, but
        any bulk-embedding caller should prefer this over looping embed()."""
        if not texts:
            return []
        try:
            response = await self._client.embeddings.create(model=self.model, input=texts)
            return [d.embedding for d in response.data]
        except (APIError, APITimeoutError):
            logger.exception("batch embedding failed, falling back to per-item calls")
            return [await self.embed(t) for t in texts]