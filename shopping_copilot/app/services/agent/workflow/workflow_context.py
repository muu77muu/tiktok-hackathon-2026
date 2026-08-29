from dataclasses import dataclass, field
from typing import Any

# Context passed between agent workflows


@dataclass
class WorkflowContext:

    session_id: str
    user_message: str
    conversation: list[dict[str, Any]] = field(default_factory=list)
    short_term_memory: dict[str, Any] = field(default_factory=dict)
    long_term_memory: dict[str, Any] = field(default_factory=dict)
    retrieved_candidates: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)