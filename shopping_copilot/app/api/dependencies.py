from functools import lru_cache

from app.ai.llm.client import LLMClient
from app.ai.embeddings.embedder import Embedder
from app.ai.rerankers.reranker import Reranker

# buying
from app.services.buying.constraint_extractor import ConstraintExtractor
from app.services.buying.constraint_validator import ConstraintValidator
from app.services.buying.filter_builder import FilterBuilder
from app.services.buying.buying_strategy import BuyingStrategy
from app.services.buying.buying_pipeline import BuyingPipeline

# browsing
from app.services.browsing.scenario_analyzer import ScenarioAnalyzer
from app.services.browsing.query_expander import QueryExpander
from app.services.browsing.multi_query_generator import MultiQueryGenerator
from app.services.browsing.hyde_service import HydeService
from app.services.browsing.browsing_strategy import BrowsingStrategy
from app.services.browsing.browsing_pipeline import BrowsingPipeline

# retrieval
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.retrieval.vector_retriever import VectorRetriever

# ranking
from app.services.ranking.scoring import Scoring
from app.services.ranking.cross_encoder import CrossEncoderReranker
from app.services.ranking.llm_ranker import LLMRanker
from app.services.ranking.diversification import Diversification
from app.services.ranking.ranking_service import RankingService

# context
from app.services.context.short_term_memory import ShortTermMemory
from app.services.context.long_term_memory import LongTermMemory
from app.services.context.preference_manager import PreferenceManager
from app.services.context.context_relevance import ContextRelevance
from app.services.context.context_distiller import ContextDistiller

# sessions
from app.services.sessions.sessions_service import SessionService

# copilot / orchestration
from app.services.orchestration.intent_router import IntentRouter
from app.services.orchestration.state_manager import StateManager
from app.services.orchestration.conversation_manager import ConversationManager
from app.services.orchestration.context_manager import ContextManager
from app.services.orchestration.clarification_service import ClarificationService
from app.services.orchestration.recommendation_service import RecommendationService
from app.services.orchestration.orchestration_service import OrchestrationService

@lru_cache()
def get_llm_client() -> LLMClient:
    return LLMClient()

@lru_cache()
def get_embedder() -> Embedder:
    return Embedder()

@lru_cache()
def get_reranker() -> Reranker:
    return Reranker()

@lru_cache()
def get_session_service() -> SessionService:
    return SessionService()

@lru_cache()
def get_retrieval_service() -> RetrievalService:
    return RetrievalService(
        keyword_retriever=None,  # TODO: wire infrastructure/search/keyword_index.py
        vector_retriever=VectorRetriever(
            vector_index=None,  # TODO: wire infrastructure/search/vector_index.py
            embedder=get_embedder(),
        ),
        category_retriever=None,  # TODO: wire infrastructure/search/category_index.py
    )

@lru_cache()
def get_ranking_service() -> RankingService:
    llm = get_llm_client()
    return RankingService(
        scoring=Scoring(),
        cross_encoder=CrossEncoderReranker(model_client=get_reranker()),
        llm_ranker=LLMRanker(llm_client=llm),
        diversification=Diversification(),
    )

@lru_cache()
def get_context_distiller() -> ContextDistiller:
    llm = get_llm_client()
    long_term = LongTermMemory(user_store=None)  # TODO: wire infrastructure/storage/user_store.py

    return ContextDistiller(
        short_term_memory=ShortTermMemory(llm_client=llm),
        long_term_memory=long_term,
        preference_manager=PreferenceManager(long_term_memory=long_term),
        context_relevance=ContextRelevance(embedder=get_embedder()),
    )

@lru_cache()
def get_buying_pipeline() -> BuyingPipeline:
    llm = get_llm_client()
    return BuyingPipeline(
        constraint_extractor=ConstraintExtractor(llm_client=llm),
        constraint_validator=ConstraintValidator(),
        filter_builder=FilterBuilder(),
        strategy=BuyingStrategy(
            retrieval_service=get_retrieval_service(),
            ranking_service=get_ranking_service(),
        ),
    )

@lru_cache()
def get_browsing_pipeline() -> BrowsingPipeline:
    llm = get_llm_client()
    return BrowsingPipeline(
        scenario_analyzer=ScenarioAnalyzer(llm_client=llm),
        query_expander=QueryExpander(synonym_lookup=None),
        multi_query_generator=MultiQueryGenerator(llm_client=llm),
        hyde_service=HydeService(llm_client=llm, embedder=get_embedder()),
        strategy=BrowsingStrategy(
            retrieval_service=get_retrieval_service(),
            ranking_service=get_ranking_service(),
        ),
    )

@lru_cache()
def get_orchestration_service() -> OrchestrationService:
    llm = get_llm_client()
    session_service = get_session_service()

    return OrchestrationService(
        conversation_manager=ConversationManager(session_service=session_service),
        intent_router=IntentRouter(classifier=None, llm_client=llm),  # TODO: wire ai/classifiers/intent_classifier.py
        state_manager=StateManager(),
        context_manager=ContextManager(
            session_service=session_service,
            context_distiller=get_context_distiller(),
            user_store=None,  # TODO: wire infrastructure/storage/user_store.py
        ),
        clarification_service=ClarificationService(llm_client=llm),
        recommendation_service=RecommendationService(llm_client=llm),
        buying_pipeline=get_buying_pipeline(),
        browsing_pipeline=get_browsing_pipeline(),
    )