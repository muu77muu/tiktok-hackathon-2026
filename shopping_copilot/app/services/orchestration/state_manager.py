
# to maintain structured conversational state and support incremental updates, overwrites, and slot removal
# Orchestration-level state: intent, previous intent, next action, pending clarification field
# state_make_decision() and intent_router.py need to make routing decisions

class StateManager:
    def __init__(self, cache=None):
        self.cache = cache
        self._local: dict[str, dict] = {}

    async def get_state(self, session_id: str) -> dict:
        if self.cache is not None:
            state = await self._safe_get(session_id)
            return state or {}
        return self._local.get(session_id, {})

    async def update_state(self, session_id: str, updates: dict) -> dict:
        current = await self.get_state(session_id)
        merged = {**current, **updates}

        if self.cache is not None:
            await self._safe_set(session_id, merged)
        else:
            self._local[session_id] = merged

        return merged

    async def _safe_get(self, session_id: str) -> dict | None:
        result = self.cache.get(session_id)
        if hasattr(result, "__await__"):
            result = await result
        return result

    async def _safe_set(self, session_id: str, value: dict) -> None:
        result = self.cache.set(session_id, value)
        if hasattr(result, "__await__"):
            await result