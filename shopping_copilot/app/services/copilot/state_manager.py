
# to maintain structured conversational state and support incremental updates, overwrites, and slot removal

class StateManager:

    def __init__(self):
        self.sessions: dict[str, dict] = {}

    def get_state(
        self,
        session_id: str,
    ) -> dict:

        return self.sessions.get(
            session_id,
            {},
        )

    def update_state(
        self,
        session_id: str,
        values: dict,
    ) -> dict:

        state = self.get_state(session_id)
        state.update(values)

        self.sessions[session_id] = state

        return state

    def remove(
        self,
        session_id: str,
        keys: list[str],
    ) -> dict:

        state = self.get_state(session_id)

        for key in keys:
            state.pop(key, None)

        self.sessions[session_id] = state

        return state

    def clear(
        self,
        session_id: str,
    ):
        self.sessions.pop(session_id, None)