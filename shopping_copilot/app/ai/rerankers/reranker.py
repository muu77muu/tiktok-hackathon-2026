import asyncio
import logging
import threading
from dataclasses import dataclass

from app.core.config import get_settings

logger = logging.getLogger(__name__)

@dataclass
class RankedCandidate:
    product_id: str
    score: float
    rank: int
    metadata: dict | None = None

# Qwen3-Reranker is a causal LM, not a classification cross-encoder: it judges
# each (query, document) pair by generating "yes"/"no", and the relevance score
# is the softmax probability of "yes" at the final position. The chat template
# below comes from the model card and must match exactly.
_PREFIX = (
    "<|im_start|>system\nJudge whether the Document meets the requirements "
    'based on the Query and the Instruct provided. Note that the answer can '
    'only be "yes" or "no".<|im_end|>\n<|im_start|>user\n'
)
_SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"

_DEFAULT_INSTRUCTION = (
    "Given a shopping query, judge whether the product listing is relevant "
    "to what the user wants to buy"
)

DEFAULT_MAX_LENGTH = 2048

class Reranker:
    def __init__(
        self,
        model: str | None = None,
        device: str | None = None,
        instruction: str = _DEFAULT_INSTRUCTION,
        max_length: int = DEFAULT_MAX_LENGTH,
    ):
        settings = get_settings()

        self.model_name = model or settings.RERANKER_MODEL
        self.device = device or settings.RERANKER_DEVICE or None
        self.instruction = instruction
        self.max_length = max_length

        self._model = None
        self._tokenizer = None
        self._lock = threading.Lock()

    def _ensure_loaded(self):
        # lazy singleton, same rationale as Embedder: don't pay the weight
        # load until the first rerank actually happens
        if self._model is None:
            with self._lock:
                if self._model is None:
                    import torch
                    from transformers import AutoModelForCausalLM, AutoTokenizer

                    logger.info("loading reranker model %s", self.model_name)
                    device = self.device or (
                        "cuda" if torch.cuda.is_available() else "cpu"
                    )
                    self._tokenizer = AutoTokenizer.from_pretrained(
                        self.model_name, padding_side="left"
                    )
                    self._model = (
                        AutoModelForCausalLM.from_pretrained(self.model_name)
                        .to(device)
                        .eval()
                    )
                    self._yes_id = self._tokenizer.convert_tokens_to_ids("yes")
                    self._no_id = self._tokenizer.convert_tokens_to_ids("no")
                    # prefix/suffix are prepended/appended at the token level
                    # so truncation of a long document can never eat the
                    # template -- the "yes"/"no" logit is read at the last
                    # position, which must stay the assistant turn
                    self._prefix_ids = self._tokenizer.encode(
                        _PREFIX, add_special_tokens=False
                    )
                    self._suffix_ids = self._tokenizer.encode(
                        _SUFFIX, add_special_tokens=False
                    )

    def _score_batch(self, query: str, documents: list[str]) -> list[float]:
        import torch

        self._ensure_loaded()

        pairs = [
            f"<Instruct>: {self.instruction}\n<Query>: {query}\n<Document>: {doc}"
            for doc in documents
        ]
        budget = self.max_length - len(self._prefix_ids) - len(self._suffix_ids)
        encoded = self._tokenizer(
            pairs,
            padding=False,
            truncation="longest_first",
            return_attention_mask=False,
            max_length=budget,
        )
        input_ids = [
            self._prefix_ids + ids + self._suffix_ids
            for ids in encoded["input_ids"]
        ]
        batch = self._tokenizer.pad(
            {"input_ids": input_ids}, padding=True, return_tensors="pt"
        ).to(self._model.device)

        with torch.no_grad():
            logits = self._model(**batch).logits[:, -1, :]
            yes_no = torch.stack(
                [logits[:, self._no_id], logits[:, self._yes_id]], dim=1
            )
            scores = torch.nn.functional.log_softmax(yes_no, dim=1)[:, 1].exp()

        return scores.tolist()

    async def score_pair(self, query: str, document: str) -> float:
        """Single-pair scoring -- the model_client interface expected by
        services/ranking/cross_encoder.py's CrossEncoderReranker."""
        [score] = await asyncio.to_thread(self._score_batch, query, [document])
        return score

    async def rerank(
        self,
        query: str,
        candidates: list[dict],
        context: dict | None = None,
    ) -> list[RankedCandidate]:
        """Scores all candidates in one batched forward pass and returns them
        sorted by relevance. Candidates follow the retrieval candidate shape:
        {"product_id": ..., "metadata": {"title": ..., "description": ...}}."""
        if not candidates:
            return []

        documents = [self._document_text(c) for c in candidates]
        scores = await asyncio.to_thread(self._score_batch, query, documents)

        ranked = sorted(
            zip(candidates, scores), key=lambda pair: pair[1], reverse=True
        )
        return [
            RankedCandidate(
                product_id=candidate.get("product_id", ""),
                score=score,
                rank=rank,
                metadata=candidate.get("metadata"),
            )
            for rank, (candidate, score) in enumerate(ranked, start=1)
        ]

    def _document_text(self, candidate: dict) -> str:
        metadata = candidate.get("metadata") or {}
        title = metadata.get("title", "")
        description = metadata.get("description", "")
        return f"{title}. {description}".strip()
