
# to inspect Information Accumulation, Intent Override, and Clarification
# pure, storate-agnostic class to persist DialogStateMachine.to_dict() across turns
# only know states and transitions, not where it is stored

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)

class DialogState(str, Enum):
    ROUTING = "routing"            # intent not yet established this turn
    ACCUMULATING = "accumulating"  # intent known, gathering/refining slots
    CLARIFYING = "clarifying"      # waiting on the user to resolve an ambiguity
    CONVERGED = "converged"        # results delivered for the current slot set

class DialogEvent(str, Enum):
    INTENT_CLASSIFIED = "intent_classified"
    SLOTS_UPDATED = "slots_updated"
    OVERRIDE_DETECTED = "override_detected"
    CLARIFICATION_NEEDED = "clarification_needed"
    CLARIFICATION_ANSWERED = "clarification_answered"
    RESULTS_DELIVERED = "results_delivered"

# (current_state, event) -> next_state. Any (state, event) pair not listed here is treated as a no-op transition (logged, state unchanged) rather than raising
TRANSITIONS: dict[tuple[DialogState, DialogEvent], DialogState] = {
    (DialogState.ROUTING, DialogEvent.INTENT_CLASSIFIED): DialogState.ACCUMULATING,
    (DialogState.ROUTING, DialogEvent.CLARIFICATION_NEEDED): DialogState.CLARIFYING,

    (DialogState.ACCUMULATING, DialogEvent.SLOTS_UPDATED): DialogState.ACCUMULATING,
    (DialogState.ACCUMULATING, DialogEvent.CLARIFICATION_NEEDED): DialogState.CLARIFYING,
    (DialogState.ACCUMULATING, DialogEvent.RESULTS_DELIVERED): DialogState.CONVERGED,
    (DialogState.ACCUMULATING, DialogEvent.OVERRIDE_DETECTED): DialogState.ROUTING,

    (DialogState.CLARIFYING, DialogEvent.CLARIFICATION_ANSWERED): DialogState.ACCUMULATING,
    (DialogState.CLARIFYING, DialogEvent.OVERRIDE_DETECTED): DialogState.ROUTING,
    # Self-loop: the user's reply still didn't resolve the ambiguity
    # (e.g. answered one clarifying question but a second one is needed).
    (DialogState.CLARIFYING, DialogEvent.CLARIFICATION_NEEDED): DialogState.CLARIFYING,

    (DialogState.CONVERGED, DialogEvent.SLOTS_UPDATED): DialogState.ACCUMULATING,
    (DialogState.CONVERGED, DialogEvent.CLARIFICATION_NEEDED): DialogState.CLARIFYING,
    (DialogState.CONVERGED, DialogEvent.OVERRIDE_DETECTED): DialogState.ROUTING,
}

MAX_HISTORY = 30

@dataclass
class TransitionRecord:
    from_state: DialogState
    event: DialogEvent
    to_state: DialogState
    timestamp: str

@dataclass
class DialogStateMachine:
    state: DialogState = DialogState.ROUTING
    history: list[TransitionRecord] = field(default_factory=list)
    consecutive_no_results: int = 0
    consecutive_clarifications: int = 0

    def apply(self, event: DialogEvent) -> DialogState:
        key = (self.state, event)
        next_state = TRANSITIONS.get(key)

        if next_state is None:
            logger.warning("unmodeled transition (%s, %s); state unchanged", self.state, event)
            next_state = self.state

        record = TransitionRecord(
            from_state=self.state,
            event=event,
            to_state=next_state,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.history.append(record)
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]

        self.state = next_state
        self._update_counters(event)
        return self.state

    def _update_counters(self, event: DialogEvent) -> None:
        if event == DialogEvent.CLARIFICATION_NEEDED:
            self.consecutive_clarifications += 1
        elif event in (DialogEvent.RESULTS_DELIVERED, DialogEvent.CLARIFICATION_ANSWERED):
            self.consecutive_clarifications = 0

        if event == DialogEvent.OVERRIDE_DETECTED:
            self.consecutive_no_results = 0
            self.consecutive_clarifications = 0

    def record_pipeline_status(self, status: str) -> None:
        if status == "no_results":
            self.consecutive_no_results += 1
        elif status == "ok":
            self.consecutive_no_results = 0

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "consecutive_no_results": self.consecutive_no_results,
            "consecutive_clarifications": self.consecutive_clarifications,
            "history": [
                {
                    "from_state": r.from_state.value,
                    "event": r.event.value,
                    "to_state": r.to_state.value,
                    "timestamp": r.timestamp,
                }
                for r in self.history
            ],
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "DialogStateMachine":
        if not data:
            return cls()

        history = [
            TransitionRecord(
                from_state=DialogState(r["from_state"]),
                event=DialogEvent(r["event"]),
                to_state=DialogState(r["to_state"]),
                timestamp=r["timestamp"],
            )
            for r in data.get("history", [])
        ]

        return cls(
            state=DialogState(data.get("state", DialogState.ROUTING.value)),
            history=history,
            consecutive_no_results=data.get("consecutive_no_results", 0),
            consecutive_clarifications=data.get("consecutive_clarifications", 0),
        )