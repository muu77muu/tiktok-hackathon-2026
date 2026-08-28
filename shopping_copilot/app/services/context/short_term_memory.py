
# to maintain transient context for the current shopping session

class ShortTermMemory:
    def __init__(self):
        self.state: dict = {}

    def get(self, key: str, default=None):
        return self.state.get(key, default)

    def set(self, key: str, value):
        self.state[key] = value

    def update(self, values: dict):
        self.state.update(values)

    def remove(self, key: str):
        self.state.pop(key, None)

    def clear(self):
        self.state.clear()

    def snapshot(self) -> dict:
        return dict(self.state)