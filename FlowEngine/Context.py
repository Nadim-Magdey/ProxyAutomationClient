from typing import Dict

class Context:
    instance = None

    def __init__(self):
        self.values: Dict[str, object] = {}
        self.request = None
        self.response = None
        
    @staticmethod
    def getInstance():
        if Context.instance is None:
            Context.instance = Context()
        return Context.instance

    def get(self, key):
        if not key:
            raise KeyError("Key cannot be empty")
        return self.values.get(key)

    def store(self, key, value):
        if not key or value is None:
            raise KeyError("Key or value cannot be None")
        if key in self.values:
            raise KeyError(f"Key '{key}' already exists")
        self.values[key] = value
        return True

    def update(self, key, value):
        if key not in self.values:
            raise KeyError(f"Key '{key}' does not exist")
        self.values[key] = value

    def remove(self, key):
        if key not in self.values:
            raise KeyError(f"Key '{key}' does not exist")
        self.values.pop(key)
