# to coordinate creation, retrieval, updating, and termination of conversational shopping sessions

from .session_state import SessionState
from .session_store import SessionStore
from .session_limits import SessionLimits
from .turn_manager import TurnManager

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

    def create(self, session_id: str, user_id: str | None = None) -> SessionState:
        session = SessionState(session_id=session_id, user_id=user_id)

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

    # fuller check than can_continue, catching idle / age expiry too
    def check_limits(self, session_id: str) -> tuple[bool, str | None]:
        session = self.get(session_id)
        if session is None:
            return False, "session_not_found"
        return self.limits.check(session)

    def record_turn(
        self,
        session_id: str,
        query: str,
        response: str,
        pipeline_result: dict | None = None,
    ) -> SessionState | None:
        session = self.get(session_id)
        if session is None:
            return None

        self.turn_manager.record_exchange(session, query, response, pipeline_result)
        self.store.update(session)

        return session

    def end(self, session_id: str) -> None:
        self.store.delete(session_id)