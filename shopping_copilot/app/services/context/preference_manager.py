
# to manage user preferences extracted from the conversation and determine how they should influence recommendations
# merges two sources of "what does this user want" that have very different trust levels:
# - session-explicit: stated in the current conversation (high trust, but only relevant to this session's shopping task)
# - long-term-inferred: learned across past sessions (lower trust per-item, but persistent -- eg. "tends to prefer mid-range price points")

# conflict rule: explicit session statements always win over inferred long-term preferences for the same key. Long-term *rejections* (rejected_brands/categories) are treated as soft excludes that a session's explicit include can override

from dataclasses import dataclass, field

from .long_term_memory import LongTermMemory, UserProfile

@dataclass
class ActivePreference:
    key: str
    value: str
    strength: float
    source: str  # "explicit" | "inferred"

@dataclass
class ActiveConstraint:
    key: str
    value: str
    kind: str  # "include" | "exclude"
    source: str  # "explicit" | "inferred" | "rejection"

@dataclass
class ResolvedPreferences:
    active_preferences: list[ActivePreference] = field(default_factory=list)
    active_constraints: list[ActiveConstraint] = field(default_factory=list)

class PreferenceManager:
    def __init__(self, long_term_memory: LongTermMemory | None = None):
        self.long_term_memory = long_term_memory

    async def resolve(
        self,
        session_constraints: object | None,  # duck-typed buying Constraints, if present
        profile: UserProfile,
    ) -> ResolvedPreferences:
        explicit_prefs, explicit_constraints = self._from_session(session_constraints)
        inferred_prefs = self._from_profile(profile)

        explicit_keys = {p.key for p in explicit_prefs}
        merged_prefs = explicit_prefs + [
            p for p in inferred_prefs if p.key not in explicit_keys
        ]

        rejections = self._from_rejections(profile)
        explicit_include_values = {
            c.value.lower() for c in explicit_constraints if c.kind == "include"
        }
        merged_constraints = explicit_constraints + [
            r for r in rejections if r.value.lower() not in explicit_include_values
        ]

        return ResolvedPreferences(
            active_preferences=merged_prefs, active_constraints=merged_constraints
        )

    def _from_session(
        self, constraints: object | None
    ) -> tuple[list[ActivePreference], list[ActiveConstraint]]:
        if constraints is None:
            return [], []

        prefs: list[ActivePreference] = []
        cons: list[ActiveConstraint] = []

        for attr_name, attr_value in getattr(constraints, "attributes", {}).items():
            prefs.append(
                ActivePreference(key=attr_name, value=str(attr_value), strength=1.0, source="explicit")
            )

        for brand in getattr(constraints, "brands_include", []) or []:
            cons.append(ActiveConstraint(key="brand", value=brand, kind="include", source="explicit"))

        for brand in getattr(constraints, "brands_exclude", []) or []:
            cons.append(ActiveConstraint(key="brand", value=brand, kind="exclude", source="explicit"))

        return prefs, cons

    def _from_profile(self, profile: UserProfile) -> list[ActivePreference]:
        if self.long_term_memory is not None:
            active = self.long_term_memory.active_preferences(profile)
        else:
            active = profile.learned_preferences

        return [
            ActivePreference(key=p.key, value=p.value, strength=p.strength, source="inferred")
            for p in active
        ]

    def _from_rejections(self, profile: UserProfile) -> list[ActiveConstraint]:
        cons = [
            ActiveConstraint(key="category", value=c, kind="exclude", source="rejection")
            for c in profile.rejected_categories
        ]
        cons += [
            ActiveConstraint(key="brand", value=b, kind="exclude", source="rejection")
            for b in profile.rejected_brands
        ]
        
        return cons