import uuid
from django.core.cache import cache

class SafeLock:
    def init(self, key, ttl=10):
        self.key = key
        self.ttl = ttl
        self.token = str(uuid.uuid4())

    def acquire(self):
        return cache.add(self.key, self.token, self.ttl)

    def release(self):
        # ⚠️ Not 100% safe unless Redis supports atomic check+delete
        val = cache.get(self.key)
        if val == self.token:
            cache.delete(self.key)
            return True
        return False