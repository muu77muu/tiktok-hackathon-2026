
# to maintain structured conversational state and support incremental updates, overwrites, and slot removal

class StateManager:
    def __init__(self, session_store=None):
        self.session_store = session_store
        self._memory: dict[str, dict] = {}

    async def get_state(
        self,
        session_id: str,
    ) -> dict:
        if self.session_store:
            return await self.session_store.get(session_id)

        return self._memory.get(
            session_id,
            {
                "session_id": session_id,
                "turn_count": 0,
                "intent": None,
                "previous_intent": None,
                "constraints": {},
                "next_action": None,
            },
        )

    # merge updates into current workflow state
    async def update_state(
        self,
        session_id: str,
        updates: dict,
    ) -> dict:
        current = await self.get_state(session_id)
        updated = {**current, **updates}

        if self.session_store:
            await self.session_store.save(session_id, updated,)
        else:
            self._memory[session_id] = updated

        return updated