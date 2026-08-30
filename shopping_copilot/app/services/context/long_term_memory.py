
# to maintain persistent user preferences and behavioral info
# Long-term memory: cross-session facts about a user, distinct from short-term memory's within-session turn window. 

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

STALE_AFTER = timedelta(days=60)  # learned preferences older than this are down-weighted

@dataclass
class LearnedPreference:
    key: str            # eg. "brand_affinity", "price_sensitivity", "style"
    value: str
    strength: float      # between 0.0 - 1.0, how strongly held
    learned_at: datetime | None = None
    source: str = "inferred"  # "inferred" | "explicit"

    def is_stale(self, now: datetime | None = None) -> bool:
        if self.learned_at is None:
            return False
        now = now or datetime.now(timezone.utc)
        return (now - self.learned_at) > STALE_AFTER

@dataclass
class UserProfile:
    user_id: str | None = None
    learned_preferences: list[LearnedPreference] = field(default_factory=list)
    rejected_categories: list[str] = field(default_factory=list)
    rejected_brands: list[str] = field(default_factory=list)
    purchase_signals: list[dict] = field(default_factory=list)  # lightweight history, not full order data
    is_new_user: bool = True

class LongTermMemory:
    def __init__(self, user_store=None):
        self.user_store = user_store

    async def get_profile(self, user_id: str | None) -> UserProfile:
        if not user_id or self.user_store is None:
            return UserProfile(user_id=user_id, is_new_user=True)

        try:
            raw = await self._safe_get(user_id)
        except Exception:
            return UserProfile(user_id=user_id, is_new_user=True)

        if not raw:
            return UserProfile(user_id=user_id, is_new_user=True)

        return self._to_profile(user_id, raw)

    async def _safe_get(self, user_id: str) -> dict | None:
        result = self.user_store.get_profile(user_id)

        if hasattr(result, "__await__"):
            result = await result

        return result

    def _to_profile(self, user_id: str, raw: dict) -> UserProfile:
        prefs = [
            LearnedPreference(
                key=p.get("key"),
                value=p.get("value"),
                strength=p.get("strength", 0.5),
                learned_at=self._parse_dt(p.get("learned_at")),
                source=p.get("source", "inferred"),
            )
            for p in raw.get("learned_preferences", [])
        ]

        return UserProfile(
            user_id=user_id,
            learned_preferences=prefs,
            rejected_categories=raw.get("rejected_categories", []),
            rejected_brands=raw.get("rejected_brands", []),
            purchase_signals=raw.get("purchase_signals", []),
            is_new_user=False,
        )

    def _parse_dt(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    # staleness checked here, not filtered at storage time
    def active_preferences(self, profile: UserProfile) -> list[LearnedPreference]:
        now = datetime.now(timezone.utc)
        return [p for p in profile.learned_preferences if not p.is_stale(now)]