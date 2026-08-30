
# Browsing pipeline: orchestrates discovery flow in stages:
#  1. scenario_analyzer -> understand occasion/use-case, detect ambiguity
#  2. query_expander + multi_query_generator + hyde_service run concurrently but indepedently
#  3. strategy.execute() fans out retrieval across all variants and fuses

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.exceptions import OverGeneralityDetected

logger = logging.getLogger(__name__)

class PipelineStatus(str, Enum):
    OK = "ok"
    NEEDS_CLARIFICATION = "needs_clarification"
    NO_RESULTS = "no_results"
    ERROR = "error"

@dataclass
class PipelineResult:
    intent: str = "browsing"
    status: PipelineStatus = PipelineStatus.OK
    query: str = ""
    scenario: Any | None = None
    expanded_query: Any | None = None
    multi_query: Any | None = None
    hyde_document: Any | None = None
    candidates: list[Any] = field(default_factory=list)
    clarification_prompt: str | None = None
    errors: list[str] = field(default_factory=list)
    context: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "status": self.status.value,
            "query": self.query,
            "scenario": self.scenario,
            "expanded_query": self.expanded_query,
            "multi_query": self.multi_query,
            "hyde_document": self.hyde_document,
            "candidates": self.candidates,
            "clarification_prompt": self.clarification_prompt,
            "errors": self.errors,
            "context": self.context,
        }

class BrowsingPipeline:
    def __init__(
        self,
        scenario_analyzer=None,
        query_expander=None,
        multi_query_generator=None,
        hyde_service=None,
        strategy=None,
    ):
        self.scenario_analyzer = scenario_analyzer
        self.query_expander = query_expander
        self.multi_query_generator = multi_query_generator
        self.hyde_service = hyde_service
        self.strategy = strategy

    async def run(self, query: str, context: dict | None = None) -> dict:
        context = context or {}
        result = PipelineResult(query=query, context=context)

        # Stage 1: understand the scenario behind the query 
        try:
            scenario = await self.scenario_analyzer.analyze(query, context)
            result.scenario = scenario
        except Exception as exc:
            logger.exception("scenario analysis failed for query=%r", query)
            result.status = PipelineStatus.ERROR
            result.errors.append(f"scenario_analysis_failed: {exc}")
            return result.to_dict()

        if scenario.is_ambiguous:
            result.status = PipelineStatus.NEEDS_CLARIFICATION
            result.clarification_prompt = scenario.ambiguity_reason or ("Can you tell me a bit more about what you're looking for?")
            return result.to_dict()

        # Stage 2: expand + fan out (independent, run concurrently)
        try:
            expanded_query, multi_query, hyde_document = await self._run_expansion_stages(
                query, scenario
            )
            result.expanded_query = expanded_query
            result.multi_query = multi_query
            result.hyde_document = hyde_document
        except Exception as exc:
            logger.exception("query expansion stages failed for query=%r", query)
            result.status = PipelineStatus.ERROR
            result.errors.append(f"expansion_failed: {exc}")
            return result.to_dict()

        # Stage 3: fold expanded terms into the multi-query set 
        multi_query = self._merge_expanded_into_multi_query(multi_query, expanded_query)
        result.multi_query = multi_query

        # Stage 4: execute retrieval strategy
        try:
            candidates = await self.strategy.execute(
                multi_query=multi_query,
                hyde_doc=hyde_document,
                scenario=scenario,
                context=context,
            )
        except OverGeneralityDetected as exc:
            result.status = PipelineStatus.NEEDS_CLARIFICATION
            result.clarification_prompt = exc.prompt
            return result.to_dict()
        except Exception as exc:
            logger.exception("browsing strategy execution failed")
            result.status = PipelineStatus.ERROR
            result.errors.append(f"strategy_failed: {exc}")
            return result.to_dict()

        result.candidates = candidates or []
        result.status = (PipelineStatus.OK if result.candidates else PipelineStatus.NO_RESULTS)
        return result.to_dict()

    # concurrent independent execution of query expansion, multi-query generation, and HyDE
    async def _run_expansion_stages(self, query: str, scenario):
        expanded_task = self.query_expander.expand(query, scenario)
        multi_query_task = self.multi_query_generator.generate(query, scenario)
        hyde_task = self.hyde_service.generate(query, scenario)

        expanded_query, multi_query, hyde_document = await asyncio.gather(
            expanded_task, multi_query_task, hyde_task
        )
        return expanded_query, multi_query, hyde_document

    def _merge_expanded_into_multi_query(self, multi_query, expanded_query):
        existing = {q.strip().lower() for q in multi_query.queries}
        if expanded_query.expanded_query_string.strip().lower() not in existing:
            multi_query.queries.append(expanded_query.expanded_query_string)
        return multi_query