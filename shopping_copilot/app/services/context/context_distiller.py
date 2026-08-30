
# to distill conversation history into relevant context for the current shopping interaction
# Distills conversation history + session state + user profile into the compact context dict that orchestration_service.py passes down into buying_pipeline.py / browsing_pipeline.py.

from .short_term_memory import ShortTermMemory
from .long_term_memory import LongTermMemory, UserProfile
from .preference_manager import PreferenceManager
from .context_relevance import ContextRelevance
from .slot_override_detector import SlotOverrideDetector
 
 
class ContextDistiller:
    def __init__(
        self,
        short_term_memory: ShortTermMemory | None = None,
        long_term_memory: LongTermMemory | None = None,
        preference_manager: PreferenceManager | None = None,
        context_relevance: ContextRelevance | None = None,
        slot_override_detector: SlotOverrideDetector | None = None,
    ):
        self.short_term_memory = short_term_memory
        self.long_term_memory = long_term_memory
        self.preference_manager = preference_manager
        self.context_relevance = context_relevance
        self.slot_override_detector = slot_override_detector or SlotOverrideDetector()
 
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
 
        override = await self._detect_override(query, session_constraints, prior_scenario)
        if override.is_override:
            # do not merge stale constraints/scenario into a topic the user has already moved on from. 
            # constraint_extractor.py's merge only runs when prior_constraints is present
            session_constraints = None
            prior_scenario = None
 
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
            "intent_override": override.is_override,
            "override_reason": override.reason,
        }
    # prior_focus_text is what the override detector compares the new message against for topic drift
    async def _detect_override(self, query: str, session_constraints, prior_scenario):
        prior_focus_text = None
        if session_constraints is not None:
            prior_focus_text = getattr(session_constraints, "category", None) or getattr(
                session_constraints, "raw_query", None
            )
        elif prior_scenario is not None:
            prior_focus_text = getattr(prior_scenario, "scenario_summary", None)
 
        return await self.slot_override_detector.detect(query, prior_focus_text)
 
    async def _resolve_profile(self, user_profile: dict, session_state: dict) -> UserProfile:
        # if caller already attached a full profile snapshot), skip the extra storage round-trip
        # # otherwise fetch from long_term_memory
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