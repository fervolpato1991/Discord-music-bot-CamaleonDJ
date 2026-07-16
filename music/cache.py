class MusicCache:

    def __init__(self):

        self._cache = {}

    # ==================================================
    # Acceso
    # ==================================================

    def has(self, key):

        return key in self._cache

    def get(self, key):

        return self._cache.get(key)

    def set(self, key, value):

        self._cache[key] = value

    # ==================================================
    # Estado
    # ==================================================

    def clear(self):

        self._cache.clear()

    def __contains__(self, key):

        return key in self._cache

    def __len__(self):

        return len(self._cache)