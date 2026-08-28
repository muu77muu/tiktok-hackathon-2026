from datetime import datetime, timezone

# manages lifecycle and history of individual conversational turns
# handles each individual conversation turns

class TurnManager:
    def __init__(self):
        self.history: dict[str, list[dict]] = {}

    def start_turn(
        self,
        session_id: str,
        message: str,
    ) -> dict:

        turns = self.history.setdefault(
            session_id,
            [],
        )
        turn = {
            "turn_number": len(turns) + 1,
            "user_message": message,
            "timestamp": datetime.now(timezone.utc),
        }

        turns.append(turn)

        return turn

    def complete_turn(
        self,
        session_id: str,
        response: dict,
    ) -> None:

        turns = self.history.get(
            session_id,
            [],
        )

        if not turns:
            return

        turns[-1]["response"] = response
        turns[-1]["completed_at"] = datetime.now(
            timezone.utc
        )

    def get_history(
        self,
        session_id: str,
    ) -> list[dict]:

        return list(
            self.history.get(
                session_id,
                [],
            )
        )

    def clear(
        self,
        session_id: str,
    ) -> None:

        self.history.pop(session_id, None)