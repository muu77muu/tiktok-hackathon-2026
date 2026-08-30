
# Buying pipeline: each stage can short-circuit the pipeline (eg. by requesting clarification or failing validation) without downstream stages needing to know why.
# Expected collaborator interfaces (duck-typed, so you can swap implementations):
#    constraint_extractor.extract(query: str, context: dict) -> Constraints
#    constraint_validator.validate(constraints: Constraints) -> ValidationResult
#    filter_builder.build(constraints: Constraints) -> dict  # search filters
#    strategy.execute(filters: dict, constraints: Constraints, context: dict) -> list[Candidate]

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.exceptions import OverGeneralityDetected

logger = logging.getLogger(__name__)

class PipelineStatus(str, Enum):
    OK = "ok"
    NEEDS_CLARIFICATION = "needs_clarification"
    VALIDATION_FAILED = "validation_failed"
    NO_RESULTS = "no_results"
    ERROR = "error"

@dataclass
class PipelineResult:
    intent: str = "buying"
    status: PipelineStatus = PipelineStatus.OK
    query: str = ""
    constraints: Any | None = None
    filters: dict | None = None
    candidates: list[Any] = field(default_factory=list)
    clarification_prompt: str | None = None
    errors: list[str] = field(default_factory=list)
    context: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "status": self.status.value,
            "query": self.query,
            "constraints": self.constraints,
            "filters": self.filters,
            "candidates": self.candidates,
            "clarification_prompt": self.clarification_prompt,
            "errors": self.errors,
            "context": self.context,
        }


class BuyingPipeline:
    def __init__(
        self,
        constraint_extractor=None,
        constraint_validator=None,
        filter_builder=None,
        strategy=None,
    ):
        self.constraint_extractor = constraint_extractor
        self.constraint_validator = constraint_validator
        self.filter_builder = filter_builder
        self.strategy = strategy

    async def run(self, query: str, context: dict | None = None) -> dict:
        context = context or {}
        result = PipelineResult(query=query, context=context)

        # Stage 1: extract constraints from the query
        try:
            constraints = await self.constraint_extractor.extract(query, context)
            result.constraints = constraints
        except Exception as exc:
            logger.exception("constraint extraction failed for query=%r", query)
            result.status = PipelineStatus.ERROR
            result.errors.append(f"extraction_failed: {exc}")
            return result.to_dict()

        # Stage 2: validate constraints (missing/conflicting info)
        try:
            validation = await self.constraint_validator.validate(constraints)
        except Exception as exc:
            logger.exception("constraint validation failed")
            result.status = PipelineStatus.ERROR
            result.errors.append(f"validation_failed: {exc}")
            return result.to_dict()

        if not validation.is_valid:
            if validation.clarification_prompt:
                result.status = PipelineStatus.NEEDS_CLARIFICATION
                result.clarification_prompt = validation.clarification_prompt
            else:
                result.status = PipelineStatus.VALIDATION_FAILED
                result.errors.extend(validation.errors)
            return result.to_dict()

        # Stage 3: build search filters from validated constraints
        try:
            filters = await self.filter_builder.build(constraints)
            result.filters = filters
        except Exception as exc:
            logger.exception("filter building failed")
            result.status = PipelineStatus.ERROR
            result.errors.append(f"filter_build_failed: {exc}")
            return result.to_dict()

        # Stage 4: execute retrieval/ranking strategy 
        try:
            candidates = await self.strategy.execute(
                filters=filters, constraints=constraints, context=context
            )
        except OverGeneralityDetected as exc:
            # Retrieval cutoff, the candidate pool was too scattered to rank meaningfully, so the strategy raised before spending any ranking budget on it. 
            result.status = PipelineStatus.NEEDS_CLARIFICATION
            result.clarification_prompt = exc.prompt
            return result.to_dict()
        except Exception as exc:
            logger.exception("strategy execution failed")
            result.status = PipelineStatus.ERROR
            result.errors.append(f"strategy_failed: {exc}")
            return result.to_dict()

        result.candidates = candidates or []
        result.status = (PipelineStatus.OK if result.candidates else PipelineStatus.NO_RESULTS)
        return result.to_dict()