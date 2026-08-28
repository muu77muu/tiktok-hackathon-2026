from .session_state import SessionState
from .session_store import SessionStore
from .session_limits import SessionLimits
from .turn_manager import TurnManager

# to coordinate creation, retrieval, updating, and termination of conversational shopping sessions

class SessionService:
    def __init__(
        self,
        store: SessionStore | None = None,
        limits: SessionLimits | None = None,
        turn_manager: TurnManager | None = None,
    ):
        self.store = store or SessionStore()
        self.limits = limits or SessionLimits()
        self.turn_manager = turn_manager or TurnManager()

    def create(self, session_id: str) -> SessionState:
        session = SessionState(session_id=session_id)

        self.store.create(session)

        return session

    def get(self, session_id: str) -> SessionState | None:
        return self.store.get(session_id)

    def exists(self, session_id: str) -> bool:
        return self.store.exists(session_id)

    def can_continue(self, session_id: str) -> bool:
        session = self.get(session_id)

        if session is None:
            return False

        return self.limits.can_continue(
            session.turn_count
        )

    def end(self, session_id: str) -> None:
        self.store.delete(session_id)