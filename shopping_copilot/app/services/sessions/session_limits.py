
# to enforce conversational session limits
# Policy checks for whether a session should be allowed to continue; separate from SessionStore (persistence) and SessionState (data) 

from datetime import datetime, timedelta, timezone

from .session_state import SessionState

DEFAULT_MAX_TURNS = 10
DEFAULT_IDLE_TIMEOUT = timedelta(minutes=30)
DEFAULT_MAX_SESSION_AGE = timedelta(hours=6)

class SessionLimits:
    def __init__(
        self,
        max_turns: int = DEFAULT_MAX_TURNS,
        idle_timeout: timedelta = DEFAULT_IDLE_TIMEOUT,
        max_session_age: timedelta = DEFAULT_MAX_SESSION_AGE,
    ):
        self.max_turns = max_turns
        self.idle_timeout = idle_timeout
        self.max_session_age = max_session_age

    def can_continue(self, turn_count: int) -> bool:
        return turn_count < self.max_turns

    def is_idle_expired(self, session: SessionState) -> bool:
        now = datetime.now(timezone.utc)
        return (now - session.last_active_at) > self.idle_timeout

    def is_age_expired(self, session: SessionState) -> bool:
        now = datetime.now(timezone.utc)
        return (now - session.created_at) > self.max_session_age

    def is_expired(self, session: SessionState) -> bool:
        return self.is_idle_expired(session) or self.is_age_expired(session)

    def check(self, session: SessionState) -> tuple[bool, str | None]:
        if self.is_age_expired(session):
            return False, "session_max_age_exceeded"
        if self.is_idle_expired(session):
            return False, "session_idle_timeout"
        if not self.can_continue(session.turn_count):
            return False, "turn_limit_exceeded"
        return True, None