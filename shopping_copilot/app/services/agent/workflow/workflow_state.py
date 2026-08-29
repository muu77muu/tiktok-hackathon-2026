from dataclasses import dataclass, field
from typing import Any

# runtime state for one agent session

@dataclass
class WorkflowState:
    """Runtime state for one Shopping Agent session."""

    session_id: str
    turn_count: int = 0
    intent: str | None = None
    previous_intent: str | None = None
    constraints: dict[str, Any] = field(default_factory=dict)
    candidates: list[Any] = field(default_factory=list)
    next_action: str | None = None
    clarification_required: bool = False
    terminated: bool = False