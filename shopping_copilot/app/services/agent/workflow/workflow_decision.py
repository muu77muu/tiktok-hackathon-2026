from dataclasses import dataclass, field
from typing import Any

# Decision emitted by the agent orchestration layer

@dataclass
class WorkflowDecision:

    action: str
    intent: str | None = None
    reason: str | None = None
    parameters: dict[str, Any] = field(
        default_factory=dict
    )