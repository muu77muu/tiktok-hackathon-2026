from typing import Any

from .model_registry import ModelRegistry

# provider-agnostic LLM client

class LLMClient:
    def __init__(
        self,
        model_registry: ModelRegistry | None = None,
    ):
        self.model_registry = (
            model_registry or ModelRegistry()
        )

    # generate text from a prompt
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:

        raise NotImplementedError(
            "LLM provider has not been configured."
        )

    # generate structured output from a prompt
    async def generate_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> dict[str, Any]:

        raise NotImplementedError(
            "Structured LLM provider has not been configured."
        )