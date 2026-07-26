import redis


class RedisCacheClient:
    """Implements CacheClient (application/caching/ports.py) against the same Redis instance
    already used as the Celery broker (settings.redis_url) — no new infrastructure. A cache
    failure (Redis briefly unreachable, etc.) must never break a request: get() returns None
    (a cache miss, caller falls back to the real read) and set() is best-effort, both swallowing
    RedisError specifically rather than letting a cache problem surface as a 500."""

    def __init__(self, redis_url: str) -> None:
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def get(self, key: str) -> str | None:
        try:
            # redis-py's stubs type Redis.get as a sync/async union (shared base class with the
            # async client) — this is the sync client with decode_responses=True, so the actual
            # runtime value is always str | None, never an Awaitable.
            return self._client.get(key)  # type: ignore[return-value]
        except redis.RedisError:
            return None

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            self._client.set(key, value, ex=ttl_seconds)
        except redis.RedisError:
            pass
