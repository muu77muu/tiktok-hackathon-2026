
# to enforce conversational session limits

class SessionLimits:
    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns

    def can_continue(
        self,
        turn_count: int,
    ) -> bool:

        return turn_count < self.max_turns

    def has_reached_limit(
        self,
        turn_count: int,
    ) -> bool:

        return turn_count >= self.max_turns

    def remaining_turns(
        self,
        turn_count: int,
    ) -> int:

        return max(
            0,
            self.max_turns - turn_count,
        )