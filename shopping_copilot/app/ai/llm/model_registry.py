from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    name: str
    provider: str
    temperature: float = 0.0
    max_tokens: int = 1024

# to register and manage LLM model configurations

class ModelRegistry:
    def __init__(self):
        self._models: dict[str, ModelConfig] = {}

    def register(
        self,
        role: str,
        config: ModelConfig,
    ) -> None:
        self._models[role] = config

    def get(
        self,
        role: str,
    ) -> ModelConfig | None:
        return self._models.get(role)

    def has(
        self,
        role: str,
    ) -> bool:
        return role in self._models

    def remove(
        self,
        role: str,
    ) -> None:
        self._models.pop(role, None)