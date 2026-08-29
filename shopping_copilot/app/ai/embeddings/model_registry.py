from dataclasses import dataclass

# configuration for an embedding model
@dataclass(frozen=True)
class EmbeddingModelConfig:
    name: str
    provider: str
    dimensions: int | None = None

# registry for embedding models
class EmbeddingModelRegistry:
    def __init__(self):
        self._models: dict[str, EmbeddingModelConfig] = {}

    def register(
        self,
        role: str,
        config: EmbeddingModelConfig,
    ) -> None:
        self._models[role] = config

    def get(
        self,
        role: str,
    ) -> EmbeddingModelConfig | None:
        return self._models.get(role)