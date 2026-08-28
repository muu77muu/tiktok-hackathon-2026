from dataclasses import dataclass, field
from datetime import datetime, timezone

# to maintain the runtime state of a single shopping conversation

@dataclass
class SessionState:

    session_id: str
    turn_count: int = 0
    intent: str | None = None
    status: str = "active"

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    metadata: dict = field(default_factory=dict)

    def increment_turn(self) -> int:
        self.turn_count += 1
        self.updated_at = datetime.now(timezone.utc)

        return self.turn_count

    def set_intent(self, intent: str | None) -> None:
        self.intent = intent
        self.updated_at = datetime.now(timezone.utc)

    def terminate(self) -> None:
        self.status = "terminated"
        self.updated_at = datetime.now(timezone.utc)