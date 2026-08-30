from dataclasses import dataclass

from app.core.config import get_settings

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


_registry = EmbeddingModelRegistry()
_settings = get_settings()

_registry.register(
    "active",
    EmbeddingModelConfig(
        name=_settings.EMBEDDING_MODEL,
        provider="local",
        dimensions=_settings.EMBEDDING_DIMENSIONS,
    ),
)


def get_active_embedding_model() -> EmbeddingModelConfig:
    config = _registry.get("active")
    if config is None:
        raise RuntimeError("No active embedding model registered.")
    return config
