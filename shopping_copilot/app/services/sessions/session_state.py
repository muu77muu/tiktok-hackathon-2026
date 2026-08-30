# to maintain the runtime state of a single shopping conversation
# session's data shape where turn_manager.py and session_store.py both need to update it in place as a conversation progresses

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

class SessionStatus(str, Enum):
    ACTIVE = "active"
    ENDED = "ended"
    EXPIRED = "expired"

@dataclass
class SessionState:
    session_id: str
    user_id: str | None = None
    status: SessionStatus = SessionStatus.ACTIVE
    turn_count: int = 0
    conversation_history: list[dict] = field(default_factory=list)
    rolling_summary: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)  # freeform, e.g. channel, locale

    def touch(self) -> None:
        now = datetime.now(timezone.utc)
        self.updated_at = now
        self.last_active_at = now

    # shape consumed by context_distiller.distill()'s session_state param
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "turn_count": self.turn_count,
            "rolling_summary": self.rolling_summary,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }