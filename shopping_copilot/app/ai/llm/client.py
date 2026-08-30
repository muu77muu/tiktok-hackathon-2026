import asyncio
import logging

from openai import AsyncOpenAI, APIError, APITimeoutError

from app.core.config import get_settings

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ):
        settings = get_settings()

        if not (api_key or settings.LLM_API_KEY):
            raise ValueError("No LLM API key configured. Set LLM_API_KEY in your environment.")

        self.model = model or settings.LLM_MODEL
        self.max_retries = max_retries if max_retries is not None else settings.LLM_MAX_RETRIES

        self._client = AsyncOpenAI(
            api_key=api_key or settings.LLM_API_KEY,
            base_url=base_url or settings.LLM_BASE_URL,
            timeout=timeout or settings.LLM_TIMEOUT_SECONDS,
        )

    async def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> str:
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.chat.completions.create(
                    model=model or self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content
                if content is None:
                    raise ValueError("LLM returned empty completion content")
                return content

            except (APIError, APITimeoutError, ValueError) as exc:
                last_error = exc
                logger.warning(
                    "LLM call failed (attempt %d/%d): %s",
                    attempt + 1,
                    self.max_retries + 1,
                    exc,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep((2 ** attempt) * 0.5)

        raise RuntimeError(
            f"LLM completion failed after {self.max_retries + 1} attempts"
        ) from last_error