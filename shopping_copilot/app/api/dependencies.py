from app.services.copilot.copilot_service import CopilotService
from app.services.sessions.sessions_service import SessionService
from app.services.ranking.ranking_service import RankingService

_copilot_service = CopilotService()
_session_service = SessionService()
_ranking_service = RankingService()

def get_copilot_service() -> CopilotService:
    return _copilot_service

def get_session_service() -> SessionService:
    return _session_service

def get_recommendation_service():
    from app.services.copilot.recommendation_service import RecommendationService
    return RecommendationService(ranking_service=_ranking_service)

def get_search_service():
    raise NotImplementedError(
        "Search service integration pending."
    )


def get_evaluation_service():
    from app.services.evaluation.evaluation_service import EvaluationService
    return EvaluationService()