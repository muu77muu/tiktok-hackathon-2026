
# to manage lifecycle of a conversational turn

class ConversationManager:
    def start_turn(
        self,
        session_id: str,
        message: str,
    ) -> dict:
        return {
            "session_id": session_id,
            "message": message,
        }

    def complete_turn(
        self,
        session_id: str,
        response: dict,
    ) -> dict:
        return response