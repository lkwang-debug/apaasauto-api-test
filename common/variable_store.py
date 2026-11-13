class VariableStore:
    def __init__(self):
        self._store = {}

    def put(self, key, value):
        self._store[key] = value

    def get(self, key, default=None):
        return self._store.get(key, default)

    def contains(self, key):
        return key in self._store

    def update(self, values):
        self._store.update(values)

    def all(self):
        return dict(self._store)

    def reset(self):
        self._store.clear()
