
# to manage user preferences extracted from the conversation and determine how they should influence recommendations

class PreferenceManager:
    def extract_preferences(
        self,
        query: str,
        context: dict | None = None,
    ) -> list[dict]:

        return []

    def update(
        self,
        preferences: list[dict],
    ) -> dict:

        return {
            "preferences": preferences,
        }

    def clear(
        self,
        preference_keys: list[str],
    ) -> dict:

        return {
            "cleared": preference_keys,
        }