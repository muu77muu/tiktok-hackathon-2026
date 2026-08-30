
# manages lifecycle and history of individual conversational turns
# Formats and appends turns to a session's conversation_history. The turn shape here matches exactly what services/context/short_term_memory.py and context_relevance.py read

from datetime import datetime, timezone

from .session_state import SessionState

class TurnManager:
    def add_user_turn(self, session: SessionState, query: str) -> None:
        session.conversation_history.append(
            {
                "role": "user",
                "content": query,
                "timestamp": self._now(),
            }
        )

    def add_assistant_turn(
        self,
        session: SessionState,
        content: str,
        pipeline_result: dict | None = None,
    ) -> None:
        turn = {
            "role": "assistant",
            "content": content,
            "timestamp": self._now(),
        }
        if pipeline_result is not None:
            turn["pipeline_result"] = pipeline_result
        session.conversation_history.append(turn)

    def record_exchange(
        self,
        session: SessionState,
        query: str,
        response: str,
        pipeline_result: dict | None = None,
    ) -> None:
        # records a full 'user -> assistant' exchange as a single logical turn
        self.add_user_turn(session, query)
        self.add_assistant_turn(session, response, pipeline_result)
        session.turn_count += 1

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()