
# to maintain persistent user preferences and behavioral info

class LongTermMemory:
    def __init__(self):
        self.profile: dict = {}

    def get(self, key: str, default=None):
        return self.profile.get(key, default)

    def set(self, key: str, value):
        self.profile[key] = value

    def update(self, values: dict):
        self.profile.update(values)

    def remove(self, key: str):
        self.profile.pop(key, None)

    def snapshot(self) -> dict:
        return dict(self.profile)