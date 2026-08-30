from dataclasses import dataclass

@dataclass
class WorkflowDecision:
    action: str  # "buying" | "browsing" | "clarify"
    intent: str
    reason: str
    clarification_prompt: str | None = None
    confidence: float = 0.0