
# to distill conversation history into relevant context for the current shopping interaction
# Distills conversation history + session state + user profile into the compact context dict that orchestration_service.py passes down into buying_pipeline.py / browsing_pipeline.py.

from .short_term_memory import ShortTermMemory
from .long_term_memory import LongTermMemory, UserProfile
from .preference_manager import PreferenceManager
from .context_relevance import ContextRelevance

class ContextDistiller:
    def __init__(
        self,
        short_term_memory: ShortTermMemory | None = None,
        long_term_memory: LongTermMemory | None = None,
        preference_manager: PreferenceManager | None = None,
        context_relevance: ContextRelevance | None = None,
    ):
        self.short_term_memory = short_term_memory
        self.long_term_memory = long_term_memory
        self.preference_manager = preference_manager
        self.context_relevance = context_relevance

    async def distill(
        self,
        query: str,
        conversation_history: list[dict] | None = None,
        session_state: dict | None = None,
        user_profile: dict | None = None,
    ) -> dict:
        conversation_history = conversation_history or []
        session_state = session_state or {}
        user_profile = user_profile or {}

        window = await self.short_term_memory.get_window(
            conversation_history, prior_summary=session_state.get("rolling_summary")
        )

        profile = await self._resolve_profile(user_profile, session_state)

        last_result = window.last_pipeline_result or {}
        session_constraints = last_result.get("constraints") if last_result.get("intent") == "buying" else None
        prior_scenario = last_result.get("scenario") if last_result.get("intent") == "browsing" else None

        resolved = await self.preference_manager.resolve(session_constraints, profile)

        relevant_history = await self.context_relevance.filter_history(query, window.recent_turns)
        relevant_preferences = await self.context_relevance.filter_preferences(
            query, resolved.active_preferences
        )

        return {
            "query": query,
            "session_context": session_state,
            "user_context": user_profile,
            "relevant_history": relevant_history,
            "active_preferences": relevant_preferences,
            "active_constraints": resolved.active_constraints,
            "summary": window.rolling_summary,
            "prior_constraints": session_constraints,
            "prior_scenario": prior_scenario,
        }

    async def _resolve_profile(self, user_profile: dict, session_state: dict) -> UserProfile:
        # If the caller already attached a full profile snapshot (eg. session_service pre-fetched it), trust it and skip the extra storage round-trip. Otherwise fetch from long_term_memory.
        if user_profile.get("learned_preferences") is not None:
            return self._profile_from_dict(user_profile)

        user_id = user_profile.get("user_id") or session_state.get("user_id")
        if self.long_term_memory is None:
            return UserProfile(user_id=user_id, is_new_user=user_id is None)

        return await self.long_term_memory.get_profile(user_id)

    def _profile_from_dict(self, user_profile: dict) -> UserProfile:
        from .long_term_memory import LearnedPreference

        prefs = [
            LearnedPreference(
                key=p.get("key"), value=p.get("value"), strength=p.get("strength", 0.5)
            )
            for p in user_profile.get("learned_preferences", [])
        ]
        
        return UserProfile(
            user_id=user_profile.get("user_id"),
            learned_preferences=prefs,
            rejected_categories=user_profile.get("rejected_categories", []),
            rejected_brands=user_profile.get("rejected_brands", []),
            purchase_signals=user_profile.get("purchase_signals", []),
            is_new_user=False,
        )