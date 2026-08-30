from app.core.config import get_settings

LLM_MODEL = get_settings().LLM_MODEL

TASK_MODELS: dict[str, str] = {
    "extraction": LLM_MODEL,
    "llm_ranking": LLM_MODEL,
    "scenario_analysis": LLM_MODEL,
}

def get_model_for_task(task: str) -> str:
    return TASK_MODELS.get(task, LLM_MODEL)