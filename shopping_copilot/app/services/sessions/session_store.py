
# in-memory storage for (requirement) conversational sessions.

class SessionStore:
    def __init__(self):
        self.sessions: dict[str, object] = {}

    def create(self, session) -> None:
        self.sessions[session.session_id] = session

    def get(self, session_id: str):
        return self.sessions.get(session_id)

    def exists(self, session_id: str) -> bool:
        return session_id in self.sessions

    def update(self, session) -> None:
        self.sessions[session.session_id] = session

    def delete(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)

    def clear(self) -> None:
        self.sessions.clear()