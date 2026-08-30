
# in-memory storage for (requirement) conversational sessions.
# Service-layer session persistence. Wraps a storage backend behind a small sync interface

from .session_state import SessionState

class SessionStore:
    def __init__(self, backend=None):
        self.backend = backend
        self._local: dict[str, SessionState] = {}

    def create(self, session: SessionState) -> None:
        if self.backend is not None:
            self.backend.set(session.session_id, self._serialize(session))
        else:
            self._local[session.session_id] = session

    def get(self, session_id: str) -> SessionState | None:
        if self.backend is not None:
            raw = self.backend.get(session_id)
            return self._deserialize(raw) if raw else None
        return self._local.get(session_id)

    def update(self, session: SessionState) -> None:
        session.touch()
        if self.backend is not None:
            self.backend.set(session.session_id, self._serialize(session))
        else:
            self._local[session.session_id] = session

    def exists(self, session_id: str) -> bool:
        return self.get(session_id) is not None

    def delete(self, session_id: str) -> None:
        if self.backend is not None:
            self.backend.delete(session_id)
        else:
            self._local.pop(session_id, None)

    def _serialize(self, session: SessionState) -> dict:
        return {
            **session.to_dict(),
            "conversation_history": session.conversation_history,
        }

    def _deserialize(self, raw: dict) -> SessionState:
        from datetime import datetime
        from .session_state import SessionStatus

        return SessionState(
            session_id=raw["session_id"],
            user_id=raw.get("user_id"),
            status=SessionStatus(raw.get("status", "active")),
            turn_count=raw.get("turn_count", 0),
            conversation_history=raw.get("conversation_history", []),
            rolling_summary=raw.get("rolling_summary"),
            created_at=datetime.fromisoformat(raw["created_at"]),
            updated_at=datetime.fromisoformat(raw["updated_at"]),
            metadata=raw.get("metadata", {}),
        )