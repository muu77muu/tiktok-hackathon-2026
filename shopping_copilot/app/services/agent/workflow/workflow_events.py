from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

 # Observable event produced during an agent workflow.

@dataclass
class WorkflowEvent:

    event_type: str
    session_id: str
    turn_count: int = 0
    payload: dict[str, Any] = field(default_factory=dict)

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))