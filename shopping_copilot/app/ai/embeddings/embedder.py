from typing import Sequence

# provider-agnostic embedding interface for product and query vector representations

class Embedder:
    def __init__(
        self,
        model_registry=None,
    ):
        self.model_registry = model_registry

    # embed a single text into a vector representation
    def embed(
        self,  
        text: str,
    ) -> list[float]:

        raise NotImplementedError(
            "Embedding provider has not been configured."
        )

    # embed multiple texts into vector representations
    def embed_batch(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:

        return [
            self.embed(text)
            for text in texts
        ]